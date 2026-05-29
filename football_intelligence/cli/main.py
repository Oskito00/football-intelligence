"""Command line interface for Football Intelligence operational workflows."""

import argparse
from collections.abc import Callable, Sequence
from typing import Any, Mapping, Optional, Protocol


CURRENT_RESULT_MODEL_CONFIG = "result_model_early"


class FootballDataStatusRenderable(Protocol):
    def to_dict(self) -> dict[str, Any]:
        """Return display-ready Football Data Status facts and warnings."""


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
    prediction_refresh.set_defaults(command_handler=_handle_prediction_refresh)

    status = subcommands.add_parser(
        "status",
        help="Show Football Data Status facts and warnings.",
    )
    status.set_defaults(command_handler=_handle_status)

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
    return command_handler(args)


def _handle_model_training(args: argparse.Namespace) -> int:
    result = run_model_training(
        args.config,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    return 0 if result.get("success") else 1


def _handle_prediction_refresh(args: argparse.Namespace) -> int:
    run_prediction_refresh()
    return 0


def _handle_status(_args: argparse.Namespace) -> int:
    print(render_football_data_status(get_football_data_status()))
    return 0


def run_prediction_refresh() -> None:
    from football_intelligence.predictions.refresh import run_prediction_refresh as refresh

    refresh()


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
