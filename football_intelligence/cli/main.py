"""Command line interface for Football Intelligence operational workflows."""

import argparse
from collections.abc import Callable, Sequence
from typing import Any, Mapping, Optional, Protocol

from football_intelligence.cli.prediction_refresh import (
    add_prediction_refresh_arguments,
    run_prediction_refresh_from_args,
)


CURRENT_RESULT_MODEL_CONFIG = "result_model_early"


class FootballDataStatusRenderable(Protocol):
    def to_dict(self) -> dict[str, Any]:
        """Return display-ready Football Data Status facts and warnings."""


class PredictionBoardRenderable(Protocol):
    def to_dict(self) -> dict[str, Any]:
        """Return display-ready Prediction Board data."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="football-intelligence",
        description="Run Football Intelligence operational workflows.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    prediction_refresh = subcommands.add_parser(
        "prediction-refresh",
        help="Run Prediction Refresh without training a new model.",
    )
    add_prediction_refresh_arguments(prediction_refresh)
    prediction_refresh.set_defaults(command_handler=_handle_prediction_refresh)

    status = subcommands.add_parser(
        "status",
        help="Show Football Data Status facts and warnings.",
    )
    status.set_defaults(command_handler=_handle_status)

    board = subcommands.add_parser(
        "board",
        help="Show Prediction Board views.",
    )
    board_subcommands = board.add_subparsers(dest="board_command", required=True)
    today = board_subcommands.add_parser(
        "today",
        help="Show today's remaining Prediction Board.",
    )
    today.set_defaults(command_handler=_handle_board_today)

    model_training = subcommands.add_parser(
        "model-training",
        help="Run explicit Model Training and save model artifacts.",
    )
    model_training.add_argument(
        "config",
        nargs="?",
        default=CURRENT_RESULT_MODEL_CONFIG,
        help=(
            "ML config name to train. Defaults to the current result model "
            f"config: {CURRENT_RESULT_MODEL_CONFIG}."
        ),
    )
    model_training.add_argument(
        "--dry-run",
        action="store_true",
        help="Run training without saving model artifacts.",
    )
    model_training.add_argument(
        "--limit",
        type=int,
        help="Limit the Historical Feature Set sample count for testing.",
    )
    model_training.set_defaults(command_handler=_handle_model_training)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command_handler: Callable[[argparse.Namespace], int] = args.command_handler
    try:
        return command_handler(args)
    except ValueError as exc:
        parser.error(str(exc))


def _handle_model_training(args: argparse.Namespace) -> int:
    result = run_model_training(
        args.config,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    return 0 if result.get("success") else 1


def _handle_prediction_refresh(args: argparse.Namespace) -> int:
    return run_prediction_refresh_from_args(args)


def _handle_status(_args: argparse.Namespace) -> int:
    print(render_football_data_status(get_football_data_status()))
    return 0


def _handle_board_today(_args: argparse.Namespace) -> int:
    print(render_prediction_board(get_today_prediction_board()))
    return 0


def run_model_training(
    config_name: str,
    *,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> dict[str, Any]:
    from football_intelligence.predictions.model_training import (
        run_model_training as train_model,
    )

    return train_model(config_name, dry_run=dry_run, limit=limit)


def get_football_data_status() -> FootballDataStatusRenderable:
    from football_intelligence.status import FootballDataStatusService

    return FootballDataStatusService.from_config().get_status()


def get_today_prediction_board() -> PredictionBoardRenderable:
    from football_intelligence.board import PredictionBoardService

    return PredictionBoardService.from_config().today()


def render_football_data_status(status: FootballDataStatusRenderable) -> str:
    data = status.to_dict()
    latest_match = data["latest_completed_match"]
    odds_freshness = data["odds_freshness"]

    lines = [
        data["title"],
        f"Latest Completed Match: {_format_latest_completed_match(latest_match)}",
        (
            "Unprocessed Completed Matches: "
            f"{data['unprocessed_completed_matches']}"
        ),
        f"Latest Elo History Date: {_format_missing(data['latest_elo_history_date'])}",
        f"Future Feature Set Count: {data['future_feature_set_count']}",
        f"Next 7 Days Prediction Count: {data['prediction_count_next_7_days']}",
        (
            "Odds Freshness: latest retrieved "
            f"{_format_missing(odds_freshness['latest_retrieved_at'])}; "
            f"{odds_freshness['matches_with_odds_next_7_days']} matches with odds"
        ),
        "Top Premier League Elo Teams:",
    ]

    top_teams = data["top_premier_league_elo_teams"]
    if top_teams:
        lines.extend(
            f"  {index}. {team['team_name']} - {_format_missing(team['elo'])}"
            for index, team in enumerate(top_teams, start=1)
        )
    else:
        lines.append("  None")

    lines.append("Warnings:")
    if data["warnings"]:
        lines.extend(f"  - {warning['message']}" for warning in data["warnings"])
    else:
        lines.append("  None")

    return "\n".join(lines)


def render_prediction_board(board: PredictionBoardRenderable) -> str:
    data = board.to_dict()
    summary = data["summary"]
    lines = [
        f"{data['title']} - {data['date']}",
        (
            f"Window: {data['window']['starts_at']} to "
            f"{data['window']['ends_at']} ({data['window']['timezone']})"
        ),
        (
            "Summary: "
            f"{summary['upcoming_match_count']} Upcoming Matches; "
            f"{summary['matches_with_predictions']} with Predictions; "
            f"{summary['matches_with_odds']} with odds; "
            f"{summary['market_value_signal_count']} Market Value Signals"
        ),
    ]

    if data["empty_state"]:
        lines.append(data["empty_state"])
    else:
        lines.append("Matches:")
        for match in data["matches"]:
            lines.extend(_render_prediction_board_match(match))

    if data["warnings"]:
        lines.append("Warnings:")
        lines.extend(f"  - {warning['message']}" for warning in data["warnings"])

    return "\n".join(lines)


def _render_prediction_board_match(match: Mapping[str, Any]) -> list[str]:
    prediction = match["prediction"]
    odds_freshness = match["odds_freshness"]
    lines = [
        (
            f"  - {match['start_time']} | {match['home_team']} vs "
            f"{match['away_team']} ({match['competition']})"
        )
    ]
    if prediction:
        lines.append(
            "    Prediction: "
            f"{prediction['predicted_result']} "
            f"({_format_percentage(prediction['confidence'])})"
        )
    else:
        lines.append("    Prediction: missing")

    if odds_freshness["has_odds"]:
        lines.append(
            "    Odds Freshness: latest retrieved "
            f"{_format_missing(odds_freshness['latest_retrieved_at'])}"
        )
    else:
        lines.append("    Odds Freshness: missing")

    if match["market_value_signals"]:
        for signal in match["market_value_signals"]:
            lines.append(
                "    Market Value Signal: "
                f"{signal['outcome']} edge {_format_percentage(signal['edge'])}; "
                f"Paper Stake {_format_number(signal['paper_stake_percentage'])}%"
            )
    return lines


def _format_latest_completed_match(match: Mapping[str, Any] | None) -> str:
    if not match:
        return "None"
    return (
        f"{match['home_team']} {match['score']} {match['away_team']} "
        f"({match['competition']}, {match['start_time']})"
    )


def _format_missing(value: Any) -> str:
    if value is None:
        return "None"
    return str(value)


def _format_percentage(value: Any) -> str:
    if value is None:
        return "None"
    return f"{float(value) * 100:.1f}%"


def _format_number(value: Any) -> str:
    if value is None:
        return "None"
    return f"{float(value):.1f}"
