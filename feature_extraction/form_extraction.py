from helpers.database_helpers.sql_statements.form import get_last_n_matches_for_team


def form_extraction(matches):
    n = [1,3,5,10,20,50]

    # Ignore first 1000 matches for parameter tuning as in all the other processing files.
    for match in matches:
        match_id, start_time, competition_id, competition_name, competition_country, home_team_id, home_team_name, away_team_id, away_team_name, \
        home_score, away_score, home_main_comp_id, home_main_comp_country, \
        away_main_comp_id, away_main_comp_country = match

        home_stats = get_last_n_matches_for_team(50, home_team_id, start_time)
        away_stats = get_last_n_matches_for_team(50, away_team_id, start_time)





