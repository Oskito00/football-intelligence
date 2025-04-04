
def add_competition_country_to_matches_table(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT match_id, competition_id FROM matches")
    matches = cursor.fetchall()
    for match in matches:
        competition_id = match[1]
        competition_country = get_competition_country(competition_id)
        cursor.execute("UPDATE matches SET competition_country = ? WHERE match_id = ?", (competition_country, match[0]))
    conn.commit()
    cursor.close(