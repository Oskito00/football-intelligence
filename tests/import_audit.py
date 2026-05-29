from __future__ import annotations

import ast
from collections.abc import Callable, Iterable
from pathlib import Path


def find_imports_matching(
    roots: Path | Iterable[Path],
    predicate: Callable[[str], bool],
    project_root: Path,
) -> list[tuple[Path, str]]:
    """Find imported modules under roots that match a predicate."""
    offenders = []

    for root in _as_roots(roots):
        for path in python_files(root):
            for module_name in imported_modules(path):
                if predicate(module_name):
                    offenders.append((path.relative_to(project_root), module_name))

    return offenders


def python_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]

    return sorted(
        path for path in root.rglob("*.py") if "__pycache__" not in path.parts
    )


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)

    return modules


def is_module_or_child(module_name: str, package_name: str) -> bool:
    return module_name == package_name or module_name.startswith(f"{package_name}.")


def _as_roots(roots: Path | Iterable[Path]) -> tuple[Path, ...]:
    if isinstance(roots, Path):
        return (roots,)

    return tuple(roots)
