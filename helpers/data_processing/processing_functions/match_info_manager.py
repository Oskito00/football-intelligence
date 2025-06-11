import math
import psycopg2


class MatchInfoManager:
    def __init__(self, conn, matches, mode='training'):
        self.conn = conn
        self.matches = matches
        self.mode = mode  # 'training' or 'inference'
        self.competition_history_data = []
        self.future_match_info_data = []  # For inference mode

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
        
        if self.mode == 'training':
            # Store for match_info_history table
            self.competition_history_data.append((match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, home_team_name, away_team_name))
        elif self.mode == 'inference':
            # Store for future match info table (or whatever features you need)
            self.future_match_info_data.append((match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, home_team_name, away_team_name))

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
            if self.mode == 'training':
                # Insert into match_info_history for training
                cursor.executemany('''
                    INSERT INTO match_info_history (
                        match_id, start_time, competition_season_name, 
                        competition_id, competition_name, competition_country, 
                        home_team_name, away_team_name
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
                    ON CONFLICT DO NOTHING
                ''', self.competition_history_data)
                
            elif self.mode == 'inference':
                # Insert into future match info table for inference
                cursor.executemany('''
                    INSERT INTO match_info_future (
                        match_id, start_time, competition_season_name, 
                        competition_id, competition_name, competition_country, 
                        home_team_name, away_team_name
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
                    ON CONFLICT DO NOTHING
                ''', self.future_match_info_data)
            
            self.conn.commit()
            
        except Exception as e:
            print(f"Error inserting match info data: {str(e)}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()

        return False
