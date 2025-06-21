import os
import json
import psycopg2
from config import get_config
from data_scraping.helpers.scrapers.main_data_scraper import scrape_matches_from_api
from utils.database.postgresql import upsert_records


config = get_config()

with psycopg2.connect(
    host=config.DB_HOST,
    database=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD
) as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, years, current_season FROM leagues")
        leagues = cursor.fetchall()

    scraped_data = scrape_matches_from_api(leagues, latest_only=True)

    upsert_records(
        conn=conn,
        table_name="matches",
        records=scraped_data,
        conflict_keys=["match_id"],
        batch_size=1000
    )