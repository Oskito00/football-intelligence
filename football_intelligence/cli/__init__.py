"""CLI home for operational Football Intelligence workflows.

Deployment-specific schedulers should call commands from this package as the
Match Intelligence Lifecycle migrates out of runtime-specific modules.
"""

from football_intelligence._compat import LegacyExport, make_legacy_getattr

from . import main as main

_LEGACY_EXPORTS = {
    "run_legacy_prediction_refresh": LegacyExport("scheduler.scheduler", "main"),
    "run_legacy_analyst_console": LegacyExport("chatbot.main", "main"),
}

__all__ = [
    "main",
    *list(_LEGACY_EXPORTS),
]
__getattr__ = make_legacy_getattr(_LEGACY_EXPORTS)
