from datetime import datetime, timedelta
import psycopg2

def prune_old_future_features(conn, days_threshold=1):
    """
    Remove future features for matches that are more than X days in the past
    """
    cutoff_time = datetime.now() - timedelta(days=days_threshold)
    
    future_tables = [
        'elo_future',
        'formation_future', 
        'stage_of_season_future',
        'match_info_future',
        #TODO: Add start time to these fields so that we can prune them
        # 'form_future',
        # 'h2h_future',
    ]
    
    cursor = conn.cursor()
    total_deleted = 0
    
    try:
        for table in future_tables:
            cursor.execute(f"""
                DELETE FROM {table} 
                WHERE start_time < %s
            """, (cutoff_time,))
            
            deleted_count = cursor.rowcount
            total_deleted += deleted_count
            print(f"Deleted {deleted_count} old records from {table}")
        
        # Also clean up processed_info for inference mode
        cursor.execute("""
            DELETE FROM processed_info 
            WHERE processing_mode = 'inference' 
            AND match_id IN (
                SELECT match_id FROM matches 
                WHERE start_time < %s
            )
        """, (cutoff_time,))
        
        deleted_processed = cursor.rowcount
        print(f"Deleted {deleted_processed} old processed_info records")
        
        conn.commit()
        print(f"Total deleted: {total_deleted} feature records + {deleted_processed} processed records")
        
    except Exception as e:
        print(f"Error pruning old features: {str(e)}")
        conn.rollback()
        raise
    finally:
        cursor.close()

def prune_all_future_features(conn):
    """
    Nuclear option: Delete ALL future features (for weekly cleanup)
    """
    future_tables = [
        'elo_future',
        'formation_future', 
        'stage_of_season_future',
        'match_info_future'
    ]
    
    cursor = conn.cursor()
    total_deleted = 0
    
    try:
        for table in future_tables:
            cursor.execute(f"DELETE FROM {table}")
            deleted_count = cursor.rowcount
            total_deleted += deleted_count
            print(f"Deleted all {deleted_count} records from {table}")
        
        # Clean up processed_info for inference mode
        cursor.execute("DELETE FROM processed_info WHERE processing_mode = 'inference'")
        deleted_processed = cursor.rowcount
        
        conn.commit()
        print(f"Total deleted: {total_deleted} feature records + {deleted_processed} processed records")
        
    except Exception as e:
        print(f"Error pruning all features: {str(e)}")
        conn.rollback()
        raise
    finally:
        cursor.close() 