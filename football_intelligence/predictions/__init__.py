"""Prediction home for inference, Prediction Refresh, and Model Training."""

from football_intelligence._compat import LegacyExport, make_legacy_getattr
from football_intelligence.predictions.refresh import (
    PredictionRefreshResult,
    PredictionRefreshStep,
    run_prediction_refresh,
)

_LEGACY_EXPORTS = {
    "run_prediction_inference": LegacyExport("ml_pipeline.main_infer", "main"),
    "infer_result_model": LegacyExport(
        "ml_pipeline.inference.infer_result_model",
        "infer_result_model",
    ),
    "train_result_model": LegacyExport(
        "ml_pipeline.training.train_result_model",
        "train_result_model",
    ),
}

__all__ = [
    "PredictionRefreshResult",
    "PredictionRefreshStep",
    "run_prediction_refresh",
    *_LEGACY_EXPORTS,
]
__getattr__ = make_legacy_getattr(_LEGACY_EXPORTS)
