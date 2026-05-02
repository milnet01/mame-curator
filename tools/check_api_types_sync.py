#!/usr/bin/env python3
"""Bidirectional drift gate for the Python ↔ TypeScript API type contract.

Per `docs/specs/P06.md` § "API contract surface": the frontend hand-mirrors
Pydantic models from `mame_curator.api.schemas` (and re-exports) into
`frontend/src/api/types.ts`. This script enforces field parity across both
sides at PR time so a Pydantic-only field doesn't silently get dropped on
the wire.

Stdlib only — `ast` parses the Python side, regex parses the TS side.

Rules:
  - For every `export interface Foo` in the TS file there MUST be a matching
    Pydantic class named `Foo` in one of the scanned modules.
  - Field sets MUST be identical for shared names (TS is required to mirror
    every Pydantic field; TS is not allowed to add fields).
  - Pydantic types not mirrored on the TS side are intentionally allowed —
    only the routes hit by the SPA need TS interfaces.

Exit 0 on parity, 1 on any drift (with a sorted finding list to stderr).
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Python modules that contribute Pydantic models reachable from api/schemas.py.
PYTHON_SOURCES = (
    "src/mame_curator/api/schemas.py",
    "src/mame_curator/api/errors.py",
    "src/mame_curator/copy/types.py",
    "src/mame_curator/parser/models.py",
    "src/mame_curator/filter/config.py",
    "src/mame_curator/filter/sessions.py",
    "src/mame_curator/filter/types.py",
)

# Hand-mirrored TS interface dump.
TS_TYPES_FILE = "frontend/src/api/types.ts"


def parse_python_models(path: Path) -> dict[str, set[str]]:
    """Walk a Python file's AST; return {ClassName: {field_name, …}}.

    A class counts as a Pydantic model if it inherits from BaseModel (the
    only base used in this codebase). Field names come from class-level
    AnnAssign nodes; methods, model_config, ClassVars, and underscore-prefixed
    private attrs are skipped.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not _inherits_basemodel(node):
            continue
        fields: set[str] = set()
        for item in node.body:
            if not isinstance(item, ast.AnnAssign):
                continue
            target = item.target
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if name == "model_config" or name.startswith("_"):
                continue
            if _is_classvar(item.annotation):
                continue
            fields.add(name)
        out[node.name] = fields
    return out


def _inherits_basemodel(cls: ast.ClassDef) -> bool:
    for base in cls.bases:
        if isinstance(base, ast.Name) and base.id == "BaseModel":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
            return True
    return False


def _is_classvar(annotation: ast.expr) -> bool:
    if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
        return annotation.value.id == "ClassVar"
    if isinstance(annotation, ast.Name):
        return annotation.id == "ClassVar"
    return False


_INTERFACE_RE = re.compile(
    r"export\s+interface\s+(\w+)\s*\{([^}]*)\}",
    re.MULTILINE | re.DOTALL,
)
_FIELD_RE = re.compile(r"^\s*(\w+)\??\s*:", re.MULTILINE)


def parse_ts_interfaces(path: Path) -> dict[str, set[str]]:
    """Return {InterfaceName: {field_name, …}} from a TS file.

    Strips `// …` and `/* … */` comments before matching so commented-out
    fields don't leak in. Optional fields (`foo?: …`) count by their name.
    """
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    out: dict[str, set[str]] = {}
    for match in _INTERFACE_RE.finditer(text):
        name = match.group(1)
        body = match.group(2)
        out[name] = {m.group(1) for m in _FIELD_RE.finditer(body)}
    return out


def find_drift(
    python_models: dict[str, set[str]],
    ts_interfaces: dict[str, set[str]],
) -> list[str]:
    """Return a sorted list of human-readable drift findings."""
    findings: list[str] = []
    for ts_name in sorted(ts_interfaces):
        py_fields = python_models.get(ts_name)
        if py_fields is None:
            findings.append(
                f"{ts_name}: TS interface has no Pydantic counterpart "
                f"(checked {len(python_models)} models across "
                f"{len(PYTHON_SOURCES)} files)"
            )
            continue
        ts_fields = ts_interfaces[ts_name]
        missing = sorted(py_fields - ts_fields)
        extra = sorted(ts_fields - py_fields)
        if missing:
            findings.append(
                f"{ts_name}: present in Pydantic but missing in TS: {', '.join(missing)}"
            )
        if extra:
            findings.append(f"{ts_name}: present in TS but missing in Pydantic: {', '.join(extra)}")
    return findings


def collect_python_models(sources: Iterable[str]) -> dict[str, set[str]]:
    """Walk each source file and return the merged {ClassName: fields} map."""
    aggregated: dict[str, set[str]] = {}
    for rel in sources:
        path = REPO_ROOT / rel
        if not path.is_file():
            print(f"warning: {rel} not found; skipping", file=sys.stderr)
            continue
        for name, fields in parse_python_models(path).items():
            if name in aggregated and aggregated[name] != fields:
                # Same class name in two source files with different field sets
                # would be ambiguous; prefer the first read and warn.
                print(
                    f"warning: duplicate class {name} in {rel}; "
                    "skipping conflicting later definition",
                    file=sys.stderr,
                )
                continue
            aggregated[name] = fields
    return aggregated


def main() -> int:
    """Run the drift gate; return 0 on parity, 1 if any finding fires."""
    python_models = collect_python_models(PYTHON_SOURCES)
    ts_path = REPO_ROOT / TS_TYPES_FILE
    if not ts_path.is_file():
        print(f"error: {TS_TYPES_FILE} not found", file=sys.stderr)
        return 1
    ts_interfaces = parse_ts_interfaces(ts_path)
    findings = find_drift(python_models, ts_interfaces)
    if findings:
        print(
            f"API type drift: {len(findings)} finding(s) "
            f"({len(ts_interfaces)} TS interfaces, {len(python_models)} "
            "Pydantic models):",
            file=sys.stderr,
        )
        for line in findings:
            print(f"  - {line}", file=sys.stderr)
        return 1
    print(
        f"API types in sync: {len(ts_interfaces)} TS interfaces match "
        f"Pydantic ({len(python_models)} models scanned)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
