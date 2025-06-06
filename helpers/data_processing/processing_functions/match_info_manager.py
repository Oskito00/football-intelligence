import math
import psycopg2


class MatchInfoManager:
    def __init__(self, conn, matches):
        self.conn = conn
        self.matches = matches
        self.competition_history_data = []

    def __enter__(self):

        return self

    def process_match(self, match):
        match_id = match['match_id']
        start_time = match['start_time']
        competition_season_name = match['competition_season_name']
        competition_id = match['competition_id']
        competition_name = match['competition_name']
        competition_country = match['competition_country']
        home_team_name = match['home_team_name']
        away_team_name = match['away_team_name']
        self.competition_history_data.append((match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, home_team_name, away_team_name))

        ...


    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Insert collected match info data to match_info_history table upon context manager exit.
        Ignores conflicts since match data is historical and won't change.
        """
        if exc_type is not None:
            self.conn.rollback()
            return False

        cursor = self.conn.cursor()
        try:
            cursor.executemany('''
                INSERT INTO match_info_history (
                    match_id, 
                    start_time, 
                    competition_season_name, 
                    competition_id, 
                    competition_name, 
                    competition_country, 
                    home_team_name, 
                    away_team_name
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
                ON CONFLICT DO NOTHING
            ''', self.competition_history_data)
            
            self.conn.commit()
            
        except Exception as e:
            print(f"Error inserting match info data: {str(e)}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()

        return False
