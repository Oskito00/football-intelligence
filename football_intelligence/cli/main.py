"""Command line interface for Football Intelligence operational workflows."""

import argparse
from collections.abc import Sequence
from typing import Optional


CURRENT_RESULT_MODEL_CONFIG = "result_model_early"


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
    prediction_refresh.set_defaults(handler=_handle_prediction_refresh)

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
    model_training.set_defaults(handler=_handle_model_training)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


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


def run_prediction_refresh() -> None:
    from scheduler.scheduler import main as refresh

    refresh()


def run_model_training(config_name: str, *, dry_run: bool = False, limit: Optional[int] = None):
    from ml_pipeline.main_train import run_model_training as train

    return train(config_name, dry_run=dry_run, limit=limit)
