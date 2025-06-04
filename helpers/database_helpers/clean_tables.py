def drop_tables(conn):
    """Drops all processing tables"""
    table_names = [
        # 'teammatchhistory',
        'counter_table',
        'elo_history',
        'club_elo_ratings',
        'league_elo_ratings',
        'nation_elo_ratings',
        'match_info_history',
        'fatigue_history',
        'formations',
        'league_standings',
        'league_standings_history',
        'stage_of_season_history',
        
    ]
    
    with conn.cursor() as cur:
        for table in reversed(table_names):
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()