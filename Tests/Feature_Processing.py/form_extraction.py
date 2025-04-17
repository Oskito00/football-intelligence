#Functions I want to test

#home_matches = get_last_n_matches_for_team(conn, home_team_id, start_time, 50)
#away_matches = get_last_n_matches_for_team(conn, away_team_id, start_time, 50)

#home_elo_ratings = get_elo_ratings_for_multiple_matches(conn, home_matches, home_team_id)
#away_elo_ratings = get_elo_ratings_for_multiple_matches(conn, away_matches, away_team_id)

# home_matches_and_elo_ratings = enrich_matches_data_with_elo_ratings(home_matches,home_elo_ratings)
# away_matches_and_elo_ratings = enrich_matches_data_with_elo_ratings(away_matches,away_elo_ratings)

#home_stats = calculate_form_stats_for_multiple_ns(home_matches, n)
#away_stats = calculate_form_stats_for_multiple_ns(away_matches, n)

import pytest

from helpers.form.form import calculate_form_stats_for_multiple_ns, enrich_matches_data_with_elo_ratings, get_elo_ratings_for_multiple_matches, get_last_n_matches_for_team


def test_get_last_n_matches_for_team(conn):
    home_matches = get_last_n_matches_for_team(conn, 'sr:competitor:40', '2022-11-06T14:00:00+00:00', 50)
    assert len(home_matches) <= 50

def test_get_elo_ratings_for_multiple_matches(conn):
    home_matches = get_last_n_matches_for_team(conn, 'sr:competitor:40', '2022-11-06T14:00:00+00:00', 50)
    home_elo_ratings = get_elo_ratings_for_multiple_matches(conn, home_matches, 'sr:competitor:40')
    assert len(home_elo_ratings) == len(home_matches)

    #Assert that the match_id's are the same.
    home_match_ids = [match['match_id'] for match in home_matches]
    elo_match_ids = [i for i in home_elo_ratings]
    assert home_match_ids == elo_match_ids

def test_enrich_matches_data_with_elo_ratings(conn):
    home_matches = get_last_n_matches_for_team(conn, 'sr:competitor:40', '2022-11-06T14:00:00+00:00', 50)
    home_elo_ratings = get_elo_ratings_for_multiple_matches(conn, home_matches, 'sr:competitor:40')
    home_matches_and_elo_ratings = enrich_matches_data_with_elo_ratings(home_matches, home_elo_ratings)
    assert len(home_matches_and_elo_ratings) == len(home_matches)


def test_calculate_form_stats_for_multiple_ns(conn):
    home_matches = get_last_n_matches_for_team(conn, 'sr:competitor:40', '2022-11-06T14:00:00+00:00', 50)
    home_elo_ratings = get_elo_ratings_for_multiple_matches(conn, home_matches, 'sr:competitor:40')
    home_matches_and_elo_ratings = enrich_matches_data_with_elo_ratings(home_matches, home_elo_ratings)
    home_stats = calculate_form_stats_for_multiple_ns(home_matches_and_elo_ratings, [1,3,5,10])
    assert home_stats['wins_in_last_1'] == 0
    assert home_stats['wins_in_last_3'] == 1
    assert home_stats['wins_in_last_5'] == 1
    assert home_stats['wins_in_last_10'] == 1

