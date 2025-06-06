def extract_team_ids(matches):
    return list(set(
        m['home_team_id'] for m in matches
    ).union(
        m['away_team_id'] for m in matches
    ))

def extract_nation_names(matches):
    return list(set(
        m['home_team_domestic_country'] for m in matches
    ).union(
        m['away_team_domestic_country'] for m in matches
    ))

def extract_league_ids(matches):
    return list(set(
        m['home_team_domestic_league_id'] for m in matches
    ).union(
        m['away_team_domestic_league_id'] for m in matches
    ))

def extract_competition_ids(matches):
    return list(set(
        m['competition_id'] for m in matches
    ))

def extract_team_id_name_map(matches):
    """
    Returns a dictionary mapping team_id -> team_name from all matches.
    If a team ID appears multiple times with different names, the latest one is used.
    """
    id_name_map = {}

    for match in matches:
        id_name_map[match['home_team_id']] = match['home_team_name']
        id_name_map[match['away_team_id']] = match['away_team_name']

    return id_name_map