import sqlite3
import pytest

@pytest.fixture
def conn():
    conn = sqlite3.connect(':memory:')
    conn.execute(
        '''
        CREATE TABLE matches (
            match_id INTEGER PRIMARY KEY,
            start_time TEXT,
            competition_season_name TEXT,
            competition_id INTEGER,
            competition_name TEXT,
            competition_country TEXT,
            home_team_id INTEGER,
            home_team_name TEXT,
            away_team_id INTEGER,
            away_team_name TEXT,
            home_score INTEGER,
            away_score INTEGER,
            home_team_domestic_league_id INTEGER,
            home_team_domestic_country TEXT,
            away_team_domestic_league_id INTEGER,
            away_team_domestic_country TEXT,
            home_team_formation TEXT,
            away_team_formation TEXT,
            season_start_date TEXT,
            season_end_date TEXT,
            is_processed INTEGER
        )
        '''
    )
    rows = [
        (
            match_id,
            f'2025-01-{match_id:02d}T12:00:00',
            '2024/2025',
            1000,
            'Premier League',
            'England',
            100 + match_id,
            f'Home {match_id}',
            200 + match_id,
            f'Away {match_id}',
            2,
            1,
            10,
            'England',
            10,
            'England',
            '4-3-3',
            '4-2-3-1',
            '2024-08-01',
            '2025-05-31',
            0,
        )
        for match_id in range(1, 11)
    ]
    conn.executemany(
        '''
        INSERT INTO matches (
            match_id,
            start_time,
            competition_season_name,
            competition_id,
            competition_name,
            competition_country,
            home_team_id,
            home_team_name,
            away_team_id,
            away_team_name,
            home_score,
            away_score,
            home_team_domestic_league_id,
            home_team_domestic_country,
            away_team_domestic_league_id,
            away_team_domestic_country,
            home_team_formation,
            away_team_formation,
            season_start_date,
            season_end_date,
            is_processed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        rows,
    )
    try:
        yield conn
    finally:
        conn.close()
