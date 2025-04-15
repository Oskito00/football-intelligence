import math
import sqlite3
from helpers.elo.elo_helpers import calculate_elo_ratings, get_club_elo, get_counts, get_league_elo, get_nation_elo, save_elo_history, update_club_elo, update_counter_table, update_league_elo, update_nation_elo

def calculate_elos(matches):
    print("Number of matches: ", len(matches))
    # First 1000 matches will be used to set initial priors on probability if home, away or draw
    first_1000 = matches[:1000]
    rest = matches[1000:]

    # First 1000 matches will be used solely as counter data (not used for ELO calculations)
    for match in first_1000:
        match_id, start_time, competition_id, competition_name, competition_country, home_team_id, home_team_name, away_team_id, away_team_name, \
        home_score, away_score, home_main_comp_id, home_main_comp_country, \
        away_main_comp_id, away_main_comp_country = match

        # Update counter table
        result = 'home' if home_score > away_score else 'away' if home_score < away_score else 'draw'
        #Must have created the counter table first
        update_counter_table(conn, competition_id, result)

    # Now that we have initialised our priors, we can start calculating ELOs
    for match in rest:
        print("Processing match: ", match[0])
        match_id, start_time, competition_id, competition_name, competition_country, home_team_id, home_team_name, away_team_id, away_team_name, \
        home_score, away_score, home_main_comp_id, home_main_comp_country, \
        away_main_comp_id, away_main_comp_country = match
        
        # Determine if match is domestic or international
        is_same_nation = (home_main_comp_country == away_main_comp_country)
        is_same_league = home_main_comp_id == away_main_comp_id
        is_domestic = is_same_nation and not is_same_league
        # NOTE: For different datasets the competitions might be named differently. Please change to your naming convention
        continental_comps = ['UEFA Champions League', 'UEFA Europa League', 'UEFA Europa Conference League']
        is_continental = competition_name in continental_comps
        
        # Get all ELO ratings for both teams
        home_club_elos = get_club_elo(conn, home_team_id, home_team_name)
        away_club_elos = get_club_elo(conn, away_team_id, away_team_name)

        home_nation_elos = get_nation_elo(conn, home_main_comp_country) if home_main_comp_country else None
        away_nation_elos = get_nation_elo(conn, away_main_comp_country) if away_main_comp_country else None

        home_league_elos = get_league_elo(conn, home_main_comp_id) if home_main_comp_id else None
        away_league_elos = get_league_elo(conn, away_main_comp_id) if away_main_comp_id else None

        # Get home, draw, away win counts for league (the league the game was played in)
        # These are used to dynamically set the k_draw_parameter and eta_home_advantage
        # used in the elo_davidson_formula.
        league_counts = get_counts(conn, competition_id, get_nation=False)

        home_wins, draw_wins, away_wins, count = league_counts

        probability_home_win = home_wins / (home_wins + draw_wins + away_wins)
        probability_away_win = away_wins / (home_wins + draw_wins + away_wins)
        probability_draw = draw_wins / (home_wins + draw_wins + away_wins)

        k_draw_parameter = probability_draw / math.sqrt(probability_home_win * probability_away_win)
        eta_home_advantage = math.log10(probability_home_win / probability_away_win)

        # Save the current ELOs to elo_history
        save_elo_history(conn, match_id, home_team_id, away_team_id, home_club_elos, away_club_elos, home_nation_elos, away_nation_elos, home_league_elos, away_league_elos, home_score, away_score, k_draw_parameter, eta_home_advantage)
   
        # K-factor values
        k_values = [5, 10, 20, 30, 40, 80]

        # Create copies for updates
        updated_home_club = home_club_elos.copy()
        updated_away_club = away_club_elos.copy()
        updated_home_league = home_league_elos.copy() 
        updated_away_league = away_league_elos.copy()
        updated_home_nation = home_nation_elos.copy()
        updated_away_nation = away_nation_elos.copy()
        
        match_info = f"{home_team_name} {home_score}-{away_score} {away_team_name}"

        # Update nation ELOs
        if not is_same_nation:
            print("Updating nation ELOs")
            updated_home_nation, updated_away_nation = calculate_elo_ratings(
                conn, home_score, away_score, 
                home_nation_elos, away_nation_elos, 
                'nation_elo_K', k_values, match_info,
                k_draw_parameter, eta_home_advantage
            )
        
        # Update league ELOs
        if is_domestic:
            print("Updating league ELOs")
            updated_home_league, updated_away_league = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_league, updated_away_league, 
                'league_domestic_elo_K', k_values, match_info,
                k_draw_parameter, eta_home_advantage
            )
        
        if not is_same_league:
            print("Updating continental ELOs")
            updated_home_league, updated_away_league = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_league, updated_away_league, 
                'league_continental_elo_K', k_values, match_info,
                k_draw_parameter, eta_home_advantage
            )
        
        # Update club ELOs
        # General ELOs (all matches)
        print("Updating club ELOs")
        updated_home_club, updated_away_club = calculate_elo_ratings(
            conn, home_score, away_score, 
            updated_home_club, updated_away_club, 
            'elo_K', k_values, match_info, 
            k_draw_parameter, eta_home_advantage
        )
        
        # Home-specific ELOs
        print("Updating home ELOs")
        home_temp = updated_home_club.copy()
        updated_home_club, _ = calculate_elo_ratings(
            conn, home_score, away_score, 
            updated_home_club, home_temp,  # Use same dict to prevent away updates 
            'elo_home_matches_K', k_values, match_info, 
            k_draw_parameter, eta_home_advantage
        )
        
        # Away-specific ELOs
        print("Updating away ELOs")
        away_temp = updated_away_club.copy()
        _, updated_away_club = calculate_elo_ratings(
            conn, home_score, away_score, 
            away_temp, updated_away_club,  # Use same dict to prevent home updates
            'elo_away_matches_K', k_values, match_info, 
            k_draw_parameter, eta_home_advantage
        )
        
        # Domestic ELOs
        if is_same_nation:
            print("Updating domestic ELOs")
            print("Updating domestic ELOs")
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_domestic_K', k_values, match_info, 
                k_draw_parameter, eta_home_advantage
            )
        
        # Intraleague ELOs
        if is_same_league:
            print("Updating intra-league ELOs")
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_intraleague_K', k_values, match_info, 
                k_draw_parameter, eta_home_advantage
            )
        
        # International ELOs
        if is_continental:
            print("Updating international ELOs")
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_international_K', k_values, match_info, 
                k_draw_parameter, eta_home_advantage
            )
        
        result = 'home' if home_score > away_score else 'away' if home_score < away_score else 'draw'
        update_counter_table(conn, competition_id, result)

        update_club_elo(conn, home_team_id, updated_home_club)
        update_club_elo(conn, away_team_id, updated_away_club)
        update_league_elo(conn, home_main_comp_id, updated_home_league)
        update_league_elo(conn, away_main_comp_id, updated_away_league)
        update_nation_elo(conn, home_main_comp_country, updated_home_nation)
        update_nation_elo(conn, away_main_comp_country, updated_away_nation)

if __name__ == "__main__":
    conn = sqlite3.connect('v2db.sqlite')
    calculate_elos(conn)
