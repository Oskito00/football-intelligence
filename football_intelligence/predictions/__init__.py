"""Prediction home for inference, evaluation, and Model Training workflows."""

from football_intelligence._compat import LegacyExport, make_legacy_getattr

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

__all__ = list(_LEGACY_EXPORTS)
__getattr__ = make_legacy_getattr(_LEGACY_EXPORTS)
