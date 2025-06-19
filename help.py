import psycopg2
from collections import defaultdict

from config import get_config

config = get_config()

def get_db_connection():
    return psycopg2.connect(
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        host=config.DB_HOST,
    )

def fetch_all_matches(cursor):
    cursor.execute("""
        SELECT match_id, home_team_name, away_team_name, competition_id, competition_country, competition_season_id,
               season_start_date, season_end_date, home_team_id, away_team_id
        FROM matches
    """)
    return cursor.fetchall()

def build_domestic_league_map(matches):
    # Format: team_id → year → comp_id → count
    league_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    country_counts = defaultdict(lambda: defaultdict(int))

    for row in matches:
        match_id, home_team_name, away_team_name, comp_id, country, season_id, season_start, season_end, home_id, away_id = row
        year = season_id.split('_')[1]
        duration = (season_end - season_start).days

        if duration > 90:
            for team_id in [home_id, away_id]:
                league_counts[team_id][year][comp_id] += 1
        for team_id in [home_id, away_id]:
            country_counts[team_id][country] += 1

    return league_counts, country_counts

def assign_domestic_league(team_id, year, league_counts):
    this_year = league_counts.get(team_id, {}).get(year, {})
    prev_year = league_counts.get(team_id, {}).get(str(int(year) - 1), {})

    if this_year:
        return max(this_year, key=this_year.get)
    elif prev_year:
        return max(prev_year, key=prev_year.get)
    else:
        return 0

def assign_country(team_id, country_counts):
    countries = country_counts.get(team_id, {})
    return max(countries, key=countries.get) if countries else None

def update_matches(cursor, matches, league_counts, country_counts):
    len_matches = len(matches)
    i = 0
    for row in matches:
        i += 1
        if i % 1000 == 0:
            print(f"Processed {i} of {len_matches} matches")

        match_id, home_team_name, away_team_name, comp_id, country, season_id, season_start, season_end, home_id, away_id = row
        year = season_id.split('_')[1]


        home_league_id = assign_domestic_league(home_id, year, league_counts)
        away_league_id = assign_domestic_league(away_id, year, league_counts)

        home_country = assign_country(home_id, country_counts)
        away_country = assign_country(away_id, country_counts)

        cursor.execute("""
            UPDATE matches
            SET home_team_domestic_league_id = %s,
                away_team_domestic_league_id = %s,
                home_team_domestic_country = %s,
                away_team_domestic_country = %s
            WHERE match_id = %s
        """, (home_league_id, away_league_id, home_country, away_country, match_id))

def main():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("Fetching matches...")
    matches = fetch_all_matches(cursor)

    print("Building domestic league mappings...")
    league_counts, country_counts = build_domestic_league_map(matches)

    print("Updating matches with new domestic league info...")
    update_matches(cursor, matches, league_counts, country_counts)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Update complete.")

if __name__ == "__main__":
    main()