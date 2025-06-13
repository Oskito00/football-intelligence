import json
from utils.database_helpers.get_and_set_functions import bulk_insert_formations, get_from_matches

class FormationManager:
    def __init__(self, conn, matches, mode='training'):
        self.conn = conn
        self.matches = matches
        self.mode = mode  # 'training' or 'inference'
        self.formation_data = []

    def __enter__(self):
        return self

    def process_match(self, match):
        """Process a single match to extract formation data"""
        try:
            match_id = match['match_id']
            start_time = match['start_time']
            home_formation = match['home_team_formation']
            away_formation = match['away_team_formation']

            # Skip if formations are not available
            if not home_formation or not away_formation:
                return

            formation_record = (
                match_id,
                start_time,
                home_formation,
                away_formation
            )

            self.formation_data.append(formation_record)

        except (KeyError, TypeError) as e:
            print(f"Skipping match {match.get('match_id', 'unknown')}: {str(e)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Insert collected formation data upon context manager exit"""
        if exc_type is not None:
            self.conn.rollback()
            return False

        cursor = self.conn.cursor()
        try:
            if self.mode == 'training':
                # Save to training table
                query = """
                    INSERT INTO formation_history (
                        match_id,
                        start_time,
                        home_team_formation,
                        away_team_formation
                    )
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """
            elif self.mode == 'inference':
                # Save to inference/future table
                query = """
                    INSERT INTO formation_future (
                        match_id,
                        start_time,
                        home_team_formation,
                        away_team_formation
                    )
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """
            
            cursor.executemany(query, self.formation_data)
            
            self.conn.commit()
            
        except Exception as e:
            print(f"Error inserting formation data: {str(e)}")
            self.conn.rollback()
            raise
        finally:
            cursor.close()

        return False

def formation_extraction(conn):
    """Extracts the formation for each match
    
    Args:
        matches (list): The list of matches to extract formations from.
    
    Returns:
        formations (list): The list of formations.
        Saves the formations to formation_history table.
    """
    matches = get_from_matches(conn, select_str='SELECT', columns=['match_id', 'home_team_formation', 'away_team_formation'], where_clause='home_team_formation IS NOT NULL AND away_team_formation IS NOT NULL AND home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = false')

    formations = []
    match_count = 0
    for match in matches:
        if match_count % 1000 == 0:
            print(f"Processing match {match_count} out of {len(matches)}")
        match_count += 1
        try:
            match_id, home_formation_str, away_formation_str = match

            formations.append({
                'match_id': match_id,
                'home_team_formation': home_formation_str,
                'away_team_formation': away_formation_str
            })
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Skipping match {match_id}: {str(e)}")
            continue
    
    bulk_insert_formations(formations, conn)
            
    return formations


