import sqlite3
from Tools.elo_helpers import calculate_elo_ratings, elo_formula, get_club_elo, get_league_elo, get_nation_elo, save_elo_history, update_club_elo, update_league_elo, update_nation_elo
from Tools.Database_helpers.get_and_set_functions import get_all_matches

def calculate_elos(conn):
    matches = get_all_matches(conn)
    for match in matches:
        print("Processing match: ", match[0])
        match_id, start_time, competition_id, competition_name, home_team_id, home_team_name, away_team_id, away_team_name, \
        home_score, away_score, home_main_comp_id, home_main_comp_country, \
        away_main_comp_id, away_main_comp_country = match
        
        # Determine if match is domestic or international
        is_same_nation = (home_main_comp_country == away_main_comp_country)
        is_same_league = home_main_comp_id == away_main_comp_id
        is_domestic = is_same_nation and not is_same_league
        # NOTE: For different datasets the competitions might be named differently.
        continental_comps = ['UEFA Champions League', 'UEFA Europa League', 'UEFA Europa Conference League']
        is_continental = competition_name in continental_comps
        
        # Get all ELO ratings for both teams
        home_club_elos = get_club_elo(conn, home_team_id, home_team_name)
        away_club_elos = get_club_elo(conn, away_team_id, away_team_name)

        home_nation_elos = get_nation_elo(conn, home_main_comp_country) if home_main_comp_country else None
        away_nation_elos = get_nation_elo(conn, away_main_comp_country) if away_main_comp_country else None

        home_league_elos = get_league_elo(conn, home_main_comp_id) if home_main_comp_id else None
        away_league_elos = get_league_elo(conn, away_main_comp_id) if away_main_comp_id else None

        # Save the current ELOs to elo_history
        save_elo_history(conn, match_id, home_team_id, away_team_id, home_club_elos, away_club_elos, home_nation_elos, away_nation_elos, home_league_elos, away_league_elos, home_score, away_score)
   
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
            updated_home_nation, updated_away_nation = calculate_elo_ratings(
                conn, home_score, away_score, 
                home_nation_elos, away_nation_elos, 
                'nation_elo_K', k_values, match_info
            )
        
        # Update league ELOs
        if is_domestic:
            updated_home_league, updated_away_league = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_league, updated_away_league, 
                'league_domestic_elo_K', k_values, match_info
            )
        
        if not is_same_league:
            updated_home_league, updated_away_league = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_league, updated_away_league, 
                'league_continental_elo_K', k_values, match_info
            )
        
        # Update club ELOs
        # General ELOs (all matches)
        updated_home_club, updated_away_club = calculate_elo_ratings(
            conn, home_score, away_score, 
            updated_home_club, updated_away_club, 
            'elo_K', k_values, match_info
        )
        
        # Home-specific ELOs
        home_temp = updated_home_club.copy()
        updated_home_club, _ = calculate_elo_ratings(
            conn, home_score, away_score, 
            updated_home_club, home_temp,  # Use same dict to prevent away updates 
            'elo_home_matches_K', k_values, match_info
        )
        
        # Away-specific ELOs
        away_temp = updated_away_club.copy()
        _, updated_away_club = calculate_elo_ratings(
            conn, home_score, away_score, 
            away_temp, updated_away_club,  # Use same dict to prevent home updates
            'elo_away_matches_K', k_values, match_info
        )
        
        # Domestic ELOs
        if is_same_nation:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_domestic_K', k_values, match_info
            )
        
        # Intraleague ELOs
        if is_same_league:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_intraleague_K', k_values, match_info
            )
        
        # International ELOs
        if is_continental:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                conn, home_score, away_score, 
                updated_home_club, updated_away_club, 
                'elo_international_K', k_values, match_info
            )

        update_club_elo(conn, home_team_id, updated_home_club)
        update_club_elo(conn, away_team_id, updated_away_club)
        update_league_elo(conn, home_main_comp_id, updated_home_league)
        update_league_elo(conn, away_main_comp_id, updated_away_league)
        update_nation_elo(conn, home_main_comp_country, updated_home_nation)
        update_nation_elo(conn, away_main_comp_country, updated_away_nation)

if __name__ == "__main__":
    conn = sqlite3.connect('v2db.sqlite')
    calculate_elos(conn)
