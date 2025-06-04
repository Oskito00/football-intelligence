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