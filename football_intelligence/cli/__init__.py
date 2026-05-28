"""CLI home for operational Football Intelligence workflows.

Deployment-specific schedulers should call commands from this package as the
Match Intelligence Lifecycle migrates out of runtime-specific modules.
"""

from football_intelligence._compat import LegacyExport, make_legacy_getattr

from . import main as main

_LEGACY_EXPORTS = {
    "run_legacy_prediction_refresh": LegacyExport("scheduler.scheduler", "main"),
}

__all__ = ["main", "prediction_refresh_main", *_LEGACY_EXPORTS]
_legacy_getattr = make_legacy_getattr(_LEGACY_EXPORTS)


def __getattr__(name: str) -> object:
    if name == "prediction_refresh_main":
        from football_intelligence.cli.prediction_refresh import main

        return main

    return _legacy_getattr(name)
