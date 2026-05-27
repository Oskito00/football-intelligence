"""Compatibility entrypoint for Historical Feature Set processing."""

from config import get_config
from football_intelligence.features import build_historical_feature_set


def process_matches(conn):
    return build_historical_feature_set(conn)


if __name__ == "__main__":
    import psycopg2
    from psycopg2.extras import RealDictCursor

    config = get_config()
    connection = psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        cursor_factory=RealDictCursor,
    )
    process_matches(connection)
