import pytest
import sqlite3
from Fifa_Ratings.deepseek_help_scraping import set_no_ai_data_flag

@pytest.fixture
def test_db():
    """Fixture that creates an in-memory database with test data"""
    conn = sqlite3.connect(':memory:')
    conn.execute('''
        CREATE TABLE player_stats (
            player_id INT PRIMARY KEY, 
            player_name TEXT,
            player_formatted_name TEXT,
            height TEXT,
            weight TEXT,
            pace_avg INT,
            acceleration INT,
            sprint_speed INT,
            shooting_avg INT,
            positioning INT,
            finishing INT,
            shot_power INT,
            long_shots INT,
            volleys INT,
            penalties INT,
            passing_avg INT,
            vision INT,
            crossing INT,
            free_kick_accuracy INT,
            short_passing INT,
            long_passing INT,
            curve INT,
            dribbling_avg INT,
            agility INT,
            reactions INT,
            balance INT,
            dribbling INT,
            ball_control INT,
            composure INT,
            defense_avg INT,
            interceptions INT,
            heading_accuracy INT,
            def_awareness INT,
            standing_tackle INT,
            sliding_tackle INT,
            physicality_avg INT,
            jumping INT,
            stamina INT,
            strength INT,
            aggression INT,
            goalkeeping_avg INT,
            gk_diving INT,
            gk_handling INT,
            gk_kicking INT,
            gk_positioning INT,
            gk_reflexes INT,
            skill_moves INT,
            total_attributes INT,
            no_ai_data INT,
            found_with_AI INT
        )''')
    conn.execute("INSERT INTO player_stats (player_id, no_ai_data) VALUES (1, 0)")
    conn.commit()
    yield conn
    conn.close()

def test_set_no_ai_data_flag_true(test_db):
    set_no_ai_data_flag(1, True, test_db)
    result = test_db.execute("SELECT no_ai_data FROM player_stats WHERE id = 1").fetchone()
    assert result[0] == 1

def test_set_no_ai_data_flag_false(test_db):
    set_no_ai_data_flag(1, False, test_db)
    result = test_db.execute("SELECT no_ai_data FROM player_stats WHERE id = 1").fetchone()
    assert result[0] == 0

def test_flag_only_affects_target_player(test_db):
    # Add second test player
    test_db.execute("INSERT INTO player_stats VALUES (2, 0)")
    test_db.commit()
    
    set_no_ai_data_flag(1, True, test_db)
    
    # Check original player updated
    result1 = test_db.execute("SELECT no_ai_data FROM player_stats WHERE id = 1").fetchone()
    # Check other player remains unchanged
    result2 = test_db.execute("SELECT no_ai_data FROM player_stats WHERE id = 2").fetchone()
    
    assert result1[0] == 1
    assert result2[0] == 0
