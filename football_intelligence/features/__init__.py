"""Feature pipeline home for Historical and Future Feature Sets.

Compatibility exports map product-language names onto existing feature
builders until the shared feature lifecycle is introduced.
"""

from football_intelligence._compat import LegacyExport, make_legacy_getattr

_LEGACY_EXPORTS = {
    "build_historical_feature_set": LegacyExport(
        "data_processing.for_training.match_result_features",
        "process_matches",
    ),
    "build_future_feature_set": LegacyExport(
        "data_processing.for_inferencing.match_result_features",
        "process_future_matches",
    ),
    "EloManager": LegacyExport(
        "data_processing.helpers.processing_functions.elo_manager",
        "EloManager",
    ),
}

__all__ = list(_LEGACY_EXPORTS)
__getattr__ = make_legacy_getattr(_LEGACY_EXPORTS)
