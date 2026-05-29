"""Match input collection helpers for Feature Set construction."""


def extract_team_ids(matches):
    return list(
        set(match["home_team_id"] for match in matches).union(
            match["away_team_id"] for match in matches
        )
    )


def extract_nation_names(matches):
    return list(
        set(match["home_team_domestic_country"] for match in matches).union(
            match["away_team_domestic_country"] for match in matches
        )
    )


def extract_league_ids(matches):
    return list(
        set(match["home_team_domestic_league_id"] for match in matches).union(
            match["away_team_domestic_league_id"] for match in matches
        )
    )


def extract_competition_ids(matches):
    return list(set(match["competition_id"] for match in matches))


def extract_team_id_name_map(matches):
    """Return the latest team-name mapping seen for each team ID."""
    id_name_map = {}

    for match in matches:
        id_name_map[match["home_team_id"]] = match["home_team_name"]
        id_name_map[match["away_team_id"]] = match["away_team_name"]

    return id_name_map
