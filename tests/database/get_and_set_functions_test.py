
from football_intelligence.database import get_from_matches

def test_get_all_from_matches(conn):
    matches = get_from_matches(conn, select_str='SELECT DISTINCT', columns=['match_id', 'start_time', 'competition_season_name', 'competition_id', 'competition_name', 'competition_country', 'home_team_id', 'home_team_name', 'away_team_id', 'away_team_name', 
               'home_score', 'away_score', 'home_team_domestic_league_id', 'home_team_domestic_country', 'away_team_domestic_league_id', 'away_team_domestic_country'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0', order_by='datetime(start_time)')

    assert len(matches) > 0
    assert len(matches) <= 10


def test_get_all_formations(conn):
    matches = get_from_matches(conn, select_str='SELECT', columns=['match_id', 'home_team_formation', 'away_team_formation'], where_clause='home_team_formation IS NOT NULL AND away_team_formation IS NOT NULL AND home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0')
    assert len(matches) > 0
    assert len(matches) == 10

def test_get_all_stage_of_season(conn):
    matches = get_from_matches(conn, select_str='SELECT', columns=['match_id', 'start_time', 'season_start_date', 'season_end_date'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0')
    print(type(matches))
    assert len(matches) > 0
    assert len(matches) == 10

def test_get_all_fatigue(conn):
    matches = get_from_matches(conn, select_str='SELECT', columns=['match_id', 'start_time', 'home_team_id', 'away_team_id'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0')
    print(type(matches))
    assert len(matches) > 0
    assert len(matches) == 10