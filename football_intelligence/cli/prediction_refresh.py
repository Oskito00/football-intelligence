"""CLI command for running Prediction Refresh."""

from __future__ import annotations

import argparse

from football_intelligence.predictions.refresh import (
    AVAILABLE_PREDICTION_REFRESH_SELECTORS,
    DEFAULT_MODEL_CONFIG,
    PREDICTION_REFRESH_STEP_HELP,
    run_prediction_refresh,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prediction-refresh",
        description="Run Prediction Refresh for the Match Intelligence Lifecycle.",
    )
    add_prediction_refresh_arguments(parser)
    return parser


def add_prediction_refresh_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared Prediction Refresh options to a parser or subparser."""
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
        choices=AVAILABLE_PREDICTION_REFRESH_SELECTORS,
        metavar="PART",
        help=(
            "Run one Prediction Refresh part. Repeat to run multiple parts. "
            "Use --list-parts to see available parts."
        ),
    )
    parser.add_argument(
        "--list-parts",
        action="store_true",
        help="List Prediction Refresh parts and exit without running.",
    )


def print_available_prediction_refresh_parts() -> None:
    print("Available Prediction Refresh parts:")
    for part, description in PREDICTION_REFRESH_STEP_HELP:
        print(f"  {part:<20} {description}")


def run_prediction_refresh_from_args(args: argparse.Namespace) -> int:
    if args.list_parts:
        print_available_prediction_refresh_parts()
        return 0

    if args.only and args.skip_odds:
        raise ValueError(
            "--skip-odds only applies to a full refresh; omit it with --only"
        )

    result = run_prediction_refresh(
        model_config=args.model_config,
        include_odds=not args.skip_odds,
        selected_steps=args.only,
    )

    selected = f" ({', '.join(args.only)})" if args.only else ""
    print(f"Prediction Refresh{selected} completed: {len(result.steps_run)} steps run")
    if result.steps_failed:
        print(f"Prediction Refresh failed steps: {len(result.steps_failed)}")
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run_prediction_refresh_from_args(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
