"""The purity invariant of ``onboarding.core``, checked mechanically.

A review comment can be ignored; this test cannot. If an effect enters the core, the import list or
the call graph below gives it away.
"""

from __future__ import annotations

import ast
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "onboarding" / "core"

FORBIDDEN_IMPORTS = {
    "httpx",
    "sqlalchemy",
    "asyncpg",
    "fastapi",
    "yaml",
    "logging",
    "random",
    "uuid",
    "time",
    "os",
    "socket",
    "requests",
    # Readers and recognizers are adapters (ADR 0015); importing one would put a model or a
    # decoder between the pure rules and their tests. ``onboarding.*`` is checked below, because
    # the core legitimately imports its own package.
    "pypdfium2",
    "pptx",
    "PIL",
    "cv2",
    "numpy",
    "paddleocr",
    "paddle",
    "rapidocr",
    "onnxruntime",
}
FORBIDDEN_CALLS = {
    ("datetime", "now"),
    ("datetime", "utcnow"),
    ("datetime", "today"),
    ("date", "today"),
    ("time", "time"),
    ("random", "random"),
    ("uuid", "uuid4"),
}


def _modules() -> list[Path]:
    return sorted(CORE.glob("*.py"))


def test_core_imports_no_effectful_modules() -> None:
    violations: list[str] = []
    for path in _modules():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            else:
                continue
            violations.extend(
                f"{path.name}: imports {name}" for name in names if name in FORBIDDEN_IMPORTS
            )

    assert violations == []


def test_core_never_reaches_into_its_own_adapter_layer() -> None:
    """``onboarding.*`` would let a value object call a repository; the import list above only
    catches the top-level name, so the package prefix is checked separately."""
    violations: list[str] = []
    for path in _modules():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            if module and module.startswith("onboarding.") and not _is_core(module):
                violations.append(f"{path.name}: imports from {module}")

    assert violations == []


def _is_core(module: str) -> bool:
    return module == "onboarding.core" or module.startswith("onboarding.core.")


def test_core_reads_no_ambient_time_or_randomness() -> None:
    violations: list[str] = []
    for path in _modules():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and (func.value.id, func.attr) in FORBIDDEN_CALLS
            ):
                violations.append(f"{path.name}: calls {func.value.id}.{func.attr}")

    assert violations == []
