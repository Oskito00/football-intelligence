"""Command line interface for Football Intelligence operational workflows."""

import argparse
from collections.abc import Callable, Sequence
from typing import Any, Mapping, Optional, Protocol

from football_intelligence.cli.prediction_refresh import (
    add_prediction_refresh_arguments,
    run_prediction_refresh_from_args,
)
from football_intelligence.value import DEFAULT_SIGNAL_DAYS
from football_intelligence.value_backtest import ValueBacktestConfig


CURRENT_RESULT_MODEL_CONFIG = "result_model_early"


class FootballDataStatusRenderable(Protocol):
    def to_dict(self) -> dict[str, Any]:
        """Return display-ready Football Data Status facts and warnings."""


class PredictionBoardRenderable(Protocol):
    def to_dict(self) -> dict[str, Any]:
        """Return display-ready Prediction Board data."""


class MarketValueSignalRenderable(Protocol):
    def to_dict(self) -> dict[str, Any]:
        """Return display-ready Market Value Signal scan data."""


class ValueBacktestRenderable(Protocol):
    def to_dict(self) -> dict[str, Any]:
        """Return display-ready Value Backtest data."""


class MarketValueSignalServiceLike(Protocol):
    def today(self) -> MarketValueSignalRenderable:
        """Return today's Market Value Signals."""

    def next_days(
        self,
        *,
        days: int = DEFAULT_SIGNAL_DAYS,
    ) -> MarketValueSignalRenderable:
        """Return Market Value Signals for the next N days."""


class ValueBacktestServiceLike(Protocol):
    def run(
        self,
        config: ValueBacktestConfig | None = None,
    ) -> ValueBacktestRenderable:
        """Run a Value Backtest report."""


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

    value_picks = subcommands.add_parser(
        "value-picks",
        help="Show Market Value Signals for upcoming matches.",
    )
    value_window = value_picks.add_mutually_exclusive_group()
    value_window.add_argument(
        "--today",
        action="store_true",
        help="Show today's remaining local-date Market Value Signals.",
    )
    value_window.add_argument(
        "--days",
        type=int,
        default=DEFAULT_SIGNAL_DAYS,
        help=f"Scan the next N days. Defaults to {DEFAULT_SIGNAL_DAYS}.",
    )
    value_picks.set_defaults(command_handler=_handle_value_picks)

    value_backtest = subcommands.add_parser(
        "value-backtest",
        help="Run a Value Backtest report for historical Predictions.",
    )
    value_backtest.add_argument(
        "--starting-bankroll",
        type=float,
        help="Starting bankroll for Paper Stake simulation. Defaults to 100.",
    )
    value_backtest.add_argument(
        "--kelly-fraction",
        type=float,
        help="Kelly fraction multiplier. 1.0 is full Kelly.",
    )
    value_backtest.add_argument(
        "--min-expected-value",
        type=float,
        help="Minimum expected value required for a Market Value Signal.",
    )
    value_backtest.add_argument(
        "--odds-mode",
        choices=("best", "average"),
        help="Backtest Odds Mode. Defaults to best.",
    )
    value_backtest.add_argument(
        "--allow-late-predictions",
        action="store_true",
        help=(
            "Allow retained Predictions with late or missing timestamps. "
            "Marks the report as less trustworthy."
        ),
    )
    value_backtest.set_defaults(command_handler=_handle_value_backtest)

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


def _handle_value_picks(args: argparse.Namespace) -> int:
    service = get_market_value_signal_service()
    scan = service.today() if args.today else service.next_days(days=args.days)
    print(render_market_value_signals(scan))
    return 0


def _handle_value_backtest(args: argparse.Namespace) -> int:
    result = get_value_backtest_service().run(_value_backtest_config_from_args(args))
    print(render_value_backtest(result))
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


def get_market_value_signal_service() -> MarketValueSignalServiceLike:
    from football_intelligence.value import MarketValueSignalService

    return MarketValueSignalService.from_config()


def get_value_backtest_service() -> ValueBacktestServiceLike:
    from football_intelligence.value_backtest import ValueBacktestService

    return ValueBacktestService.from_config()


