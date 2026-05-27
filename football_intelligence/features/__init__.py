"""Feature pipeline home for Historical and Future Feature Sets."""

from football_intelligence._compat import LegacyExport, make_legacy_getattr
from football_intelligence.features.pipeline import (
    FeaturePipelineDependencies,
    FeaturePipelineResult,
    FeatureSetMode,
    build_future_feature_set,
    build_historical_feature_set,
    default_feature_pipeline_dependencies,
    run_feature_pipeline,
)

_LEGACY_EXPORTS = {
    "EloManager": LegacyExport(
        "data_processing.helpers.processing_functions.elo_manager",
        "EloManager",
    ),
}

__all__ = [
    "FeaturePipelineDependencies",
    "FeaturePipelineResult",
    "FeatureSetMode",
    "build_future_feature_set",
    "build_historical_feature_set",
    "default_feature_pipeline_dependencies",
    "run_feature_pipeline",
    *_LEGACY_EXPORTS,
]
__getattr__ = make_legacy_getattr(_LEGACY_EXPORTS)
