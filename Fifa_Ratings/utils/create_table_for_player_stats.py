
import sqlite3


def create_players_stats_table(conn):
    """Create table if not exists"""
    conn.execute('''CREATE TABLE IF NOT EXISTS player_stats (
        player_id TEXT PRIMARY KEY,
        player_name TEXT,
        player_formatted_name TEXT,
        -- Physical Section
        height TEXT,
        weight TEXT,
                 
        -- Pace Section
        pace_avg INTEGER,
        acceleration INTEGER,
        sprint_speed INTEGER,
        
        -- Shooting Section
        shooting_avg INTEGER,
        positioning INTEGER,
        finishing INTEGER,
        shot_power INTEGER,
        long_shots INTEGER,
        volleys INTEGER,
        penalties INTEGER,
        
        -- Passing Section
        passing_avg INTEGER,
        vision INTEGER,
        crossing INTEGER,
        free_kick_accuracy INTEGER,
        short_passing INTEGER,
        long_passing INTEGER,
        curve INTEGER,
        
        -- Dribbling Section
        dribbling_avg INTEGER,
        agility INTEGER,
        reactions INTEGER,
        balance INTEGER,
        dribbling INTEGER,
        ball_control INTEGER,
        composure INTEGER,
        
        -- Defense Section
        defense_avg INTEGER,
        interceptions INTEGER,
        heading_accuracy INTEGER,
        def_awareness INTEGER,
        standing_tackle INTEGER,
        sliding_tackle INTEGER,
        
        -- Physicality Section
        physicality_avg INTEGER,
        jumping INTEGER,
        stamina INTEGER,
        strength INTEGER,
        aggression INTEGER,
        
        -- Goalkeeping Section
        goalkeeping_avg INTEGER,
        gk_diving INTEGER,
        gk_handling INTEGER,
        gk_kicking INTEGER,
        gk_positioning INTEGER,
        gk_reflexes INTEGER,
        
        -- Special Fields
        total_attributes INTEGER,
        skill_moves INTEGER,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')


print("Trying to create table")
conn = sqlite3.connect('v2db.sqlite')
create_players_stats_table(conn)
conn.close()