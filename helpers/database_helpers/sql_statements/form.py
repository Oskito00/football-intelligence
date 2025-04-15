import sqlite3
import json


def get_last_n_matches_for_team(conn, team_id, start_time, n=50):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT json_group_array(
            json_object(
                'goals_scored', goals_scored,
                'goals_conceded', goals_conceded,
                'result', result,
                'is_home', is_home,
                'is_intraleague_match', is_intraleague_match,
                'is_domestic_cup_match', is_domestic_cup_match,
                'is_continental_cup_match', is_continental_cup_match
            )
        )
        FROM (
            SELECT result, goals_scored, goals_conceded, is_home, is_intraleague_match, is_domestic_cup_match, is_continental_cup_match
            FROM TeamMatchHistory
            WHERE team_id = ?
            AND start_time < ?
            ORDER BY start_time DESC
            LIMIT ?
        )
    """, (team_id, start_time, n))
    
    result = cursor.fetchone()
    if result and result[0]:
        return json.loads(result[0])
    return []

def calulate_form_stats_in_last_n_matches(previous_matches, n):
    pass