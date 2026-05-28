"""API-Football provider implementation for Source Data Ingestion."""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

from config import get_config
from utils.database.create_tables import create_odds_table
from utils.database.get_and_set_functions import get_future_matches_with_odds
from utils.database.postgresql import upsert_records
from utils.formatting.time import datetime_string_converter


config = get_config()

BASE_URL = "https://v3.football.api-sports.io/"
API_FOOTBALL_HEADERS = {
    "x-rapidapi-key": config.API_FOOTBALL_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io",
}
MATCH_SCRAPER_HEADERS = {
    "x-rapidapi-key": os.getenv("API_FOOTBALL_KEY"),
    "x-rapidapi-host": "v3.football.api-sports.io",
}
PAYLOAD = {}

# Target bookmakers: Betfair, Bwin, William Hill, Bet365, Betfred
TARGET_BOOKMAKERS = [3, 6, 7, 8, 12]


class ApiFootballSourceDataProvider:
    """Provider adapter that preserves the existing API-Football ingestion behavior."""

    def refresh_league_catalogue(self, conn: Any) -> None:
        get_all_leagues_on_api(conn)

    def refresh_current_match_data(self) -> None:
        scrape_current_seasons()

    def refresh_match_odds(self, conn: Any) -> None:
        scrape_future_match_odds(conn)


def fetch_with_retry(url, headers, payload=None, max_retries=2, timeout=4):
    """Fetch API data with the legacy retry behavior."""
    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.get(url, headers=headers, data=payload, timeout=timeout)
            if response.status_code == 200:
                return response.json()
            print(f"Non-200 status code {response.status_code} for {url}")
            return None
        except requests.exceptions.Timeout:
            print(f"Timeout on {url} (attempt {attempt + 1})")
        except requests.exceptions.RequestException as e:
            print(f"Request failed on {url}: {e}")
        attempt += 1
        time.sleep(0.1)
    print(f"Failed after {max_retries} attempts: {url}")
    return None


def get_all_leagues_on_api(conn):
    response = requests.get(
        "https://v3.football.api-sports.io/leagues",
        headers=API_FOOTBALL_HEADERS,
    )

    if response.status_code != 200:
        print("Failed to fetch leagues:", response.text)
        return

    data = response.json().get("response", [])

    rows = []
    for league in data:
        print("Processing league:", league["league"]["name"])
        league_data = {
            "id": league["league"]["id"],
            "name": league["league"]["name"],
            "type": league["league"]["type"],
            "logo": league["league"]["logo"],
            "country": json.dumps(league["country"]),
            "years": ([season["year"] for season in league["seasons"]]),
            "current_season": next(
                (season["year"] for season in league["seasons"] if season["current"]),
                None,
            ),
            "seasons": json.dumps(league["seasons"]),
        }
        print(league_data["years"])
        rows.append(league_data)

    upsert_records(conn, "leagues", rows, ["id"], batch_size=1000)


def scrape_current_seasons():
    current_config = get_config()
    conn = psycopg2.connect(
        host=current_config.DB_HOST,
        database=current_config.DB_NAME,
        user=current_config.DB_USER,
        password=current_config.DB_PASSWORD,
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
        batch_size=1000,
    )


