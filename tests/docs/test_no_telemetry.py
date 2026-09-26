"""No telemetry, no analytics — as a check, not a promise.

README, CLAUDE.md § "Things this project deliberately does not do" and
the help pages all say MAME Curator sends nothing anywhere. Until
2026-09-26 nothing enforced it; the README's "grep-gated" had no gate
behind it. This is that gate.

It fails if a known analytics / telemetry / crash-reporting package is a
DIRECT dependency (`pyproject.toml`, `frontend/package.json`), or if a
tracker's name or domain appears in the shipped sources (`src/`,
`frontend/src/`). Transitive dependencies are out of scope: the lockfile
carries packages this project never calls, and banning those would fail
on things nobody chose.

The list is deliberately specific. A match is a name nobody adds by
accident; extend it when a new service becomes common.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Package names, matched against the name part of each direct dependency.
_BANNED_PACKAGES = re.compile(
    r"(?i)^(@sentry/.*|sentry-sdk|posthog.*|mixpanel.*|@segment/.*|analytics-node"
    r"|@amplitude/.*|amplitude.*|react-ga4?|@datadog/.*|ddtrace|newrelic|bugsnag.*"
    r"|@bugsnag/.*|rollbar|opentelemetry.*|@opentelemetry/.*|logrocket|@fullstory/.*"
    r"|plausible-tracker|hotjar.*|@vercel/analytics)$"
)
# Tracker names and domains, matched anywhere in source text.
_BANNED_SOURCE = re.compile(
    r"(?i)google-analytics\.com|googletagmanager\.com|\bgtag\(|sentry\.io|posthog"
    r"|mixpanel|api\.amplitude\.com|plausible\.io|hotjar|logrocket|fullstory"
)


def _python_deps() -> list[str]:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    specs = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        specs.extend(extra)
    for group in data.get("dependency-groups", {}).values():
        specs.extend(s for s in group if isinstance(s, str))
    return [re.split(r"[\s<>=!~;\[]", s, maxsplit=1)[0] for s in specs]


def _frontend_deps() -> list[str]:
    data = json.loads((REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    return [*data.get("dependencies", {}), *data.get("devDependencies", {})]


def _source_hits() -> list[str]:
    hits = []
    for root, suffixes in (
        (REPO_ROOT / "src", {".py"}),
        (REPO_ROOT / "frontend" / "src", {".ts", ".tsx", ".html"}),
    ):
        for path in sorted(root.rglob("*")):
            if path.suffix not in suffixes or "__tests__" in path.parts:
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if _BANNED_SOURCE.search(line):
                    hits.append(f"{path.relative_to(REPO_ROOT)}:{n}: {line.strip()}")
    return hits


def test_no_telemetry_dependencies_or_trackers() -> None:
    banned = [d for d in _python_deps() + _frontend_deps() if _BANNED_PACKAGES.match(d)]
    assert not banned, f"telemetry/analytics dependency added: {banned}"
    hits = _source_hits()
    assert not hits, "tracker reference in shipped source:\n" + "\n".join(hits)


def test_the_patterns_catch_what_they_claim_to() -> None:
    """Planted samples: proves the check can fail, so a green run means something."""
    for name in ("@sentry/react", "posthog-js", "sentry-sdk", "@vercel/analytics"):
        assert _BANNED_PACKAGES.match(name), name
    for line in ("<script src='https://www.googletagmanager.com/gtag/js'>", "gtag('config', x)"):
        assert _BANNED_SOURCE.search(line), line
    for innocent in ("react", "fastapi", "lucide-react", "sentinel"):
        assert not _BANNED_PACKAGES.match(innocent), innocent
