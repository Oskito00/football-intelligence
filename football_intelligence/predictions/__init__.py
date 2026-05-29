"""Prediction home for inference, Prediction Refresh, and Model Training."""

from football_intelligence.predictions.refresh import (
    PredictionRefreshResult,
    PredictionRefreshStep,
    run_prediction_refresh,
)

_PRODUCT_EXPORTS = {
    "ResultFeatureLoader": (
        "football_intelligence.predictions.result_features",
        "ResultFeatureLoader",
    ),
    "infer_result_model": (
        "football_intelligence.predictions.inference",
        "infer_result_model",
    ),
    "run_model_training": (
        "football_intelligence.predictions.model_training",
        "run_model_training",
    ),
    "run_prediction_inference": (
        "football_intelligence.predictions.inference_entrypoint",
        "main",
    ),
    "train_result_model": (
        "football_intelligence.predictions.training",
        "train_result_model",
    ),
}

__all__ = [
    "PredictionRefreshResult",
    "PredictionRefreshStep",
    "run_prediction_refresh",
    *_PRODUCT_EXPORTS,
]


def __getattr__(name: str):
    if name not in _PRODUCT_EXPORTS:
        raise AttributeError(name)

    from importlib import import_module

    module_path, attribute_name = _PRODUCT_EXPORTS[name]
    module = import_module(module_path)
    return getattr(module, attribute_name)
