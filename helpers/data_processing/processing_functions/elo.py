import math
from helpers.database_helpers.get_and_set_functions import get_from_matches
from helpers.elo.elo_helpers import calculate_elo_ratings, get_counts, get_entity_elo, save_elo_history, update_counter_table, update_entity_elo

def calculate_elos(conn):
    """Main function to calculate ELO ratings for both teams before a match and update their ratings based on the result of the match in question
    
    Args:
        conn (sqlite3.Connection): The database connection
        matches (list): The list of matches to process from
    """

    processed_count = 0
    
    matches = get_from_matches(conn, select_str='SELECT DISTINCT', columns=['match_id', 'start_time', 'competition_id', 'competition_name', 'competition_country', 'home_team_id', 'home_team_name', 'away_team_id', 'away_team_name', 
               'home_score', 'away_score', 'home_team_domestic_league_id', 'home_team_domestic_country', 'away_team_domestic_league_id', 'away_team_domestic_country'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = false', order_by='start_time')

    # Start calculating ELOs for the rest of the matches
    for match in matches:
        match_id, start_time, competition_id, competition_name, competition_country, home_team_id, home_team_name, away_team_id, away_team_name, \
        home_score, away_score, home_team_domestic_league_id, home_team_domestic_country, \
        away_team_domestic_league_id, away_team_domestic_country = match

        if processed_count % 1000 == 0:
            print(f"ELO: Processing match {processed_count}/{len(matches)}")
        
        is_same_nation = (home_team_domestic_country == away_team_domestic_country) 
        is_same_league = home_team_domestic_league_id == away_team_domestic_league_id
        is_domestic = is_same_nation and not is_same_league

        # NOTE: For different datasets the competitions might be named differently. Please change to your naming convention
        
        is_international = not is_same_nation and not is_same_league
        
        # Get ALL elo ratings for both team (club, nation, league)
        home_club_elos = get_entity_elo(conn, 'club_elo_ratings', 'team_id', home_team_id, 'team_name', home_team_name)
        home_nation_elos = get_entity_elo(conn, 'nation_elo_ratings', 'nation_name', home_team_domestic_country) if home_team_domestic_country else None
        home_league_elos = get_entity_elo(conn, 'league_elo_ratings', 'league_id', home_team_domestic_league_id) if home_team_domestic_league_id else None

        away_club_elos = get_entity_elo(conn, 'club_elo_ratings', 'team_id', away_team_id, 'team_name', away_team_name)
        away_nation_elos = get_entity_elo(conn, 'nation_elo_ratings', 'nation_name', away_team_domestic_country) if away_team_domestic_country else None
        away_league_elos = get_entity_elo(conn, 'league_elo_ratings', 'league_id', away_team_domestic_league_id) if away_team_domestic_league_id else None

        # Get match result counts for the competition, used to dynamically set the k_draw_parameter and eta_home_advantage
        league_counts = get_counts(conn, str(competition_id), get_nation=False)
        home_wins, draw_wins, away_wins, count = league_counts

        probability_home_win = home_wins / (home_wins + draw_wins + away_wins)
        probability_away_win = away_wins / (home_wins + draw_wins + away_wins)
        probability_draw = draw_wins / (home_wins + draw_wins + away_wins)

        denominator = math.sqrt(probability_home_win * probability_away_win)
        if denominator == 0:
            k_draw_parameter = 0.25 #Default values
            eta_home_advantage = 0.3 
        else:
            k_draw_parameter = probability_draw / math.sqrt(probability_home_win * probability_away_win) #Useful in elo_davidson_formula
            eta_home_advantage = math.log10(probability_home_win / probability_away_win) #Useful in elo_davidson_formula

        # Important: Save the current ELO ratings before updating them
        save_elo_history(conn, match_id, home_team_id, away_team_id, home_club_elos, away_club_elos, home_nation_elos, away_nation_elos, home_league_elos, away_league_elos, home_score, away_score, k_draw_parameter, eta_home_advantage)
   
        k_values = [5, 10, 20, 30, 40, 80] #Parameter of the elo_davidson_formula

        # Create copies for updates
        #TODO: Check if this is necessary
        updated_home_club = home_club_elos.copy()
        updated_away_club = away_club_elos.copy()
        updated_home_league = home_league_elos.copy() 
        updated_away_league = away_league_elos.copy()
        updated_home_nation = home_nation_elos.copy()
        updated_away_nation = away_nation_elos.copy()
        
        match_info = f"{home_team_name} {home_score}-{away_score} {away_team_name}"

        # NATION ELOs
        if not is_same_nation:
            updated_home_nation, updated_away_nation = calculate_elo_ratings(
                conn, home_score, away_score, 
                home_nation_elos, away_nation_elos, 
                'nation_elo_k', k_values, match_info,
                k_draw_parameter, eta_home_advantage
            )
        
        # LEAGUE ELOs
        if is_domestic:
            updated_home_league, updated_away_league = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_league, updated_away_league, 
                'league_domestic_elo_k', k_values, match_info,
                k_draw_parameter, eta_home_advantage
            )

        if not is_same_league:
            updated_home_league, updated_away_league = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_league, updated_away_league, 
                'league_continental_elo_k', k_values, match_info,
                k_draw_parameter, eta_home_advantage
            )
        
        # CLUB ELOs
        # General ELOs (all matches)
        updated_home_club, updated_away_club = calculate_elo_ratings(
            conn, home_score, away_score, 
            updated_home_club, updated_away_club, 
            'elo_k', k_values, match_info, 
            k_draw_parameter, eta_home_advantage
        )
        
        # Home-specific ELOs
        home_temp = updated_home_club.copy()
        updated_home_club, _ = calculate_elo_ratings(
            conn, home_score, away_score, 
            updated_home_club, home_temp,  # Use same dict to prevent away updates 
            'elo_home_matches_k', k_values, match_info, 
            k_draw_parameter, eta_home_advantage
        )
        
        # Away-specific ELOs
        away_temp = updated_away_club.copy()
        _, updated_away_club = calculate_elo_ratings(
            conn, home_score, away_score, 
            away_temp, updated_away_club,  # Use same dict to prevent home updates
            'elo_away_matches_k', k_values, match_info, 
            k_draw_parameter, eta_home_advantage
        )
        
        # Domestic ELOs
        if is_same_nation:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_domestic_k', k_values, match_info, 
                k_draw_parameter, eta_home_advantage
            )
        
        # Intraleague ELOs
        if is_same_league:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_intraleague_k', k_values, match_info, 
                k_draw_parameter, eta_home_advantage
            )
        
        # International ELOs
        if is_international:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_international_k', k_values, match_info, 
                k_draw_parameter, eta_home_advantage
            )
        
        result = 'home' if home_score > away_score else 'away' if home_score < away_score else 'draw'
        update_counter_table(conn, str(competition_id), result)

        # Update ALL Elo ratings for both clubs in the database
        #Home team
        update_entity_elo(conn, 'club_elo_ratings', 'team_id', home_team_id, updated_home_club)
        update_entity_elo(conn, 'nation_elo_ratings', 'nation_name', home_team_domestic_country, updated_home_nation)
        update_entity_elo(conn, 'league_elo_ratings', 'league_id', home_team_domestic_league_id, updated_home_league)

        #Away team
        update_entity_elo(conn, 'club_elo_ratings', 'team_id', away_team_id, updated_away_club)
        update_entity_elo(conn, 'nation_elo_ratings', 'nation_name', away_team_domestic_country, updated_away_nation)
        update_entity_elo(conn, 'league_elo_ratings', 'league_id', away_team_domestic_league_id, updated_away_league)

        processed_count += 1