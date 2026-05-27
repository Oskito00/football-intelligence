"""Compatibility helpers for staged imports from legacy modules."""

from importlib import import_module
from typing import NamedTuple


class LegacyExport(NamedTuple):
    module_path: str
    object_name: str


def resolve_legacy_export(exports: dict[str, LegacyExport], name: str):
    """Resolve a lazy legacy export for product-namespace adapters."""
    try:
        legacy_export = exports[name]
    except KeyError as exc:
        raise AttributeError(f"module has no attribute {name!r}") from exc

    module = import_module(legacy_export.module_path)
    return getattr(module, legacy_export.object_name)