def scrape_matches_from_api(leagues, latest_only=False):
    scraped_data = []

    for i, league in enumerate(leagues):
        print(f"----- Processing League {league[0]}\n League {i} of {len(leagues)}------")
        competition_id = league[0]
        years = league[1]
        current_season = league[2]

        target_years = [current_season] if latest_only else years
        for year in target_years:
            print(f"-------- Processing Year {year} --------")
            try:
                fixtures_url = BASE_URL + f"fixtures?league={competition_id}&season={year}"
                json_fixtures_response = fetch_with_retry(
                    fixtures_url,
                    MATCH_SCRAPER_HEADERS,
                    PAYLOAD,
                )
                if json_fixtures_response is None:
                    print(f"No fixture data for league {competition_id}, year {year}")
                    continue

                season_info_url = BASE_URL + f"leagues?id={competition_id}&season={year}"
                json_season_info_response = fetch_with_retry(
                    season_info_url,
                    MATCH_SCRAPER_HEADERS,
                    PAYLOAD,
                )
                if json_season_info_response is None:
                    print(f"No season info for league {competition_id}, year {year}")
                    continue

                season_info = json_season_info_response["response"]
                season_fixtures = json_fixtures_response["response"]
                season_start_date = season_info[0]["seasons"][0]["start"]
                season_end_date = season_info[0]["seasons"][0]["end"]

                for content in season_fixtures:
                    home_score = content["score"]["fulltime"].get("home")
                    away_score = content["score"]["fulltime"].get("away")

                    result = None
                    if home_score is not None and away_score is not None:
                        if home_score == away_score:
                            result = "Draw"
                        elif home_score > away_score:
                            result = "Home Win"
                        else:
                            result = "Away Win"

                    match_data = {
                        "match_id": content["fixture"]["id"],
                        "start_time": content["fixture"]["date"],
                        "clean_date": datetime_string_converter(content["fixture"]["date"]),
                        "competition_name": season_info[0]["league"]["name"],
                        "competition_id": competition_id,
                        "competition_country": season_info[0]["country"]["name"],
                        "competition_season_name": (
                            f"{season_info[0]['league']['name']}_{year}"
                        ),
                        "competition_season_id": f"{competition_id}_{year}",
                        "season_start_date": season_start_date,
                        "season_end_date": season_end_date,
                        "round_info": content["league"]["round"],
                        "home_team_id": content["teams"]["home"]["id"],
                        "home_team_name": content["teams"]["home"]["name"],
                        "home_team_domestic_league_id": None,
                        "away_team_domestic_league_id": None,
                        "home_team_domestic_country": None,
                        "away_team_domestic_country": None,
                        "away_team_id": content["teams"]["away"]["id"],
                        "away_team_name": content["teams"]["away"]["name"],
                        "match_status": content["fixture"]["status"]["short"],
                        "home_score": home_score,
                        "away_score": away_score,
                        "result": result,
                        "all_fixture_data": json.dumps(content),
                        "all_season_info": json.dumps(season_info),
                        "home_team_formation": None,
                        "away_team_formation": None,
                        "home_team_lineup": None,
                        "away_team_lineup": None,
                        "attempted_formation_scrape": False,
                        "is_current_season": season_info[0]["seasons"][0]["current"],
                        "has_odds": season_info[0]["seasons"][0]["coverage"]["odds"],
                        "has_players": season_info[0]["seasons"][0]["coverage"]["players"],
                        "has_lineups": season_info[0]["seasons"][0]["coverage"]["fixtures"][
                            "lineups"
                        ],
                        "has_events": season_info[0]["seasons"][0]["coverage"]["fixtures"][
                            "events"
                        ],
                        "has_statistics_players": season_info[0]["seasons"][0]["coverage"][
                            "fixtures"
                        ]["statistics_players"],
                        "has_statistics_fixtures": season_info[0]["seasons"][0]["coverage"][
                            "fixtures"
                        ]["statistics_fixtures"],
                    }
                    scraped_data.append(match_data)

            except Exception as e:
                print(f"Error while processing {competition_id} {year}: {e}")

    _assign_domestic_leagues(scraped_data)
    return scraped_data


def _assign_domestic_leagues(scraped_data):
    domestic_league_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    country_dict = defaultdict(lambda: defaultdict(int))

    def extract_year(season_id):
        return season_id.split("_")[1]

    for match in scraped_data:
        year = extract_year(match["competition_season_id"])
        comp_id = match["competition_id"]
        country = match["competition_country"]

        if match["season_start_date"] is None or match["season_end_date"] is None:
            duration = 0
        else:
            season_start = datetime.strptime(match["season_start_date"], "%Y-%m-%d")
            season_end = datetime.strptime(match["season_end_date"], "%Y-%m-%d")
            duration = (season_end - season_start).days

        if duration > 90:
            for team_id in [match["home_team_id"], match["away_team_id"]]:
                domestic_league_dict[team_id][year][comp_id] += 1
        for team_id in [match["home_team_id"], match["away_team_id"]]:
            country_dict[team_id][country] += 1

    for match in scraped_data:
        year = extract_year(match["competition_season_id"])
        prev_year = str(int(year) - 1)

        for side in ["home", "away"]:
            team_id = match[f"{side}_team_id"]

            current_counts = domestic_league_dict[team_id].get(year, {})
            prev_counts = domestic_league_dict[team_id].get(prev_year, {})

            if current_counts:
                league_id = max(current_counts, key=current_counts.get)
            elif prev_counts:
                league_id = max(prev_counts, key=prev_counts.get)
            else:
                league_id = 0

            match[f"{side}_team_domestic_league_id"] = league_id

            country_counts = country_dict[team_id]
            match[f"{side}_team_domestic_country"] = (
                max(country_counts, key=country_counts.get) if country_counts else None
            )


