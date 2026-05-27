import pytest
from unittest.mock import MagicMock, patch

from data_processing.helpers.processing_functions.elo_manager import EloManager


@pytest.fixture
def sample_matches():
    return [
        {
            'match_id': 1,
            'home_team_id': 100,
            'away_team_id': 200,
            'home_score': 2,
            'away_score': 1,
            'home_team_domestic_country': 'England',
            'away_team_domestic_country': 'England',
            'home_team_domestic_league_id': 10,
            'away_team_domestic_league_id': 10,
            'competition_id': 555,
            'home_team_name': 'TeamA',
            'away_team_name': 'TeamB',
            'start_time': '2025-01-01T12:00:00'
        },
        {
            'match_id': 2,
            'home_team_id': 101,
            'away_team_id': 201,
            'home_score': 0,
            'away_score': 2,
            'home_team_domestic_country': 'England',
            'away_team_domestic_country': 'England',
            'home_team_domestic_league_id': 10,
            'away_team_domestic_league_id': 10,
            'competition_id': 555,
            'home_team_name': 'TeamC',
            'away_team_name': 'TeamD',
            'start_time': '2025-01-02T12:00:00'
        },
        {
            'match_id': 3,
            'home_team_id': 100,
            'away_team_id': 201,
            'home_score': 3,
            'away_score': 1,
            'home_team_domestic_country': 'England',
            'away_team_domestic_country': 'England',
            'home_team_domestic_league_id': 10,
            'away_team_domestic_league_id': 10,
            'competition_id': 555,
            'home_team_name': 'TeamA',
            'away_team_name': 'TeamD',
            'start_time': '2025-01-03T12:00:00'
        },
        {
            'match_id': 4,
            'home_team_id': 101,
            'away_team_id': 200,
            'home_score': 5,
            'away_score': 0,
            'home_team_domestic_country': 'England',
            'away_team_domestic_country': 'England',
            'home_team_domestic_league_id': 10,
            'away_team_domestic_league_id': 10,
            'competition_id': 555,
            'home_team_name': 'TeamC',
            'away_team_name': 'TeamB',
            'start_time': '2025-01-04T12:00:00'
        }
    ]


@patch('data_processing.helpers.processing_functions.elo_manager.get_bulk_entity_elos')
@patch('data_processing.helpers.processing_functions.elo_manager.get_counts')
@patch('data_processing.helpers.processing_functions.elo_manager.calculate_elo_ratings')
@patch('data_processing.helpers.processing_functions.elo_manager.build_elo_history_record')
@patch('data_processing.helpers.processing_functions.elo_manager.save_elo_history_bulk')
@patch('data_processing.helpers.processing_functions.elo_manager.save_updated_elos_bulk')
@patch('data_processing.helpers.processing_functions.elo_manager.save_updated_counts')
@patch('data_processing.helpers.processing_functions.elo_manager.extract_team_ids')
@patch('data_processing.helpers.processing_functions.elo_manager.extract_nation_names')
@patch('data_processing.helpers.processing_functions.elo_manager.extract_league_ids')
@patch('data_processing.helpers.processing_functions.elo_manager.extract_competition_ids')
def test_elomanager_process_match(
    mock_extract_competition_ids,
    mock_extract_league_ids,
    mock_extract_nation_names,
    mock_extract_team_ids,
    mock_save_counts,
    mock_save_elos,
    mock_save_history,
    mock_build_elo_history_record,
    mock_calculate_elo_ratings,
    mock_get_counts,
    mock_get_bulk_entity_elos,
    sample_matches
):
    # Setup mocks return values
    mock_extract_team_ids.return_value = [100, 200, 101, 201]
    mock_extract_nation_names.return_value = ['England']
    mock_extract_league_ids.return_value = [10]
    mock_extract_competition_ids.return_value = [555]

    mock_get_bulk_entity_elos.side_effect = lambda conn, table, key_field, ids, *args: {id_: {'elo_k': 1500} for id_ in ids}
    mock_get_counts.return_value = {
        '555': {'home_wins': 3, 'draw_wins': 0, 'away_wins': 1, 'count': 4},
        'combined_leagues': {'home_wins': 0, 'draw_wins': 0, 'away_wins': 0, 'count': 0},
    }
    mock_build_elo_history_record.return_value = {'dummy_record': True}
    
    # Just return inputs as "updated" for simplicity
    def fake_calculate_elo_ratings(conn, home_score, away_score, home_elo, away_elo, elo_field, k_values, desc, k_draw, eta):
        # Log or assert which level you're working on
        if elo_field == 'elo_k':
            return {'elo_k': home_elo['elo_k'] + 10}, {'elo_k': away_elo['elo_k'] - 10}
        else:
            return home_elo, away_elo

    mock_calculate_elo_ratings.side_effect = fake_calculate_elo_ratings

    # Mock connection with commit and rollback
    conn = MagicMock()
    conn.commit = MagicMock()
    conn.rollback = MagicMock()

    # Use context manager
    with EloManager(conn, sample_matches) as manager:
        assert set(manager.team_ids) == {100, 200, 101, 201}
        assert set(manager.nation_names) == {'England'}
        assert set(manager.league_ids) == {10}
        assert set(manager.competition_ids) == {555}

        # Process match
        manager.process_match(sample_matches[0])

        assert manager.club_elos[100]['elo_k'] == 1510
        assert manager.club_elos[200]['elo_k'] == 1490

        # Check that elo_history recorded the build call
        assert len(manager.elo_history) == 1
        assert manager.elo_history[0] == {'dummy_record': True}

        # Check counts updated
        assert manager.counts['555']['home_wins'] == 4
        assert manager.counts['555']['count'] == 5
        assert manager.counts['combined_leagues']['home_wins'] == 1
        assert manager.counts['combined_leagues']['count'] == 1

    # On exit, check saves and commit called
    mock_save_history.assert_called_once_with(conn, manager.elo_history)
    mock_save_elos.assert_called_once_with(conn, manager.club_elos, manager.nation_elos, manager.league_elos, manager.continent_elos)
    mock_save_counts.assert_called_once_with(conn, manager.counts)
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
