from datetime import datetime
import logging
from psycopg2.extras import execute_values

from utils.database.create_tables import create_match_result_predictions_table

def upsert_records(conn, table_name, records, conflict_keys, batch_size=1000):
    if not records:
        return

    columns = records[0].keys()
    update_columns = [col for col in columns if col not in conflict_keys]

    insert_query = f"""
        INSERT INTO {table_name} ({', '.join(columns)})
        VALUES %s
        ON CONFLICT ({', '.join(conflict_keys)}) DO UPDATE SET
        {', '.join([f"{col} = EXCLUDED.{col}" for col in update_columns])}
    """

    def batched(iterable, n):
        for i in range(0, len(iterable), n):
            yield iterable[i:i + n]

    with conn.cursor() as cursor:
        for batch in batched(records, batch_size):
            values = [tuple(record[col] for col in columns) for record in batch]
            execute_values(cursor, insert_query, values)
        conn.commit()

    print(f"Upserted {len(records)} records into {table_name}")

def save_predictions_to_db(conn, predictions_df, model_type='basic'):
    """
    Save match predictions to the database
    
    Args:
        conn: Database connection
        predictions_df: DataFrame with predictions
        model_type: 'basic' or 'with_formation'
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Ensure the table exists
        create_match_result_predictions_table(conn)
        
        # Add model_type if not already present
        if 'model_type' not in predictions_df.columns:
            predictions_df = predictions_df.copy()
            predictions_df['model_type'] = model_type
        
        # Ensure we have the required columns
        required_columns = [
            'match_id', 'predicted_result', 'start_time', 
            'home_team_name', 'away_team_name', 
            'prob_home_win', 'prob_draw', 'prob_away_win',
            'model_type', 'prediction_timestamp'
        ]
        
        # Check if all required columns exist
        missing_columns = [col for col in required_columns if col not in predictions_df.columns]
        if missing_columns:
            logger.warning(f"Missing columns: {missing_columns}")
            # Add missing columns with default values
            for col in missing_columns:
                if col == 'prediction_timestamp':
                    predictions_df[col] = datetime.now()
                else:
                    predictions_df[col] = None
        
        # Convert DataFrame to records
        records = predictions_df[required_columns].to_dict('records')
        
        # Use existing upsert function
        upsert_records(
            conn=conn,
            table_name='match_result_predictions',
            records=records,
            conflict_keys=['match_id']
        )
        
        logger.info(f"Successfully saved {len(records)} predictions with model_type='{model_type}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save predictions to database: {str(e)}")
        return False

def get_latest_predictions(conn, limit=None):
    """
    Get latest predictions from database
    
    Args:
        conn: Database connection 
        limit: Optional limit on number of records
        
    Returns:
        List of prediction records
    """
    cursor = conn.cursor()
    
    query = """
        SELECT 
            match_id, predicted_result, start_time,
            home_team_name, away_team_name,
            prob_home_win, prob_draw, prob_away_win,
            model_type, prediction_timestamp
        FROM match_result_predictions
        ORDER BY start_time ASC
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()
    
    return results