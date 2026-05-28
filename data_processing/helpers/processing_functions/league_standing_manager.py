from football_intelligence.database import get_from_matches, get_from_standings
from data_processing.helpers.league_standings.league_standings import find_team_standing, save_to_standings_history, upsert_into_standings


#TODO: Change this to make use of a context manager
# Save standings in memory and then insert into the database in batches

def extract_league_standings(conn):
    print("**********Running League Standings Extraction**********")

    matches = get_from_matches(conn, select_str='SELECT DISTINCT', columns=['match_id', 'start_time','competition_season_id', 'round_info', 'home_team_id', 'away_team_id', 'home_score', 'away_score'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = false', order_by='start_time')

    standings_history = []
    BATCH_SIZE = 10000
    match_count = 0

    for match in matches: 
        match_id, start_time, competition_season_id, round_info, home_team_id, away_team_id, home_score, away_score = match
        if round_info.startswith('Regular Season'):
            league_info = get_from_standings(conn, select_str='SELECT', columns=['team_id','matches_played', 'wins', 'draws', 'losses', 'goals_for', 'goals_against', 'goal_difference', 'points'], where_clause='competition_season_id = %s', where_clause_args=[competition_season_id])
            if match_count % 10000 == 0:
                print(f"Processing match {match_count} out of {len(matches)}")
            match_count += 1
            if len(league_info) == 0:
                home_team_stats = [-1] + [0] * 8
                away_team_stats = [-1] + [0] * 8

            else:
                league_info.sort(key=lambda x: (-x[8], -x[7], -x[6], -x[5]))

                home_team_standing = find_team_standing(home_team_id, league_info)
                away_team_standing = find_team_standing(away_team_id, league_info)
                home_team_stats = [home_team_standing] + list(league_info[home_team_standing-1][1:]) if home_team_standing else [-1] + [0] * 8
                away_team_stats = [away_team_standing] + list(league_info[away_team_standing-1][1:]) if away_team_standing else [-1] + [0] * 8

            
            standings = [match_id] + home_team_stats + away_team_stats
            standings_history.append(standings)

            if len(standings_history) >= BATCH_SIZE:
                print("Batch limit reached, saving to database")
                save_to_standings_history(conn, standings_history)
                standings_history = []

            #Now we need to upsert into the standings table
            upsert_into_standings(conn, home_team_id, away_team_id, home_team_stats, away_team_stats, competition_season_id, home_score, away_score)
        
        else:
            continue

    if len(standings_history) > 0:
        print("Saving remaining standings to history in last batch")
        save_to_standings_history(conn, standings_history)