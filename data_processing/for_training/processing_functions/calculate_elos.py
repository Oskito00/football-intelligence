import math
import sqlite3
from helpers.database_helpers.create_tables import create_elo_tables
from helpers.elo.elo_helpers import calculate_elo_ratings, get_club_elo, get_counts, get_entity_elo, get_league_elo, get_nation_elo, save_elo_history, update_club_elo, update_counter_table, update_entity_elo, update_league_elo, update_nation_elo

def calculate_elos(conn, matches):
    """Main function to calculate ELO ratings for both teams before a match and update their ratings based on the result of the match in question
    
    Args:
        conn (sqlite3.Connection): The database connection
        matches (list): The list of matches to process from
    """
    print("Number of matches: ", len(matches))
    first_5000 = matches[:5000] #first 5000 matches are used to establish k_draw_parameter and eta_home advantage in elo_extraction
    rest = matches[5000:]

    create_elo_tables(conn) #If not already created

    #Generate initial priors for k_draw_parameter and eta_home_advantage
    for match in first_5000: 
        match_id, start_time, competition_id, competition_name, competition_country, home_team_id, home_team_name, away_team_id, away_team_name, \
        home_score, away_score, home_team_domestic_league_id, home_team_domestic_country, \
        away_team_domestic_league_id, away_team_domestic_country = match

        result = 'home' if home_score > away_score else 'away' if home_score < away_score else 'draw'
        update_counter_table(conn, competition_id, result)

    # Start calculating ELOs for the rest of the matches
    for match in rest:
        match_id, start_time, competition_id, competition_name, competition_country, home_team_id, home_team_name, away_team_id, away_team_name, \
        home_score, away_score, home_team_domestic_league_id, home_team_domestic_country, \
        away_team_domestic_league_id, away_team_domestic_country = match

        print("Processing match: ", match_id)
        
        is_same_nation = (home_team_domestic_country == away_team_domestic_country) 
        is_same_league = home_team_domestic_league_id == away_team_domestic_league_id
        is_domestic = is_same_nation and not is_same_league

        # NOTE: For different datasets the competitions might be named differently. Please change to your naming convention
        continental_comps = ['Champions League', 'Europa League', 'Europa Conference League']
        is_continental = competition_name in continental_comps
        
        # Get ALL elo ratings for both team (club, nation, league)
        home_club_elos = get_entity_elo(conn, 'club_elo_ratings', 'team_id', home_team_id, 'team_name', home_team_name)
        home_nation_elos = get_entity_elo(conn, 'nation_elo_ratings', 'nation_name', home_team_domestic_country) if home_team_domestic_country else None
        home_league_elos = get_entity_elo(conn, 'league_elo_ratings', 'league_id', home_team_domestic_league_id) if home_team_domestic_league_id else None

        away_club_elos = get_entity_elo(conn, 'club_elo_ratings', 'team_id', away_team_id, 'team_name', away_team_name)
        away_nation_elos = get_entity_elo(conn, 'nation_elo_ratings', 'nation_name', away_team_domestic_country) if away_team_domestic_country else None
        away_league_elos = get_entity_elo(conn, 'league_elo_ratings', 'league_id', away_team_domestic_league_id) if away_team_domestic_league_id else None

        # Get match result counts for the competition, used to dynamically set the k_draw_parameter and eta_home_advantage
        league_counts = get_counts(conn, competition_id, get_nation=False)
        home_wins, draw_wins, away_wins, count = league_counts

        probability_home_win = home_wins / (home_wins + draw_wins + away_wins)
        probability_away_win = away_wins / (home_wins + draw_wins + away_wins)
        probability_draw = draw_wins / (home_wins + draw_wins + away_wins)

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
                'nation_elo_K', k_values, match_info,
                k_draw_parameter, eta_home_advantage
            )
        
        # LEAGUE ELOs
        if is_domestic:
            updated_home_league, updated_away_league = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_league, updated_away_league, 
                'league_domestic_elo_K', k_values, match_info,
                k_draw_parameter, eta_home_advantage
            )

        if not is_same_league:
            updated_home_league, updated_away_league = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_league, updated_away_league, 
                'league_continental_elo_K', k_values, match_info,
                k_draw_parameter, eta_home_advantage
            )
        
        # CLUB ELOs
        # General ELOs (all matches)
        updated_home_club, updated_away_club = calculate_elo_ratings(
            conn, home_score, away_score, 
            updated_home_club, updated_away_club, 
            'elo_K', k_values, match_info, 
            k_draw_parameter, eta_home_advantage
        )
        
        # Home-specific ELOs
        home_temp = updated_home_club.copy()
        updated_home_club, _ = calculate_elo_ratings(
            conn, home_score, away_score, 
            updated_home_club, home_temp,  # Use same dict to prevent away updates 
            'elo_home_matches_K', k_values, match_info, 
            k_draw_parameter, eta_home_advantage
        )
        
        # Away-specific ELOs
        away_temp = updated_away_club.copy()
        _, updated_away_club = calculate_elo_ratings(
            conn, home_score, away_score, 
            away_temp, updated_away_club,  # Use same dict to prevent home updates
            'elo_away_matches_K', k_values, match_info, 
            k_draw_parameter, eta_home_advantage
        )
        
        # Domestic ELOs
        if is_same_nation:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_domestic_K', k_values, match_info, 
                k_draw_parameter, eta_home_advantage
            )
        
        # Intraleague ELOs
        if is_same_league:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_intraleague_K', k_values, match_info, 
                k_draw_parameter, eta_home_advantage
            )
        
        # International ELOs
        if is_continental:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_international_K', k_values, match_info, 
                k_draw_parameter, eta_home_advantage
            )
        
        result = 'home' if home_score > away_score else 'away' if home_score < away_score else 'draw'
        update_counter_table(conn, competition_id, result)

        # Update ALL Elo ratings for both clubs in the database
        #Home team
        update_entity_elo(conn, 'club_elo_ratings', 'team_id', home_team_id, updated_home_club)
        update_entity_elo(conn, 'nation_elo_ratings', 'nation_name', home_team_domestic_country, updated_home_nation)
        update_entity_elo(conn, 'league_elo_ratings', 'league_id', home_team_domestic_league_id, updated_home_league)

        #Away team
        update_entity_elo(conn, 'club_elo_ratings', 'team_id', away_team_id, updated_away_club)
        update_entity_elo(conn, 'nation_elo_ratings', 'nation_name', away_team_domestic_country, updated_away_nation)
        update_entity_elo(conn, 'league_elo_ratings', 'league_id', away_team_domestic_league_id, updated_away_league)


if __name__ == "__main__":
    conn = sqlite3.connect('v2db.sqlite')
    calculate_elos(conn)
