import pytest
import sqlite3
import json
from Data_Migration.oscar_SQLite_migration.migrate_jsons_to_sql import create_matches_table, insert_or_update_match_record

def test_create_matches_table():
    """Test to see if the table creation creates a table with all the columns specified in the schema"""
    conn = sqlite3.connect(":memory:")
    create_matches_table(conn)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(matches)")
    columns = cursor.fetchall()
    assert len(columns) == 32
    conn.close()

@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    create_matches_table(conn)
    yield conn
    conn.close()

def test_insert_or_update_match_workflow(test_db):
    """Test to see if the function inserts a record into the database and updates it correctly"""
    sample_ended_match = {
    'match_id': 'sr:match:12345',
    'start_time': '2024-03-15T20:00:00+00:00',
    'competition_id': 'sr:competition:45',
    'competition_name': 'Premier League',
    'competition_season_id': 'sr:season:12345',
    'competition_season_name': 'Premier League 23/24',
    'season_start_date': '2023-08-11',
    'season_end_date': '2024-05-19',
    'round_info': '{"number": 28}',
    'home_team_id': 'sr:team:123',
    'home_team_name': 'Manchester United',
    'away_team_id': 'sr:team:456',
    'away_team_name': 'Liverpool',
    'venue_id': 'sr:venue:789',
    'venue_name': 'Old Trafford',
    'venue_capacity': 74140,
    'status': 'completed',
    'match_status': 'ended',
    'home_score': 5,
    'away_score': 2,
    'period_scores': [
        {'home_score': 1, 'away_score': 0, 'type': 'regular_period', 'number': 1},
        {'home_score': 1, 'away_score': 1, 'type': 'regular_period', 'number': 2}
    ],
    'winner_id': 'sr:team:123',
    'home_team_stats': {
        'possession_percentage': 55,
        'shots_on_target': 6,
        'shots_off_target': 8,
        'corners': 7
    },
    'home_team_player_stats': [
        {'player_id': 'sr:player:1', 'name': 'Marcus Rashford', 'goals': 1, 'assists': 1},
        {'player_id': 'sr:player:2', 'name': 'Bruno Fernandes', 'goals': 1, 'assists': 0}
    ],
    'away_team_stats': {
        'possession_percentage': 45,
        'shots_on_target': 4,
        'shots_off_target': 6,
        'corners': 5
    },
    'away_team_player_stats': [
        {'player_id': 'sr:player:3', 'name': 'Mohamed Salah', 'goals': 1, 'assists': 0},
        {'player_id': 'sr:player:4', 'name': 'Darwin Nunez', 'goals': 0, 'assists': 1}
    ]
}
    sample_ended_lineups = {
    'match_id': 'sr:match:12345',
    'start_time': '2024-03-15T20:00:00+00:00',
    'competition_id': 'sr:competition:45',
    'competition_name': 'Premier League',
    'competition_season_id': 'sr:season:12345',
    'competition_season_name': 'Premier League 23/24',
    'season_start_date': '2023-08-11',
    'season_end_date': '2024-05-19',
    'round_info': '{"number": 28}',
    'home_team_id': 'sr:team:123',
    'home_team_name': 'Manchester United',
    'away_team_id': 'sr:team:456',
    'away_team_name': 'Liverpool',
    'venue_id': 'sr:venue:789',
    'venue_name': 'Old Trafford',
    'venue_capacity': 74140,
    'status': 'completed',
    'match_status': 'ended',
    'home_score': 2,
    'away_score': 1,
    'period_scores': [
        {'home_score': 1, 'away_score': 0, 'type': 'regular_period', 'number': 1},
        {'home_score': 1, 'away_score': 1, 'type': 'regular_period', 'number': 2}
    ],
    'winner_id': 'sr:team:123',
    'home_team_lineup_info': [
        {'player_id': 'sr:player:1', 'name': 'Marcus Rashford', 'position': 'forward', 'shirt_number': 10},
        {'player_id': 'sr:player:2', 'name': 'Bruno Fernandes', 'position': 'midfielder', 'shirt_number': 8},
        {'player_id': 'sr:player:3', 'name': 'Steve wright', 'position': 'forward', 'shirt_number': 12},
        {'player_id': 'sr:player:4', 'name': 'James Kinnaird', 'position': 'midfielder', 'shirt_number': 7}
    ],
    'home_team_manager_info': {
        'id': 'sr:manager:123',
        'name': 'Erik ten Hag',
        'nationality': 'Netherlands'
    },
    'home_team_formation': '4-3-3',
    'away_team_lineup_info': [
        {'player_id': 'sr:player:3', 'name': 'Mohamed Salah', 'position': 'forward', 'shirt_number': 11},
        {'player_id': 'sr:player:4', 'name': 'Darwin Nunez', 'position': 'forward', 'shirt_number': 9}
    ],
    'away_team_manager_info': {
        'id': 'sr:manager:456',
        'name': 'Jurgen Klopp',
        'nationality': 'Germany'
    },
    'away_team_formation': '4-3-3'
}
    sample_future_lineups2 = {
    'match_id': 'sr:match:12346',
    'start_time': '2024-03-15T20:00:00+00:00',
    'competition_id': 'sr:competition:45',
    'competition_name': 'Premier League',
    'competition_season_id': 'sr:season:12345',
    'competition_season_name': 'Premier League 23/24',
    'season_start_date': '2023-08-11',
    'season_end_date': '2024-05-19',
    'round_info': '{"number": 28}',
    'home_team_id': 'sr:team:123',
    'home_team_name': 'Manchester United',
    'away_team_id': 'sr:team:456',
    'away_team_name': 'Liverpool',
    'venue_id': 'sr:venue:789',
    'venue_name': 'Old Trafford',
    'venue_capacity': 74140,
    'status': 'not_started',
    'match_status': 'not_started',
    'home_score': None,
    'away_score': None,
    'period_scores': None,
    'winner_id': None,
    'home_team_lineup_info': [
        {'player_id': 'sr:player:1', 'name': 'Marcus Rashford', 'position': 'forward', 'shirt_number': 10},
        {'player_id': 'sr:player:2', 'name': 'Bruno Fernandes', 'position': 'midfielder', 'shirt_number': 8}
    ],
    'home_team_manager_info': {
        'id': 'sr:manager:123',
        'name': 'Erik ten Hag',
        'nationality': 'Netherlands'
    },
    'home_team_formation': '4-3-3',
    'away_team_lineup_info': [
        {'player_id': 'sr:player:3', 'name': 'Mohamed Salah', 'position': 'forward', 'shirt_number': 11},
        {'player_id': 'sr:player:4', 'name': 'Darwin Nunez', 'position': 'forward', 'shirt_number': 9}
    ],
    'away_team_manager_info': {
        'id': 'sr:manager:456',
        'name': 'Jurgen Klopp',
        'nationality': 'Germany'
    },
    'away_team_formation': '4-3-3'
}
    sample_ended_match2 = {
    'match_id': 'sr:match:12346',
    'start_time': '2024-03-15T20:00:00+00:00',
    'competition_id': 'sr:competition:45',
    'competition_name': 'Premier League',
    'competition_season_id': 'sr:season:12345',
    'competition_season_name': 'Premier League 23/24',
    'season_start_date': '2023-08-11',
    'season_end_date': '2024-05-19',
    'round_info': '{"number": 28}',
    'home_team_id': 'sr:team:123',
    'home_team_name': 'Manchester United',
    'away_team_id': 'sr:team:456',
    'away_team_name': 'Liverpool',
    'venue_id': 'sr:venue:789',
    'venue_name': 'Old Trafford',
    'venue_capacity': 74140,
    'status': 'completed',
    'match_status': 'ended',
    'home_score': 2,
    'away_score': 1,
    'period_scores': [
        {'home_score': 1, 'away_score': 0, 'type': 'regular_period', 'number': 1},
        {'home_score': 1, 'away_score': 1, 'type': 'regular_period', 'number': 2}
    ],
    'winner_id': 'sr:team:123',
    'home_team_stats': {
        'possession_percentage': 55,
        'shots_on_target': 6,
        'shots_off_target': 8,
        'corners': 7
    },
    'home_team_player_stats': [
        {'player_id': 'sr:player:1', 'name': 'Marcus Rashford', 'goals': 1, 'assists': 1},
        {'player_id': 'sr:player:2', 'name': 'Bruno Fernandes', 'goals': 1, 'assists': 0}
    ],
    'away_team_stats': {
        'possession_percentage': 45,
        'shots_on_target': 4,
        'shots_off_target': 6,
        'corners': 5
    },
    'away_team_player_stats': [
        {'player_id': 'sr:player:3', 'name': 'Mohamed Salah', 'goals': 1, 'assists': 0},
        {'player_id': 'sr:player:4', 'name': 'Darwin Nunez', 'goals': 0, 'assists': 1}
    ]
}
    sample_ended_lineups2 = {'match_id': 'sr:match:12346',
    'start_time': '2024-03-15T20:00:00+00:00',
    'competition_id': 'sr:competition:45',
    'competition_name': 'Premier League',
    'competition_season_id': 'sr:season:12345',
    'competition_season_name': 'Premier League 23/24',
    'season_start_date': '2023-08-11',
    'season_end_date': '2024-05-19',
    'round_info': '{"number": 28}',
    'home_team_id': 'sr:team:123',
    'home_team_name': 'Manchester United',
    'away_team_id': 'sr:team:456',
    'away_team_name': 'Liverpool',
    'venue_id': 'sr:venue:789',
    'venue_name': 'Old Trafford',
    'venue_capacity': 74140,
    'status': 'completed',
    'match_status': 'ended',
    'home_score': 2,
    'away_score': 1,
    'period_scores': [
        {'home_score': 1, 'away_score': 0, 'type': 'regular_period', 'number': 1},
        {'home_score': 1, 'away_score': 1, 'type': 'regular_period', 'number': 2}
    ],
   'winner_id': 'sr:team:123',
    'home_team_lineup_info': [
        {'player_id': 'sr:player:1', 'name': 'Marcus Rashford', 'position': 'forward', 'shirt_number': 10},
        {'player_id': 'sr:player:2', 'name': 'Bruno Fernandes', 'position': 'midfielder', 'shirt_number': 8},
        {'player_id': 'sr:player:3', 'name': 'Steve wright', 'position': 'forward', 'shirt_number': 12},
        {'player_id': 'sr:player:4', 'name': 'James Kinnaird', 'position': 'midfielder', 'shirt_number': 7}
    ],
    'home_team_manager_info': {
        'id': 'sr:manager:123',
        'name': 'Erik ten Hag',
        'nationality': 'Netherlands'
    },
    'home_team_formation': '4-3-3',
    'away_team_lineup_info': [
        {'player_id': 'sr:player:3', 'name': 'Mohamed Salah', 'position': 'forward', 'shirt_number': 11},
        {'player_id': 'sr:player:4', 'name': 'Darwin Nunez', 'position': 'forward', 'shirt_number': 9},
        {'player_id': 'sr:player:5', 'name': 'Steve wright', 'position': 'forward', 'shirt_number': 12},
        {'player_id': 'sr:player:6', 'name': 'James Kinnaird', 'position': 'midfielder', 'shirt_number': 7}
    ],
    'away_team_manager_info': {
        'id': 'sr:manager:456',
        'name': 'Jurgen Klopp',
        'nationality': 'Germany'
    },
    'away_team_formation': '4-3-3'
}
    
    #INSERT 1: Match in the future ('not started') potential lineups but no stats..
    insert_or_update_match_record(test_db, sample_future_lineups2)

    cursor = test_db.cursor()
    cursor.execute("""
        SELECT match_id, home_team_name, away_team_name, home_score, 
               home_team_lineup_info, away_team_lineup_info, 
               home_team_stats, away_team_stats, status 
        FROM matches 
        WHERE match_id=?
    """, (sample_future_lineups2['match_id'],))
    result = cursor.fetchone()

    assert result[0] == sample_future_lineups2['match_id']
    assert result[1] == sample_future_lineups2['home_team_name']
    assert result[2] == sample_future_lineups2['away_team_name']
    assert result[3] == None
    # Compare parsed JSON objects instead of strings
    assert json.loads(result[4]) == sample_future_lineups2['home_team_lineup_info']
    assert json.loads(result[5]) == sample_future_lineups2['away_team_lineup_info']
    assert result[6] == None
    assert result[7] == None
    assert result[8] == 'not_started'

    #UPDATE 2: Match that has been completed, same ID as INSERT 1. Now we should have match stats and lineups
    insert_or_update_match_record(test_db, sample_ended_match2)

    cursor.execute("""
        SELECT match_id, home_team_name, away_team_name, home_score, 
               home_team_lineup_info, away_team_lineup_info, 
               home_team_stats, away_team_stats, status 
        FROM matches 
        WHERE match_id=?
    """, (sample_ended_match2['match_id'],))
    result = cursor.fetchone()

    assert result[0] == sample_ended_match2['match_id']
    assert result[1] == sample_ended_match2['home_team_name']
    assert result[2] == sample_ended_match2['away_team_name']
    assert result[3] == sample_ended_match2['home_score']
    # Compare parsed JSON objects instead of strings
    assert json.loads(result[4]) == sample_future_lineups2['home_team_lineup_info']
    assert json.loads(result[5]) == sample_future_lineups2['away_team_lineup_info']
    assert json.loads(result[6]) == sample_ended_match2['home_team_stats']
    assert json.loads(result[7]) == sample_ended_match2['away_team_stats']
    assert result[8] == 'completed'

    #UPDATE 3: Match that has been completed, now we have confirmed lineups which should update the potential lineups we has already.
    insert_or_update_match_record(test_db, sample_ended_lineups2)

    cursor.execute("""
        SELECT match_id, home_team_name, away_team_name, home_score, 
               home_team_lineup_info, away_team_lineup_info, 
               home_team_stats, away_team_stats, status 
        FROM matches 
        WHERE match_id=?
    """, (sample_ended_match2['match_id'],))
    result = cursor.fetchone()

    assert result[0] == sample_ended_match2['match_id']
    assert result[1] == sample_ended_match2['home_team_name']
    assert result[2] == sample_ended_match2['away_team_name']
    assert result[3] == sample_ended_match2['home_score']
    # Compare parsed JSON objects instead of strings
    assert json.loads(result[4]) == sample_ended_lineups2['home_team_lineup_info']
    assert json.loads(result[5]) == sample_ended_lineups2['away_team_lineup_info']
    assert json.loads(result[4]) != sample_future_lineups2['home_team_lineup_info']
    assert json.loads(result[5]) != sample_future_lineups2['away_team_lineup_info']
    assert json.loads(result[6]) == sample_ended_match2['home_team_stats']
    assert json.loads(result[7]) == sample_ended_match2['away_team_stats']
    assert result[8] == 'completed'

    #INSERT 4: Match that has been completed, only has match stats and no lineups
    insert_or_update_match_record(test_db, sample_ended_match)

    cursor.execute("""
        SELECT match_id, home_team_name, away_team_name, home_score, 
               home_team_lineup_info, away_team_lineup_info, 
               home_team_stats, away_team_stats, status 
        FROM matches 
        WHERE match_id=?
    """, (sample_ended_match['match_id'],))
    result = cursor.fetchone()

    assert result[0] == sample_ended_match['match_id']
    assert result[0] != sample_ended_match2['match_id']
    assert result[1] == sample_ended_match['home_team_name']
    assert result[2] == sample_ended_match['away_team_name']
    assert result[3] == sample_ended_match['home_score']
    assert result[4] == None
    assert result[5] == None
    assert json.loads(result[6]) == sample_ended_match['home_team_stats']
    assert json.loads(result[7]) == sample_ended_match['away_team_stats']
    assert result[8] == 'completed'
    # Compare parsed JSON objects instead of strings










    






