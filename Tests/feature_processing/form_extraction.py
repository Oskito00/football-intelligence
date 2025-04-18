#Functions I want to test

#home_matches = get_last_n_matches_for_team(conn, home_team_id, start_time, 50)
#away_matches = get_last_n_matches_for_team(conn, away_team_id, start_time, 50)

#home_elo_ratings = get_elo_ratings_for_multiple_matches(conn, home_matches, home_team_id)
#away_elo_ratings = get_elo_ratings_for_multiple_matches(conn, away_matches, away_team_id)

# home_matches_and_elo_ratings = enrich_matches_data_with_elo_ratings(home_matches,home_elo_ratings)
# away_matches_and_elo_ratings = enrich_matches_data_with_elo_ratings(away_matches,away_elo_ratings)

#home_stats = calculate_form_stats_for_multiple_ns(home_matches, n)
#away_stats = calculate_form_stats_for_multiple_ns(away_matches, n)

import math
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

    # Basic stats assertions
    assert home_stats['wins_in_last_1'] == 0
    assert home_stats['wins_in_last_3'] == 1
    assert home_stats['wins_in_last_5'] == 1
    assert home_stats['wins_in_last_10'] == 2
    assert home_stats['draws_in_last_1'] == 0
    assert home_stats['draws_in_last_3'] == 0
    assert home_stats['draws_in_last_5'] == 1
    assert home_stats['draws_in_last_10'] == 3
    assert home_stats['clean_sheets_in_last_1'] == 0
    assert home_stats['clean_sheets_in_last_3'] == 1
    assert home_stats['clean_sheets_in_last_5'] == 1
    assert home_stats['clean_sheets_in_last_10'] == 3
    assert home_stats['wins_at_home_in_last_1'] == 0
    assert home_stats['wins_at_home_in_last_3'] == 1
    assert home_stats['wins_at_home_in_last_5'] == 1
    assert home_stats['wins_at_home_in_last_10'] == 2
    assert home_stats['wins_away_in_last_1'] == 0
    assert home_stats['wins_away_in_last_3'] == 0
    assert home_stats['wins_away_in_last_5'] == 0
    assert home_stats['wins_away_in_last_10'] == 0
    assert home_stats['home_match_count_in_last_1'] == 0
    assert home_stats['home_match_count_in_last_3'] == 1
    assert home_stats['home_match_count_in_last_5'] == 2
    assert home_stats['home_match_count_in_last_10'] == 5
    assert home_stats['away_match_count_in_last_1'] == 1
    assert home_stats['away_match_count_in_last_3'] == 2
    assert home_stats['away_match_count_in_last_5'] == 3
    assert home_stats['away_match_count_in_last_10'] == 5
    assert home_stats['ave_goals_scored_in_last_1'] == 0
    assert home_stats['ave_goals_scored_in_last_3'] == 4/3
    assert home_stats['ave_goals_scored_in_last_5'] == 1
    assert home_stats['ave_goals_scored_in_last_10'] == 0.8

    #Elo assertions
    assert home_stats['matches_vs_better_elo_away_matches_in_last_3'] == 3
    assert home_stats['wins_vs_better_elo_away_matches_in_last_3'] == 1
    assert home_stats['draws_vs_better_elo_away_matches_in_last_3'] == 0
    assert home_stats['matches_vs_worse_elo_away_matches_in_last_3'] == 0
    assert home_stats['wins_vs_worse_elo_away_matches_in_last_3'] == 0
    assert home_stats['draws_vs_worse_elo_away_matches_in_last_3'] == 0
    assert home_stats['matches_vs_similar_elo_away_matches_in_last_3'] == 0
    assert home_stats['wins_vs_similar_elo_away_matches_in_last_3'] == 0
    assert home_stats['draws_vs_similar_elo_away_matches_in_last_3'] == 0
    
    assert home_stats['matches_vs_better_nation_elo_in_last_3'] == 0
    assert home_stats['wins_vs_better_nation_elo_in_last_3'] == 0
    assert home_stats['draws_vs_better_nation_elo_in_last_3'] == 0
    assert home_stats['matches_vs_worse_nation_elo_in_last_3'] == 0
    assert home_stats['wins_vs_worse_nation_elo_in_last_3'] == 0
    assert home_stats['draws_vs_worse_nation_elo_in_last_3'] == 0
    assert home_stats['matches_vs_similar_nation_elo_in_last_3'] == 3
    assert home_stats['wins_vs_similar_nation_elo_in_last_3'] == 1
    assert home_stats['draws_vs_similar_nation_elo_in_last_3'] == 0

    assert home_stats['matches_vs_better_league_domestic_elo_in_last_3'] == 0
    assert home_stats['wins_vs_better_league_domestic_elo_in_last_3'] == 0
    assert home_stats['draws_vs_better_league_domestic_elo_in_last_3'] == 0
    assert home_stats['matches_vs_worse_league_domestic_elo_in_last_3'] == 0
    assert home_stats['wins_vs_worse_league_domestic_elo_in_last_3'] == 0
    assert home_stats['draws_vs_worse_league_domestic_elo_in_last_3'] == 0
    assert home_stats['matches_vs_similar_league_domestic_elo_in_last_3'] == 3
    assert home_stats['wins_vs_similar_league_domestic_elo_in_last_3'] == 1
    assert home_stats['draws_vs_similar_league_domestic_elo_in_last_3'] == 0

    assert home_stats['ave_goals_scored_vs_better_elo_away_matches_in_last_3'] == 4/3
    assert home_stats['ave_goals_conceded_vs_better_elo_away_matches_in_last_3'] == 7/3
    assert home_stats['ave_goals_scored_vs_worse_elo_away_matches_in_last_3'] == 0
    assert home_stats['ave_goals_conceded_vs_worse_elo_away_matches_in_last_3'] == 0
    assert home_stats['ave_goals_scored_vs_similar_nation_elo_in_last_3'] == 4/3
    assert home_stats['ave_goals_conceded_vs_similar_nation_elo_in_last_3'] == 7/3

    #Asserting that raw goals were deleted and replaced with averages
    assert 'goals_scored_vs_better_elo_away_matches_in_last_3' not in home_stats
    assert 'goals_conceded_vs_better_elo_away_matches_in_last_3' not in home_stats

    # #Elo-change
    assert math.isclose(home_stats['ave_elo_away_matches_change_in_last_3'], 5.7603, rel_tol=1e-04)
    assert math.isclose(home_stats['ave_nation_elo_change_in_last_3'], 1.2065, rel_tol=1e-04)
    #More tests to add

