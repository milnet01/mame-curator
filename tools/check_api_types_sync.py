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
    """True iff `cls` inherits from `pydantic.BaseModel` (by name or qualified).

    FP11 § C2: the prior matcher accepted any `*.BaseModel` attribute access
    (e.g. `pydantic_settings.BaseModel`, custom shims), risking misclassification.
    Restricted to bare `BaseModel` (the only form actually used in this
    codebase) and `pydantic.BaseModel`. Anything else won't match — by
    design, since we don't want to track non-Pydantic models.
    """
    for base in cls.bases:
        if isinstance(base, ast.Name) and base.id == "BaseModel":
            return True
        if (
            isinstance(base, ast.Attribute)
            and base.attr == "BaseModel"
            and isinstance(base.value, ast.Name)
            and base.value.id == "pydantic"
        ):
            return True
    return False


def _is_classvar(annotation: ast.expr) -> bool:
    if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
        return annotation.value.id == "ClassVar"
    if isinstance(annotation, ast.Name):
        return annotation.id == "ClassVar"
    return False


_INTERFACE_HEADER_RE = re.compile(r"export\s+interface\s+(\w+)\s*\{")
_FIELD_LINE_RE = re.compile(r"^\s*(\w+)\??\s*:")


class TsParseError(Exception):
    """Raised on malformed TS input (unbalanced braces, etc.)."""


def _strip_ts_comments(text: str) -> str:
    """Remove `/* … */` and `// …` comments.

    String-literal blind, but no interface body in `types.ts` uses `//`
    inside a string literal today; if that ever changes, the gate will
    mis-strip and the resulting field drift will trip the parity check
    loudly — far better than a silent miss.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _extract_interface_body(text: str, header_end: int) -> tuple[str, int]:
    """Walk from the position right after `{` and return the body + end-pos.

    Brace-balanced scan so nested object types (`bar: { x: number }`) don't
    truncate the body at the inner `}`. FP11 § C1 supersedes the prior
    `[^}]*` regex which silently dropped fields after the first inner `}`.
    """
    depth = 1
    i = header_end
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[header_end:i], i + 1
        i += 1
    raise TsParseError(f"unbalanced braces at offset {header_end} (no matching `}}`)")


def _outer_field_names(body: str) -> set[str]:
    """Return the field names declared at the OUTER level of an interface body.

    Skips field-name matches inside nested object literals (`bar: { x: ... }`
    must not contribute `x` to the parent's field set). Walks lines while
    tracking brace depth.
    """
    fields: set[str] = set()
    depth = 0
    for raw_line in body.splitlines():
        # Match field-name at depth 0 BEFORE we advance the depth for this line.
        if depth == 0:
            m = _FIELD_LINE_RE.match(raw_line)
            if m:
                fields.add(m.group(1))
        for ch in raw_line:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth = max(0, depth - 1)
    return fields


def parse_ts_interfaces(path: Path) -> dict[str, set[str]]:
    """Return {InterfaceName: {field_name, …}} from a TS file.

    Brace-balanced parse — interfaces with nested object types parse
    correctly (FP11 § C1). Optional fields (`foo?: …`) count by their
    base name.
    """
    text = _strip_ts_comments(path.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    pos = 0
    while True:
        match = _INTERFACE_HEADER_RE.search(text, pos)
        if not match:
            break
        name = match.group(1)
        body, end_pos = _extract_interface_body(text, match.end())
        out[name] = _outer_field_names(body)
        pos = end_pos
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


class DuplicateModelError(Exception):
    """Raised on a divergent duplicate-name BaseModel declaration.

    Two source files declaring `class Foo(BaseModel)` with different
    field sets is ambiguous — the drift gate's accuracy depends on
    globally-unique model names, so a divergence must fail loud
    (FP11 § C3) rather than silently pick one and warn.
    """


def collect_python_models(sources: Iterable[str]) -> dict[str, set[str]]:
    """Walk each source file and return the merged {ClassName: fields} map.

    Identical re-declarations (same fields) are tolerated (Python may
    legitimately re-export a base via `import as`); divergent ones raise
    `DuplicateModelError` so the drift gate doesn't pick the lucky one
    and run against the wrong model.
    """
    aggregated: dict[str, set[str]] = {}
    origins: dict[str, str] = {}
    for rel in sources:
        path = REPO_ROOT / rel
        if not path.is_file():
            print(f"warning: {rel} not found; skipping", file=sys.stderr)
            continue
        for name, fields in parse_python_models(path).items():
            existing = aggregated.get(name)
            if existing is not None and existing != fields:
                raise DuplicateModelError(
                    f"class {name!r} declared in {origins[name]!r} with fields "
                    f"{sorted(existing)} AND in {rel!r} with fields "
                    f"{sorted(fields)} — globally-unique BaseModel names are "
                    "required so the drift gate compares against the right model"
                )
            if existing is None:
                aggregated[name] = fields
                origins[name] = rel
    return aggregated


def main() -> int:
    """Run the drift gate; return 0 on parity, 1 if any finding fires."""
    try:
        python_models = collect_python_models(PYTHON_SOURCES)
    except DuplicateModelError as exc:
        print(f"error: duplicate model: {exc}", file=sys.stderr)
        return 1
    ts_path = REPO_ROOT / TS_TYPES_FILE
    if not ts_path.is_file():
        print(f"error: {TS_TYPES_FILE} not found", file=sys.stderr)
        return 1
    try:
        ts_interfaces = parse_ts_interfaces(ts_path)
    except TsParseError as exc:
        print(f"error: TS parse failed: {exc}", file=sys.stderr)
        return 1
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
