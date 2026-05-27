"""Product namespace for the Football Intelligence Agent migration.

Existing implementation-era packages remain importable while follow-up slices
move behavior into this namespace behind stable product concepts.
"""

PRODUCT_NAME = "Football Intelligence Agent"

__all__ = [
    "PRODUCT_NAME",
    "analyst",
    "ingestion",
    "features",
    "predictions",
    "api",
    "database",
    "cli",
]