def fetch_odds_for_match(match_id: int) -> dict | None:
    """Fetch odds for a specific match from API-Football."""
    url = "https://v3.football.api-sports.io/odds"
    params = {
        "fixture": match_id,
        "bet": 1,
    }

    try:
        print(f"  🌐 Fetching odds for match {match_id}")
        response = requests.get(
            url,
            headers=API_FOOTBALL_HEADERS,
            params=params,
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("errors"):
            print(f"❌ API error for match {match_id}: {data['errors']}")
            return None

        print(f"  ✅ Success: Match {match_id}")
        return data

    except Exception as e:
        print(f"❌ Error fetching odds for match {match_id}: {str(e)}")
        return None


def parse_odds_data(api_response: dict, match_id: int) -> list:
    """Parse odds data from API-Football response for target bookmakers."""
    odds_records = []

    if not api_response or not api_response.get("response"):
        return odds_records

    response_data = api_response["response"]

    for match_data in response_data:
        if match_data["fixture"]["id"] != match_id:
            continue

        api_last_updated = match_data.get("update")
        bookmakers = match_data.get("bookmakers", [])

        for bookmaker in bookmakers:
            bookmaker_id = bookmaker["id"]

            if bookmaker_id not in TARGET_BOOKMAKERS:
                continue

            for bet in bookmaker.get("bets", []):
                for value in bet.get("values", []):
                    odds_records.append(
                        {
                            "match_id": match_id,
                            "bookmaker_id": bookmaker_id,
                            "bookmaker_name": bookmaker["name"],
                            "bet_type_id": bet["id"],
                            "bet_type_name": bet["name"],
                            "bet_value": value["value"],
                            "odds_value": float(value["odd"]),
                            "api_last_updated": api_last_updated,
                        }
                    )

    return odds_records


def save_odds_to_db(conn, odds_records: list):
    """Save odds records to the database."""
    if not odds_records:
        return 0

    cursor = conn.cursor()
    rows_inserted = 0

    try:
        for record in odds_records:
            cursor.execute(
                """
                INSERT INTO odds (
                    match_id, bookmaker_id, bookmaker_name, bet_type_id,
                    bet_type_name, bet_value, odds_value, api_last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    record["match_id"],
                    record["bookmaker_id"],
                    record["bookmaker_name"],
                    record["bet_type_id"],
                    record["bet_type_name"],
                    record["bet_value"],
                    record["odds_value"],
                    record["api_last_updated"],
                ),
            )
            rows_inserted += 1

        conn.commit()
        return rows_inserted

    except Exception as e:
        print(f"❌ Error saving odds: {str(e)}")
        conn.rollback()
        return 0
    finally:
        cursor.close()


def scrape_future_match_odds(conn=None):
    """Scrape odds for future matches from API-Football."""
    print("🚀 Starting odds scraping for future matches...")
    print(f"🎯 Target bookmakers: {TARGET_BOOKMAKERS}")

    should_close_conn = conn is None
    if conn is None:
        print("🔌 Creating new database connection...")
        conn = psycopg2.connect(
            host=config.DB_HOST,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            cursor_factory=RealDictCursor,
        )
    else:
        print("🔌 Using provided database connection...")

    try:
        print("📋 Creating odds table if it doesn't exist...")
        create_odds_table(conn)
        print("✅ Odds table ready")

        print("🔍 Querying for future matches with odds...")
        try:
            match_ids = get_future_matches_with_odds(conn)
            print(f"📋 Found {len(match_ids)} future matches to process")
        except Exception as e:
            print(f"❌ Error in get_future_matches_with_odds: {str(e)}")
            import traceback

            traceback.print_exc()
            return

        if len(match_ids) == 0:
            print("⚠️ No future matches found with odds available")
            print("💡 This could mean:")
            print("   • No matches have has_odds = TRUE")
            print("   • No future matches within 7 days")
            print("   • All future matches already have scores")
            return

        successful_matches = 0
        failed_matches = 0
        total_odds_saved = 0

        for i, match_id in enumerate(match_ids, 1):
            print(f"\n⚽ Processing match {i}/{len(match_ids)}: {match_id}")

            odds_data = fetch_odds_for_match(match_id)

            if odds_data:
                odds_records = parse_odds_data(odds_data, match_id)

                if odds_records:
                    saved_count = save_odds_to_db(conn, odds_records)
                    if saved_count > 0:
                        successful_matches += 1
                        total_odds_saved += saved_count
                        print(f"✅ Saved {saved_count} odds for match {match_id}")
                    else:
                        failed_matches += 1
                        print(f"❌ Failed to save odds for match {match_id}")
                else:
                    failed_matches += 1
                    print(f"⚠️ No valid odds found for match {match_id}")
            else:
                failed_matches += 1

        print("\n🎉 SCRAPING COMPLETED!")
        print("📊 Results:")
        print(f"   • Total matches processed: {len(match_ids)}")
        print(f"   • Successful matches: {successful_matches}")
        print(f"   • Failed matches: {failed_matches}")
        print(f"   • Total odds records saved: {total_odds_saved}")

    except Exception as e:
        print(f"❌ Error during scraping: {str(e)}")
        import traceback

        print("🔍 Full error details:")
        traceback.print_exc()

    finally:
        if should_close_conn and conn:
            print("🔌 Closing database connection...")
            conn.close()
