"""CLI home for operational Football Intelligence workflows.

Deployment-specific runtimes should call commands from this package as the
Match Intelligence Lifecycle migrates out of runtime-specific modules.
"""

from . import main as main

__all__ = ["main", "prediction_refresh_main"]


def __getattr__(name: str) -> object:
    if name == "prediction_refresh_main":
        from football_intelligence.cli.prediction_refresh import main

        return main

    raise AttributeError(f"module has no attribute {name!r}")