def _value_backtest_config_from_args(
    args: argparse.Namespace,
) -> ValueBacktestConfig | None:
    config_overrides: dict[str, Any] = {
        "starting_bankroll": args.starting_bankroll,
        "kelly_multiplier": args.kelly_fraction,
        "min_expected_value": args.min_expected_value,
        "odds_mode": args.odds_mode,
        "strict_prediction_timing": (
            False if args.allow_late_predictions else None
        ),
    }
    selected_overrides = {
        key: value for key, value in config_overrides.items() if value is not None
    }
    if not selected_overrides:
        return None

    return ValueBacktestConfig(**selected_overrides)


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
    window = data["window"]
    summary = data["summary"]
    lines = [
        f"{data['title']} - {data['date']}",
        (
            f"Window: {window['starts_at']} to {window['ends_at']} "
            f"({window['timezone']})"
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


def render_market_value_signals(scan: MarketValueSignalRenderable) -> str:
    data = scan.to_dict()
    window = data["window"]
    summary = data["summary"]
    lines = [
        f"{data['title']} - {window['label']}",
        (
            f"Window: {window['starts_at']} to {window['ends_at']} "
            f"({window['timezone']})"
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
        lines.append("Signals:")
        for signal in data["signals"]:
            lines.extend(_render_market_value_signal(signal))

    if data["warnings"]:
        lines.append("Warnings:")
        lines.extend(f"  - {warning['message']}" for warning in data["warnings"])

    return "\n".join(lines)


def render_value_backtest(result: ValueBacktestRenderable) -> str:
    data = result.to_dict()
    summary = data["summary"]
    configuration = data["configuration"]
    lines = [
        data["title"],
        data["headline"],
        f"Starting Bankroll: {_format_decimal_money(summary['starting_bankroll'])}",
        f"Final Bankroll: {_format_decimal_money(summary['final_bankroll'])}",
        f"Profit/Loss: {_format_decimal_money(summary['profit_loss'])}",
        f"ROI: {_format_percentage(summary['roi'])}",
        f"Eligible Completed Matches: {summary['eligible_match_count']}",
        f"Paper Bets: {summary['paper_bet_count']}",
        f"Wins/Losses: {summary['wins']}/{summary['losses']}",
        f"Hit Rate: {_format_percentage(summary['hit_rate'])}",
        f"Average Odds: {_format_decimal_odds(summary['average_odds'])}",
        (
            "Average Expected Value: "
            f"{_format_percentage(summary['average_expected_value'])}"
        ),
        f"Max Drawdown: {_format_percentage(summary['max_drawdown'])}",
        (
            "Kelly Fraction: "
            f"{_format_strategy_number(configuration['kelly_multiplier'])}"
        ),
        (
            "Minimum Expected Value: "
            f"{_format_percentage(configuration['min_expected_value'])}"
        ),
        f"Odds Mode: {configuration['odds_mode']}",
        (
            "Prediction Timing: "
            f"{_format_backtest_prediction_timing(configuration)}"
        ),
        (
            "Paper Stake Rule: "
            f"{_format_strategy_number(configuration['kelly_multiplier'])}x "
            "Kelly on every "
            "positive-Kelly Market Value Signal"
        ),
    ]

    if data["skipped_matches"]:
        lines.append("Skipped Matches:")
        lines.extend(
            f"  - {reason}: {count}"
            for reason, count in sorted(data["skipped_matches"].items())
        )

    if data["paper_bets"]:
        lines.append("Paper Stakes:")
        for bet in data["paper_bets"]:
            lines.extend(_render_backtest_paper_bet(bet))

    if data["warnings"]:
        lines.append("Warnings:")
        lines.extend(f"  - {warning['message']}" for warning in data["warnings"])

    return "\n".join(lines)


def _render_backtest_paper_bet(bet: Mapping[str, Any]) -> list[str]:
    return [
        (
            f"  - {bet['start_time']} | {bet['home_team']} vs "
            f"{bet['away_team']} | {bet['outcome']} | {bet['result']}"
        ),
        (
            f"    Paper Stake: {_format_decimal_money(bet['stake'])}; "
            f"Odds: {_format_decimal_odds(bet['odds'])}; "
            f"EV: {_format_percentage(bet['expected_value'])}; "
            f"Kelly: {_format_percentage(bet['kelly_fraction'])}"
        ),
        (
            "    Bankroll: "
            f"{_format_decimal_money(bet['bankroll_before_match'])} -> "
            f"{_format_decimal_money(bet['bankroll_after_settlement'])}; "
            f"Profit/Loss: {_format_decimal_money(bet['profit_loss'])}"
        ),
    ]


def _render_market_value_signal(signal: Mapping[str, Any]) -> list[str]:
    return [
        (
            f"  - {signal['start_time']} | {signal['home_team']} vs "
            f"{signal['away_team']} ({signal['competition']})"
        ),
        f"    Outcome: {signal['outcome']}",
        f"    Model Probability: {_format_percentage(signal['model_probability'])}",
        f"    Best Odds: {_format_decimal_odds(signal['best_odds'])}",
        f"    Implied Probability: {_format_percentage(signal['implied_probability'])}",
        f"    Edge: {_format_percentage(signal['edge'])}",
        f"    Bookmaker: {_format_missing(signal['bookmaker'])}",
        f"    Paper Stake: {_format_number(signal['paper_stake_percentage'])}%",
    ]


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


def _format_strategy_number(value: Any) -> str:
    if value is None:
        return "None"
    formatted = f"{float(value):.4f}".rstrip("0").rstrip(".")
    if "." not in formatted:
        return f"{formatted}.0"
    return formatted


def _format_backtest_prediction_timing(configuration: Mapping[str, Any]) -> str:
    if configuration.get("strict_prediction_timing"):
        return "strict pre-kickoff"
    return "late or missing timestamps allowed"


def _format_decimal_odds(value: Any) -> str:
    if value is None:
        return "None"
    return f"{float(value):.2f}"


def _format_decimal_money(value: Any) -> str:
    if value is None:
        return "None"
    return f"{float(value):.2f}"
