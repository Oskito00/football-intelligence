import os
import json
import psycopg2
from data_scraping.helpers.scrapers.main_data_scraper import scrape_matches_from_api
from utils.database.postgresql import upsert_records
from config import get_config

def scrape_current_seasons():
    config = get_config()
    conn = psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )

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
