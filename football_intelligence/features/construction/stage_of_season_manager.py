from zoneinfo import ZoneInfo
from datetime import datetime, time

class StageOfSeasonManager:
    def __init__(self, conn, matches, mode='training'):
        self.conn = conn
        self.matches = matches
        self.mode = mode  # 'training' or 'inference'
        self.stage_of_season_data = []

    def __enter__(self):
        return self

    def process_match(self, match):
        """Process a single match to calculate stage of season metrics"""
        match_id = match['match_id']
        start_time = match['start_time']
        season_start_date = match['season_start_date']
        season_end_date = match['season_end_date']
        
        stage_of_season = self.calculate_stage_of_season(start_time, season_start_date, season_end_date)
        stage_of_season_category = self.get_season_phase(stage_of_season)
        
        self.stage_of_season_data.append((
            match_id,
            start_time,
            season_start_date,
            season_end_date,
            stage_of_season,
            stage_of_season_category
        ))

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Insert collected stage of season data upon context manager exit"""
        if exc_type is not None:
            self.conn.rollback()
            return False

        cursor = self.conn.cursor()
        try:
            if self.mode == 'training':
                # Save to training table
                cursor.executemany('''
                    INSERT INTO stage_of_season_history (
                        match_id,
                        start_time,
                        season_start_date,
                        season_end_date,
                        stage_of_season,
                        stage_of_season_category
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                ''', self.stage_of_season_data)
            elif self.mode == 'inference':
                # Save to inference/future table
                cursor.executemany('''
                    INSERT INTO stage_of_season_future (
                        match_id,
                        start_time,
                        season_start_date,
                        season_end_date,
                        stage_of_season,
                        stage_of_season_category
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                ''', self.stage_of_season_data)
            
            self.conn.commit()
            
        except Exception as e:
            print(f"Error inserting stage of season data: {str(e)}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()

        return False

    @staticmethod
    def calculate_stage_of_season(start_time, season_start_date, season_end_date):
        """Calculate the stage of season normalized between 0 and 1"""
        # Handle None values
        if season_start_date is None or season_end_date is None:
            return 0.0  # Default to early season if dates are missing
        
        # Convert strings to datetime objects if needed
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if isinstance(season_start_date, str):
            season_start_date = datetime.fromisoformat(season_start_date + 'T00:00:00+00:00')
        if isinstance(season_end_date, str):
            season_end_date = datetime.fromisoformat(season_end_date + 'T00:00:00+00:00')

        season_start_date = datetime.combine(season_start_date, time.min, tzinfo=ZoneInfo("UTC"))
        season_end_date = datetime.combine(season_end_date, time.min, tzinfo=ZoneInfo("UTC"))
        
        days_from_season_start = (start_time - season_start_date).total_seconds() / (24 * 3600)
        season_length_days = (season_end_date - season_start_date).total_seconds() / (24 * 3600)
        
        if season_length_days > 0:
            return max(0.0, min(1.0, days_from_season_start / season_length_days))
        return 0.0

    @staticmethod
    def get_season_phase(season_progress):
        """Convert numerical season progress to categorical phase"""
        if season_progress < 0.1:
            return 'Early Season (0-10%)'
        elif season_progress < 0.3:
            return 'Early-Mid Season (10-30%)'
        elif season_progress < 0.7:
            return 'Mid Season (30-70%)'
        elif season_progress < 0.9:
            return 'Mid-Late Season (70-90%)'
        else:
            return 'Late Season (90-100%)' 