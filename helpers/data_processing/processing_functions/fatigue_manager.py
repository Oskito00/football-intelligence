from datetime import datetime, timedelta

#TODO: MAKE FASTER: The code here is just a placeholder so that one can use it as an idea for their better implementation 
# This is very slow as it is not properly making use of managing match contexts We could keep track of
# recent matches for a team, store them in memory and then append to the list instead of querying the database
# for each match.

class FatigueManager:
    def __init__(self, conn, matches):
        self.conn = conn
        self.matches = matches
        self.fatigue_data = []

    def __enter__(self):
        return self

    def process_match(self, match):
        """Process a single match to calculate fatigue metrics"""
        match_id = match['match_id']
        start_time = match['start_time']
        home_team_id = match['home_team_id']
        away_team_id = match['away_team_id']

        # Get match history for both teams
        home_team_matches = self.get_last_n_matches_for_team(str(home_team_id), start_time, 15)
        away_team_matches = self.get_last_n_matches_for_team(str(away_team_id), start_time, 15)
        
        # Calculate fatigue features
        home_team_fatigue = self.calculate_match_history_features(home_team_matches, start_time)
        away_team_fatigue = self.calculate_match_history_features(away_team_matches, start_time)

        # Skip if either team has no history
        if home_team_fatigue['time_since_last_match'] is None or away_team_fatigue['time_since_last_match'] is None:
            return

        # Prepare data for insertion
        fatigue_record = (
            match_id,
            home_team_fatigue['time_since_last_match'],
            away_team_fatigue['time_since_last_match']
        )

        # Add matches in different time windows
        for days in [1, 3, 5, 10, 15, 30]:
            fatigue_record += (
                home_team_fatigue[f'matches_last_{days}_days'],
                home_team_fatigue[f'home_matches_last_{days}_days'],
                home_team_fatigue[f'away_matches_last_{days}_days'],
                away_team_fatigue[f'matches_last_{days}_days'],
                away_team_fatigue[f'home_matches_last_{days}_days'],
                away_team_fatigue[f'away_matches_last_{days}_days']
            )

        self.fatigue_data.append(fatigue_record)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Insert collected fatigue data upon context manager exit"""
        if exc_type is not None:
            self.conn.rollback()
            return False

        cursor = self.conn.cursor()
        try:
            # Generate column names programmatically
            base_columns = ['match_id', 'home_team_time_since_last_match', 'away_team_time_since_last_match']
            
            # Generate the fatigue metric columns for each time window
            time_windows = [1, 3, 5, 10, 15, 30]
            metric_types = [
                'matches',
                'home_matches',
                'away_matches'
            ]
            
            fatigue_columns = []
            for days in time_windows:
                for metric in metric_types:
                    for team in ['home_team', 'away_team']:
                        fatigue_columns.append(f"{team}_{metric}_last_{days}_days")
            
            # Combine all columns
            all_columns = base_columns + fatigue_columns
            
            # Generate the SQL statement
            placeholders = ', '.join(['%s'] * len(all_columns))
            columns_str = ', '.join(all_columns)
            
            query = f"""
                INSERT INTO fatigue_history (
                    {columns_str}
                )
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            
            cursor.executemany(query, self.fatigue_data)
            
            self.conn.commit()
            print(f"Processed {cursor.rowcount} rows in fatigue_history")
            
        except Exception as e:
            print(f"Error inserting fatigue data: {str(e)}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()

        return False

    @staticmethod
    def calculate_match_history_features(match_history, current_match_start_time):
        """Calculate fatigue features from match history"""
        result = {}
        
        sorted_history = sorted(match_history, 
                              key=lambda x: datetime.strptime(x['start_time'] + '+00:00', "%Y-%m-%dT%H:%M:%S%z"), 
                              reverse=True)
        
        # Time since last match (in days)
        if sorted_history:
            last_match_time = datetime.strptime(sorted_history[0]['start_time'] + '+00:00', "%Y-%m-%dT%H:%M:%S%z")
            result['time_since_last_match'] = (current_match_start_time - last_match_time).total_seconds() / (24 * 3600)
        else:
            result['time_since_last_match'] = None
        
        # Calculate features for each time window
        for days in [1, 3, 5, 10, 15, 30]:
            cutoff_date = current_match_start_time - timedelta(days=days)
            
            matches_in_window = [
                match for match in match_history 
                if datetime.strptime(match['start_time'] + '+00:00', "%Y-%m-%dT%H:%M:%S%z") >= cutoff_date
            ]
            
            result[f'matches_last_{days}_days'] = len(matches_in_window)
            result[f'home_matches_last_{days}_days'] = sum(1 for match in matches_in_window if match['is_home'] == 1)
            result[f'away_matches_last_{days}_days'] = sum(1 for match in matches_in_window if match['is_home'] == 0)
            
        return result

    def get_last_n_matches_for_team(self, team_id, current_match_time, n):
        """Get the last N matches for a team before the current match time"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                m.start_time,
                CASE WHEN m.home_team_id = %s THEN 1 ELSE 0 END as is_home
            FROM matches m
            WHERE (m.home_team_id = %s OR m.away_team_id = %s)
            AND m.start_time < %s
            AND m.home_score IS NOT NULL
            ORDER BY m.start_time DESC
            LIMIT %s
        """, (team_id, team_id, team_id, current_match_time, n))
        
        return cursor.fetchall() 