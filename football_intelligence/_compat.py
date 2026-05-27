"""Compatibility helpers for staged imports from legacy modules."""

from collections.abc import Callable, Mapping
from importlib import import_module
from typing import NamedTuple


class LegacyExport(NamedTuple):
    module_path: str
    object_name: str


LegacyExports = Mapping[str, LegacyExport]


def resolve_legacy_export(exports: LegacyExports, name: str) -> object:
    """Resolve a lazy legacy export for product-namespace adapters."""
    try:
        legacy_export = exports[name]
    except KeyError as exc:
        raise AttributeError(f"module has no attribute {name!r}") from exc

    module = import_module(legacy_export.module_path)
    return getattr(module, legacy_export.object_name)


def make_legacy_getattr(exports: LegacyExports) -> Callable[[str], object]:
    """Build a module-level __getattr__ for lazy legacy exports."""

    def __getattr__(name: str) -> object:
        return resolve_legacy_export(exports, name)

    return __getattr__
