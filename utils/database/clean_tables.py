def drop_tables(conn):
    """Drops all processing tables"""
    table_names = [
        # 'teammatchhistory',
        # 'counter_table',
        # 'elo_history',
        # 'club_elo_ratings',
        # 'league_elo_ratings',
        # 'nation_elo_ratings',
        # 'match_info_history',
        # 'stage_of_season_history',
        # 'form_history',
        # 'form_matches_cache',
        # 'h2h_history',
        # 'h2h_stats',
        # 'processed_info'


        # 'fatigue_history',
        # 'league_standings',
        # 'league_standings_history',
        # 'formations',
    ]
    
    with conn.cursor() as cur:
        for table in reversed(table_names):
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()

def drop_future_tables(conn):
    """Drops all future processing tables"""
    table_names = [
        'elo_future',
        'stage_of_season_future',
        'match_info_future',
        'league_standings_future',
        'formation_future',
        'form_future',
        'h2h_future',
        'fatigue_future'
    ]
    with conn.cursor() as cur:
        for table in reversed(table_names):
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()