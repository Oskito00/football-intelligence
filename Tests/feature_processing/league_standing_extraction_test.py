from utils.database_helpers.get_and_set_functions import get_from_matches
from data_processing.helpers.league_standings.league_standings import find_new_stats, find_team_standing

def test_find_new_stats():
    """Unit test for find_new_stats function"""
    home_team_stats = [7,10,7,3,0,10,5,5,24]
    away_team_stats = [20,10,3,0,7,5,10,-5,9]
    home_score = 3
    away_score = 1
    new_stats = find_new_stats(home_team_stats, away_team_stats, home_score, away_score)
    print(new_stats)
    new_home_stats = new_stats[0]
    new_away_stats = new_stats[1]
    assert new_home_stats == [11,8,3,0,13,6,7,27]
    assert new_away_stats == [11,3,0,8,6,13,-7,9]

def test_find_team_standing():
    """Unit test for find_team_standing function"""
    league_info = [['72', 10, 7, 3, 0, 10, 5, 5, 24], ['73', 10, 7, 3, 0, 10, 5, 5, 24], ['74', 10, 7, 3, 0, 10, 5, 5, 24]]
    assert find_team_standing('73', league_info) == 2
    assert find_team_standing('74', league_info) == 3


def test_league_standing_extraction_full_process(conn):
    print("Started running test...")
    matches = get_from_matches(conn, select_str='SELECT DISTINCT', columns=['match_id', 'start_time','competition_season_id', 'round_info', 'home_team_id', 'away_team_id', 'home_score', 'away_score'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0', order_by='datetime(start_time)')
    # extract_league_standings(conn, matches) # Uncomment this if running the full process for the first time

    print(f"Got {len(matches)} matches")
    # extract_league_standings(conn, matches)

    # Check if the league standings table is populated
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM league_standings")
    assert cursor.fetchone()[0] > 0

    # Check if the league standings history table is populated
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM league_standings_history")
    assert cursor.fetchone()[0] > 0

    # Check a match in the league standings history to check if the stats are correct.
    match_id = 201
    cursor.execute("SELECT home_standing, away_standing, home_points, away_points, home_goal_difference, away_goal_difference FROM league_standings_history WHERE match_id = ?", (match_id,))
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == 2
    assert result[1] == 6
    assert result[2] == 33
    assert result[3] == 22
    assert result[4] == 21
    assert result[5] == 5


