def check_if_player_exists(player_id, conn):
    """Check if a player exists in the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM player_stats WHERE player_id = ?", (player_id,))
    
    exists = cursor.fetchone() is not None
    if exists:
        print(f"Player {player_id} already exists in database... Skipping")
    
    cursor.close()
    return exists

def check_if_player_exists_and_has_stats(player_name, conn):
    """Check if a player exists in the database and has stats"""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM player_stats WHERE player_name = ? AND height IS NOT NULL AND weight IS NOT NULL", (player_name))
    print("Player already exists in database and has stats... Skipping")
    return cursor.fetchone() is not None

