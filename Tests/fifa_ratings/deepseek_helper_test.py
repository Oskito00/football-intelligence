import pytest
from unittest.mock import Mock, patch
import sqlite3

from fifa_ratings.deepseek_player_scraping import scrape_and_process_player

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
    conn.commit()
    yield conn
    conn.close()

def test_scrape_and_process_player_success(test_db):
    mock_ds = Mock()
    mock_response = Mock()
    
    with patch('Fifa_Ratings.deepseek_help_scraping.scrape_player_ratings') as mock_scrape, \
         patch('Fifa_Ratings.deepseek_help_scraping.parse_html_to_json') as mock_parse:
        
        # Configure mock DeepSeek response
        mock_ds.create_chat_completion.return_value = "john-d,john-do,j-doe"
        
        # First slug returns 404, second succeeds
        mock_scrape.side_effect = [
            Mock(status_code=404, url="https://www.fifaratings.com/bad-slug"),
            Mock(status_code=200, url="https://www.fifaratings.com/john-do", text="<html>data</html>"),
            Mock(status_code=404, url="https://www.fifaratings.com/bad-slug2")
        ]
        
        # Mock parsed data
        mock_parse.return_value = {
            'Acceleration': 85,
            'Height': "5'11\"",
            'Weight': "170lbs"
        }
        
        # Run the test
        print("Running test")
        scrape_and_process_player(mock_ds, 'Doe, John', 'john-doe', 1, test_db)
        print("Test complete")

        
        # Verify database updates
        print("Verifying database updates")

        result = test_db.execute("SELECT no_ai_data, acceleration FROM player_stats WHERE player_id = 1").fetchone()
        assert result[0] == 0  # Flag should be unset after success
        assert result[1] == 85  # Acceleration from mock data

def test_scrape_and_process_player_no_data(test_db):
    mock_ds = Mock()
    
    with patch('Fifa_Ratings.deepseek_help_scraping.scrape_player_ratings') as mock_scrape:
        mock_ds.create_chat_completion.return_value = "bad-slug1,bad-slug2"
        mock_scrape.return_value = Mock(status_code=404, url="https://www.fifaratings.com/bad-slug")
        
        scrape_and_process_player(mock_ds, 'Doe, John', 'john-doe', 1, test_db)
        
        result = test_db.execute("SELECT no_ai_data FROM player_stats WHERE id = 1").fetchone()
        assert result[0] == 1  # Flag should be set after all failures
