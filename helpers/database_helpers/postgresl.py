from psycopg2.extras import execute_values

def upsert_records(conn, table_name, records, conflict_keys):
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

    values = [tuple(record[col] for col in columns) for record in records]

    with conn.cursor() as cursor:
        execute_values(cursor, insert_query, values)
    conn.commit()