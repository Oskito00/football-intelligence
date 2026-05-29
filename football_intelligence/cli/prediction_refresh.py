"""CLI command for running Prediction Refresh."""

from __future__ import annotations

import argparse

from football_intelligence.predictions.refresh import (
    DEFAULT_MODEL_CONFIG,
    PREDICTION_REFRESH_SELECTOR_CHOICES,
    run_prediction_refresh,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prediction-refresh",
        description="Run Prediction Refresh for the Match Intelligence Lifecycle.",
    )
    add_arguments(parser)
    return parser


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add Prediction Refresh arguments to a parser or subparser."""
    parser.add_argument(
        "--model-config",
        default=DEFAULT_MODEL_CONFIG,
        help="Inference config name to use with the current model.",
    )
    parser.add_argument(
        "--skip-odds",
        action="store_true",
        help="Skip odds refresh after predictions are updated.",
    )
    parser.add_argument(
        "--only",
        action="append",
        choices=PREDICTION_REFRESH_SELECTOR_CHOICES,
        default=[],
        metavar="SELECTOR",
        help=(
            "Run only one Prediction Refresh selector. "
            "May be repeated for multiple selectors."
        ),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_from_args(args)


def run_from_args(args: argparse.Namespace) -> int:
    result = run_prediction_refresh(
        model_config=args.model_config,
        include_odds=not args.skip_odds,
        selectors=tuple(args.only),
    )

    print(f"Prediction Refresh completed: {len(result.steps_run)} steps run")
    if result.steps_failed:
        print(f"Prediction Refresh failed steps: {len(result.steps_failed)}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
