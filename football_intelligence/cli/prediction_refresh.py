"""CLI command for running Prediction Refresh."""

from __future__ import annotations

import argparse

from football_intelligence.predictions.refresh import (
    DEFAULT_MODEL_CONFIG,
    run_prediction_refresh,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prediction-refresh",
        description="Run Prediction Refresh for the Match Intelligence Lifecycle.",
    )
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_prediction_refresh(
        model_config=args.model_config,
        include_odds=not args.skip_odds,
    )

    print(f"Prediction Refresh completed: {len(result.steps_run)} steps run")
    if result.steps_failed:
        print(f"Prediction Refresh failed steps: {len(result.steps_failed)}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
