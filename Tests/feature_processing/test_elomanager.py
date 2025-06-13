import pytest
from unittest.mock import MagicMock, patch
from utils.data_processing.processing_functions.elo_manager import EloManager  # Adjust import path as needed


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
            'away_team_name': 'TeamB'
        }
    ]


@patch('helpers.data_processing.processing_functions.elo_manager.get_bulk_entity_elos')
@patch('helpers.data_processing.processing_functions.elo_manager.get_counts')
@patch('helpers.data_processing.processing_functions.elo_manager.calculate_elo_ratings')
@patch('helpers.data_processing.processing_functions.elo_manager.build_elo_history_record')
@patch('helpers.data_processing.processing_functions.elo_manager.save_elo_history_bulk')
@patch('helpers.data_processing.processing_functions.elo_manager.save_updated_elos_bulk')
@patch('helpers.data_processing.processing_functions.elo_manager.save_updated_counts')
@patch('helpers.parsing_helpers.list.extract_team_ids')
@patch('helpers.parsing_helpers.list.extract_nation_names')
@patch('helpers.parsing_helpers.list.extract_league_ids')
@patch('helpers.parsing_helpers.list.extract_competition_ids')
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
    mock_extract_team_ids.return_value = [100, 200]
    mock_extract_nation_names.return_value = ['England']
    mock_extract_league_ids.return_value = [10]
    mock_extract_competition_ids.return_value = [555]

    mock_get_bulk_entity_elos.side_effect = lambda conn, table, key_field, ids: {id_: {'elo_k': 1500} for id_ in ids}
    mock_get_counts.return_value = {'555': {'home_wins': 1, 'draw_wins': 0, 'away_wins': 0, 'count': 1}}
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
        assert set(manager.team_ids) == {100, 200}
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
        assert manager.counts['555']['home_wins'] == 2  # incremented from 1 to 2
        assert manager.counts['555']['count'] == 2

    # On exit, check saves and commit called
    mock_save_history.assert_called_once_with(conn, manager.elo_history)
    mock_save_elos.assert_called_once_with(conn, manager.club_elos, manager.nation_elos, manager.league_elos)
    mock_save_counts.assert_called_once_with(conn, manager.counts)
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()