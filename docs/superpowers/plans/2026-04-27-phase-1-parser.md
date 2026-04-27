# Phase 1 — DAT + INI Parsers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pure-Python `parser/` module that turns the user's MAME DAT XML and the five `.ini` reference files into typed in-memory data, plus a CLI smoke command (`mame-curator parse`) that prints sane summary stats. Foundation for Phase 2's filter rule chain.

**Architecture:** `lxml.iterparse` streams the 48 MB DAT XML so we never load the full tree. Parsed machines become **frozen Pydantic 2 models** (immutable, validated, auto-typed). Each `.ini` file is parsed by a single small `_parse_simple_ini()` helper composed into per-file functions. CHD detection comes from a separate official MAME `-listxml` (the Pleasuredome ROM-set DAT does not contain `<disk>` elements). Manufacturer fields like `"Capcom (Sega license)"` are split into publisher + developer.

**Tech Stack:** Python 3.12+, `lxml.iterparse`, Pydantic 2, stdlib `argparse` (kept lightweight; no extra dep), `rich` for CLI output formatting (already a runtime dep).

**Companion docs:**
- [Design spec §6.1](../specs/2026-04-27-mame-curator-design.md#61-parser)
- [Roadmap Phase 1](../specs/2026-04-27-roadmap.md#phase-1--dat--ini-parsers-parser)
- [Coding standards](../../standards/coding-standards.md)

**Acceptance (lifted from roadmap):**
- [ ] All listed tests pass.
- [ ] `parser/spec.md` exists and matches the implementation.
- [ ] Coverage on `parser/` ≥ 90%.
- [ ] CLI smoke run on user's real DAT completes in <30 s and prints a sane-looking summary.
- [ ] No public function exceeds 50 lines (per coding standards §2).

---

## File Structure

| Path | Responsibility |
|---|---|
| `src/mame_curator/parser/__init__.py` | Public re-exports: `Machine`, `parse_dat`, `parse_catver`, `parse_languages`, `parse_bestgames`, `parse_mature`, `parse_series`, `parse_listxml_disks`, `split_manufacturer`. |
| `src/mame_curator/parser/spec.md` | Audit surface: contract for every public symbol. |
| `src/mame_curator/parser/models.py` | `Machine` Pydantic model + supporting types (`DriverStatus` enum, `Rom`, `BiosSet`). |
| `src/mame_curator/parser/dat.py` | `parse_dat(path)` — streams XML via `lxml.iterparse`, handles `.zip`-wrapped XML transparently. |
| `src/mame_curator/parser/ini.py` | `_parse_simple_ini` helper + the five typed wrappers (`parse_catver`, `parse_languages`, `parse_bestgames`, `parse_mature`, `parse_series`). |
| `src/mame_curator/parser/listxml.py` | `parse_listxml_disks(path) -> set[str]` — official MAME XML for CHD detection. |
| `src/mame_curator/parser/manufacturer.py` | `split_manufacturer("Capcom (Sega license)") -> ("Capcom", "Sega")`. |
| `src/mame_curator/cli.py` | `argparse`-based CLI with `parse` subcommand and dispatch entry point. |
| `src/mame_curator/main.py` | `main()` thin entrypoint exposed via `[project.scripts]` in `pyproject.toml`. |
| `tests/parser/__init__.py` | Test package marker. |
| `tests/parser/conftest.py` | Shared fixtures (path resolvers for `tests/parser/fixtures/`). |
| `tests/parser/fixtures/mini.dat.xml` | Hand-crafted ~6-machine DAT exercising parent/clone/bios/device/mechanical/preliminary. |
| `tests/parser/fixtures/listxml_with_disks.xml` | Hand-crafted 3-machine listxml — one with `<disk>`, two without. |
| `tests/parser/fixtures/catver.ini` | Synthetic ~10-line catver fixture. |
| `tests/parser/fixtures/languages.ini` | Synthetic ~10-line languages fixture. |
| `tests/parser/fixtures/bestgames.ini` | Synthetic ~10-line bestgames fixture (Best/Great/.../Awful). |
| `tests/parser/fixtures/mature.ini` | Synthetic ~5-line mature fixture. |
| `tests/parser/fixtures/series.ini` | Synthetic ~10-line series fixture. |
| `tests/parser/test_models.py` | `Machine` model tests. |
| `tests/parser/test_dat.py` | DAT parser tests. |
| `tests/parser/test_ini.py` | All five INI parser tests. |
| `tests/parser/test_listxml.py` | Listxml CHD-detection tests. |
| `tests/parser/test_manufacturer.py` | Manufacturer-split tests. |
| `tests/parser/test_cli_parse.py` | End-to-end test of `mame-curator parse <dat>` against the mini fixture. |

---

## Pre-flight

- [ ] **Step 0a: Verify Phase 0 is committed and green**

```bash
cd /mnt/Storage/Scripts/Linux/MAME_Curator
git log --oneline -1
uv run pytest -q
```

Expected: log shows `chore(scaffold): phase-0 tooling and CI baseline complete` as the most recent commit. Pytest shows `2 passed`. (No specific commit hash is pinned — hashes are environment-dependent.)

- [ ] **Step 0b: Verify the user's real DAT is reachable**

```bash
ls -la "/mnt/Games/MAME/MAME 0.284 ROMs (non-merged).zip"
```

Expected: file exists, size ~6 MB.

---

## Task 1: Write `parser/spec.md`

**Files:**
- Create: `src/mame_curator/parser/__init__.py` (placeholder for now; populated by later tasks)
- Create: `src/mame_curator/parser/spec.md`

The spec is the audit surface. Per coding standards §7, every feature module ships with one. We write it FIRST so the tests (next task) and implementation can be checked against it.

- [ ] **Step 1: Create the parser package directory and placeholder `__init__.py`**

```bash
mkdir -p src/mame_curator/parser
```

Then create `src/mame_curator/parser/__init__.py` with exactly:

```python
"""DAT XML and INI reference-file parsers.

Public API surface — see spec.md for the full contract.
"""
```

- [ ] **Step 2: Write `src/mame_curator/parser/spec.md`**

Write the file with exactly this content:

````markdown
# parser/ spec

## Contract

- Streams a MAME non-merged DAT XML into typed `Machine` records keyed by short name.
- Tolerates a DAT path that is either a `.xml` file or a `.zip` containing a single `.xml`.
- Parses the five progettoSnaps reference INI files: `catver.ini`, `languages.ini`, `bestgames.ini`, `mature.ini`, `series.ini`.
- Parses the official MAME `-listxml` output (separate from the Pleasuredome DAT) and returns the set of machine short names that require a CHD.
- Splits a DAT `<manufacturer>` field that encodes both publisher and developer (e.g. `"Capcom (Sega license)"`) into a `(publisher, developer)` tuple.

## Public types

### `class Machine` (frozen Pydantic model)

| Field | Type | Source |
|---|---|---|
| `name` | `str` | DAT `<machine name="...">` (the short name) |
| `description` | `str` | DAT `<description>` |
| `year` | `int \| None` | DAT `<year>` (parsed; `"????"` and unparseable → `None`) |
| `manufacturer_raw` | `str \| None` | DAT `<manufacturer>` verbatim |
| `publisher` | `str \| None` | derived via `split_manufacturer` |
| `developer` | `str \| None` | derived via `split_manufacturer` (may equal publisher when no `(... license)` suffix) |
| `cloneof` | `str \| None` | DAT attribute |
| `romof` | `str \| None` | DAT attribute |
| `is_bios` | `bool` | DAT attribute `isbios="yes"` |
| `is_device` | `bool` | DAT attribute `isdevice="yes"` |
| `is_mechanical` | `bool` | DAT attribute `ismechanical="yes"` |
| `runnable` | `bool` | DAT attribute `runnable="no"` → `False`; default `True` |
| `roms` | `tuple[Rom, ...]` | DAT `<rom>` children |
| `biossets` | `tuple[BiosSet, ...]` | DAT `<biosset>` children |
| `driver_status` | `DriverStatus \| None` | DAT `<driver status="...">`; absent → `None` |
| `sample_of` | `str \| None` | DAT attribute |

`Machine` is `frozen=True` (immutability per coding standards §3) and uses `model_config = ConfigDict(frozen=True, extra="forbid")`.

### `class Rom` (frozen)

| Field | Type |
|---|---|
| `name` | `str` |
| `size` | `int \| None` |
| `crc` | `str \| None` |
| `sha1` | `str \| None` |

### `class BiosSet` (frozen)

| Field | Type |
|---|---|
| `name` | `str` |
| `description` | `str \| None` |
| `default` | `bool` |

### `class DriverStatus` (str enum)

Values: `GOOD`, `IMPERFECT`, `PRELIMINARY`. String representation matches the DAT attribute exactly.

## Public functions

### `parse_dat(path: Path) -> dict[str, Machine]`

- Accepts `.xml` or `.zip`. For `.zip`, extracts to a temp file (single XML inside) and parses that.
- Streams via `lxml.iterparse(events=("end",), tag="machine")` — never loads the full tree.
- Calls `Element.clear()` after each `<machine>` to free memory.
- Returns a dict keyed by `Machine.name`. Two machines with the same name is a `ParserError`.
- Raises `ParserError` on malformed XML, missing root element, missing required attributes, or duplicate `name`.

### `parse_catver(path: Path) -> dict[str, str]`

- Returns `{shortname: category}`.
- Tolerates blank lines, lines starting with `;` or `#`, and section headers in `[brackets]`.

### `parse_languages(path: Path) -> dict[str, list[str]]`

- Returns `{shortname: [lang, ...]}` (multiple languages possible per machine).
- Comma-separated language values are split + stripped.

### `parse_bestgames(path: Path) -> dict[str, str]`

- Returns `{shortname: tier}` where `tier ∈ {"Best", "Great", "Good", "Average", "Bad", "Awful"}`.

### `parse_mature(path: Path) -> set[str]`

- Returns the set of shortnames listed as adult content.

### `parse_series(path: Path) -> dict[str, str]`

- Returns `{shortname: series_name}`.

### `parse_listxml_disks(path: Path) -> set[str]`

- Returns the set of machine shortnames that have at least one `<disk>` child.

### `split_manufacturer(raw: str | None) -> tuple[str | None, str | None]`

- Returns `(publisher, developer)`.
- `None` or empty input → `(None, None)`.
- `"Capcom"` → `("Capcom", "Capcom")`.
- `"Capcom (Sega license)"` → `("Capcom", "Sega")` — last `( ... license)` parenthetical is the developer.
- `"Bally / Midway"` → `("Bally / Midway", "Bally / Midway")` — slashes are kept verbatim; we do not attempt to split co-publisher cases.

## Errors

- `ParserError(Exception)` — raised on malformed input. Sub-classes: `DATError`, `INIError`, `ListxmlError`. All carry the source path and a one-sentence cause.

## Edge cases handled

- DAT `.zip` containing zero or multiple `.xml` files → `DATError` with the count.
- DAT `<year>` is `"????"` or `"19??"` → `Machine.year = None`.
- DAT `<machine>` with no `<description>` → `DATError` (description is required).
- DAT attribute combinations: `isbios + isdevice` is allowed (some entries have both); we record both.
- INI shortname appearing twice → last write wins; warn via `logger.warning`.
- INI line with no `=` separator → skipped silently (matches progettoSnaps' own tolerance).

## Out of scope

- Filtering or picking (Phase 2).
- Downloading the INI / listxml files (Phase 7's `downloads.py` primitive + Phase 8's wizard).
- Verifying that DAT short names match a known set (Phase 4 startup validation).
- Software-list routing (post-v1, see design §13).
````

- [ ] **Step 3: Run linters and commit**

```bash
uv run ruff check
uv run ruff format --check
uv run mypy
git add src/mame_curator/parser/
git commit -m "docs(parser): phase-1 spec for parser module"
```

Expected: gates pass; one new commit.

---

## Task 2: Test fixtures (synthetic DAT + INI files + listxml)

**Files:**
- Create: `tests/parser/__init__.py` (empty)
- Create: `tests/parser/conftest.py`
- Create: `tests/parser/fixtures/mini.dat.xml`
- Create: `tests/parser/fixtures/listxml_with_disks.xml`
- Create: `tests/parser/fixtures/catver.ini`
- Create: `tests/parser/fixtures/languages.ini`
- Create: `tests/parser/fixtures/bestgames.ini`
- Create: `tests/parser/fixtures/mature.ini`
- Create: `tests/parser/fixtures/series.ini`

The fixtures are deliberately small but exercise every code path: parent + clone, BIOS, device, mechanical, preliminary driver, multi-language, missing year, manufacturer with `(license)`, INI comments and section headers.

- [ ] **Step 1: Create `tests/parser/__init__.py`**

```bash
mkdir -p tests/parser/fixtures
touch tests/parser/__init__.py
```

- [ ] **Step 2: Create `tests/parser/conftest.py`**

```python
"""Shared fixtures for parser tests."""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mini_dat() -> Path:
    """Path to the 6-machine mini DAT fixture."""
    return FIXTURES / "mini.dat.xml"


@pytest.fixture
def listxml_with_disks() -> Path:
    """Path to a tiny listxml fixture with one CHD-required machine."""
    return FIXTURES / "listxml_with_disks.xml"


@pytest.fixture
def catver_ini() -> Path:
    """Path to the catver.ini fixture."""
    return FIXTURES / "catver.ini"


@pytest.fixture
def languages_ini() -> Path:
    """Path to the languages.ini fixture."""
    return FIXTURES / "languages.ini"


@pytest.fixture
def bestgames_ini() -> Path:
    """Path to the bestgames.ini fixture."""
    return FIXTURES / "bestgames.ini"


@pytest.fixture
def mature_ini() -> Path:
    """Path to the mature.ini fixture."""
    return FIXTURES / "mature.ini"


@pytest.fixture
def series_ini() -> Path:
    """Path to the series.ini fixture."""
    return FIXTURES / "series.ini"
```

- [ ] **Step 3: Create `tests/parser/fixtures/mini.dat.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<datafile>
    <header>
        <name>MAME mini fixture</name>
        <version>0.284-fixture</version>
    </header>
    <machine name="pacman">
        <description>Pac-Man (Midway)</description>
        <year>1980</year>
        <manufacturer>Namco (Midway license)</manufacturer>
        <rom name="pacman.6e" size="4096" crc="c1e6ab10" sha1="e87e059c5be45753f7e9f33dff851f16d6751181"/>
    </machine>
    <machine name="pacmanf" cloneof="pacman" romof="pacman">
        <description>Pac-Man (speedup hack)</description>
        <year>1981</year>
        <manufacturer>hack</manufacturer>
        <rom name="pacmanf.6e" size="4096" crc="aaaaaaaa" sha1="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"/>
        <driver status="imperfect"/>
    </machine>
    <machine name="neogeo" isbios="yes">
        <description>Neo-Geo</description>
        <year>1990</year>
        <manufacturer>SNK</manufacturer>
        <rom name="neo-epo.bin" size="131072" crc="11111111" sha1="0000000000000000000000000000000000000001"/>
    </machine>
    <machine name="z80" isdevice="yes" runnable="no">
        <description>Z80 CPU device</description>
        <manufacturer>Zilog</manufacturer>
    </machine>
    <machine name="3bagfull" ismechanical="yes">
        <description>3 Bags Full</description>
        <year>1996</year>
        <manufacturer>Aristocrat</manufacturer>
        <rom name="3bagfull.u86" size="32768" crc="22222222" sha1="0000000000000000000000000000000000000002"/>
    </machine>
    <machine name="brokensim">
        <description>Broken Simulation (preliminary)</description>
        <year>????</year>
        <manufacturer>Unknown</manufacturer>
        <rom name="broken.bin" size="1024" crc="33333333" sha1="0000000000000000000000000000000000000003"/>
        <driver status="preliminary"/>
    </machine>
</datafile>
```

- [ ] **Step 4: Create `tests/parser/fixtures/listxml_with_disks.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<mame build="0.284-fixture">
    <machine name="kinst">
        <description>Killer Instinct</description>
        <rom name="ki-l13.u98" size="524288" crc="65f7ea31" sha1="00000000000000000000000000000000000000ab"/>
        <disk name="kinst" sha1="00000000000000000000000000000000000000aa"/>
    </machine>
    <machine name="pacman">
        <description>Pac-Man</description>
        <rom name="pacman.6e" size="4096" crc="c1e6ab10" sha1="00000000000000000000000000000000000000ac"/>
    </machine>
    <machine name="kinst2">
        <description>Killer Instinct 2</description>
        <disk name="kinst2" sha1="00000000000000000000000000000000000000ad"/>
    </machine>
</mame>
```

- [ ] **Step 5: Create `tests/parser/fixtures/catver.ini`**

```ini
; comment line — should be ignored
[Category]
pacman=Maze / Collect
pacmanf=Maze / Collect
neogeo=System / Neo-Geo
3bagfull=Casino / Slot Machine
brokensim=Misc.
```

- [ ] **Step 6: Create `tests/parser/fixtures/languages.ini`**

```ini
[Languages]
pacman=English
brokensim=Japanese
mahjongx=Japanese, English
```

(`mahjongx` is intentionally not in the DAT fixture — exercises "INI mentions a machine the DAT doesn't have", which is a legitimate runtime case once we ship.)

- [ ] **Step 7: Create `tests/parser/fixtures/bestgames.ini`**

```ini
[Best]
pacman=

[Great]
neogeo=

[Good]
3bagfull=

[Average]
brokensim=
```

(progettoSnaps' bestgames format uses `[Tier]` section headers with shortname keys.)

- [ ] **Step 8: Create `tests/parser/fixtures/mature.ini`**

```ini
[ROOT_FOLDER]

[Mature]
brokensim=
```

- [ ] **Step 9: Create `tests/parser/fixtures/series.ini`**

```ini
[Pac-Man]
pacman=
pacmanf=

[Neo-Geo]
neogeo=
```

- [ ] **Step 10: Commit fixtures**

```bash
git add tests/parser/
git commit -m "test(parser): synthetic fixtures for DAT, listxml, and 5 ini files"
```

---

## Task 3: `Machine` model + `split_manufacturer` utility

**Files:**
- Create: `src/mame_curator/parser/manufacturer.py`
- Create: `src/mame_curator/parser/models.py`
- Create: `tests/parser/test_manufacturer.py`
- Create: `tests/parser/test_models.py`

- [ ] **Step 1: Write `tests/parser/test_manufacturer.py` (failing)**

```python
"""Tests for split_manufacturer."""

import pytest

from mame_curator.parser.manufacturer import split_manufacturer


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, (None, None)),
        ("", (None, None)),
        ("   ", (None, None)),
        ("Capcom", ("Capcom", "Capcom")),
        ("Capcom (Sega license)", ("Capcom", "Sega")),
        ("Konami (Sun Electronics license)", ("Konami", "Sun Electronics")),
        ("Bally / Midway", ("Bally / Midway", "Bally / Midway")),
        ("Atari (no license info)", ("Atari (no license info)", "Atari (no license info)")),
        # licence (UK spelling) is NOT recognized — only the US spelling
    ],
)
def test_split_manufacturer(raw: str | None, expected: tuple[str | None, str | None]) -> None:
    assert split_manufacturer(raw) == expected
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/parser/test_manufacturer.py -v
```

Expected: ImportError / ModuleNotFoundError.

- [ ] **Step 3: Implement `src/mame_curator/parser/manufacturer.py`**

```python
"""Split a MAME `<manufacturer>` field into (publisher, developer)."""

from __future__ import annotations

import re

# Matches "... ( ... license)" — only the US spelling, only when "license" is the LAST
# word inside the trailing parenthetical, and we keep the publisher = everything before.
_LICENSE_RE = re.compile(r"^\s*(?P<publisher>.+?)\s*\((?P<developer>.+?)\s+license\)\s*$")


def split_manufacturer(raw: str | None) -> tuple[str | None, str | None]:
    """Split a manufacturer field into (publisher, developer).

    `"Capcom (Sega license)"` -> `("Capcom", "Sega")`.
    `"Capcom"` -> `("Capcom", "Capcom")`.
    `None` / empty / whitespace -> `(None, None)`.
    """
    if raw is None:
        return (None, None)
    cleaned = raw.strip()
    if not cleaned:
        return (None, None)
    match = _LICENSE_RE.match(cleaned)
    if match is None:
        return (cleaned, cleaned)
    return (match.group("publisher").strip(), match.group("developer").strip())
```

- [ ] **Step 4: Run, expect pass**

```bash
uv run pytest tests/parser/test_manufacturer.py -v
```

Expected: all parametrized cases pass.

- [ ] **Step 5: Write `tests/parser/test_models.py` (failing)**

```python
"""Tests for the Machine model."""

import pytest
from pydantic import ValidationError

from mame_curator.parser.models import BiosSet, DriverStatus, Machine, Rom


def test_minimal_machine_constructs() -> None:
    m = Machine(name="pacman", description="Pac-Man (Midway)")
    assert m.name == "pacman"
    assert m.description == "Pac-Man (Midway)"
    assert m.year is None
    assert m.is_bios is False
    assert m.is_device is False
    assert m.is_mechanical is False
    assert m.runnable is True
    assert m.roms == ()
    assert m.biossets == ()
    assert m.driver_status is None


def test_full_machine_constructs() -> None:
    m = Machine(
        name="kinst",
        description="Killer Instinct",
        year=1994,
        manufacturer_raw="Rare / Nintendo (Midway license)",
        publisher="Rare / Nintendo",
        developer="Midway",
        cloneof=None,
        romof=None,
        is_bios=False,
        is_device=False,
        is_mechanical=False,
        runnable=True,
        roms=(Rom(name="ki.u98", size=524288, crc="65f7ea31", sha1="abc"),),
        biossets=(BiosSet(name="default", description="Default", default=True),),
        driver_status=DriverStatus.GOOD,
        sample_of=None,
    )
    assert m.driver_status is DriverStatus.GOOD
    assert m.roms[0].crc == "65f7ea31"
    assert m.biossets[0].default is True


def test_machine_is_frozen() -> None:
    m = Machine(name="pacman", description="Pac-Man")
    with pytest.raises(ValidationError):
        m.name = "other"  # type: ignore[misc]


def test_machine_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Machine(name="x", description="y", bogus_field=True)  # type: ignore[call-arg]


def test_driver_status_values() -> None:
    assert DriverStatus.GOOD.value == "good"
    assert DriverStatus.IMPERFECT.value == "imperfect"
    assert DriverStatus.PRELIMINARY.value == "preliminary"
```

- [ ] **Step 6: Run, expect failure**

```bash
uv run pytest tests/parser/test_models.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 7: Implement `src/mame_curator/parser/models.py`**

```python
"""Typed Pydantic models for parsed MAME data."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class DriverStatus(str, Enum):
    """MAME driver emulation status."""

    GOOD = "good"
    IMPERFECT = "imperfect"
    PRELIMINARY = "preliminary"


class Rom(BaseModel):
    """A single ROM entry within a machine."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    size: int | None = None
    crc: str | None = None
    sha1: str | None = None


class BiosSet(BaseModel):
    """A `<biosset>` declaration within a machine."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str | None = None
    default: bool = False


class Machine(BaseModel):
    """A parsed MAME machine record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str
    year: int | None = None
    manufacturer_raw: str | None = None
    publisher: str | None = None
    developer: str | None = None
    cloneof: str | None = None
    romof: str | None = None
    is_bios: bool = False
    is_device: bool = False
    is_mechanical: bool = False
    runnable: bool = True
    roms: tuple[Rom, ...] = ()
    biossets: tuple[BiosSet, ...] = ()
    driver_status: DriverStatus | None = None
    sample_of: str | None = None
```

- [ ] **Step 8: Run, expect pass**

```bash
uv run pytest tests/parser/test_models.py tests/parser/test_manufacturer.py -v
```

Expected: all green.

- [ ] **Step 9: Lint + types**

```bash
uv run ruff check
uv run ruff format
uv run mypy
```

Expected: clean. (`ruff format` may rewrite the new files into canonical form — that's fine.)

- [ ] **Step 10: Commit**

```bash
git add src/mame_curator/parser/manufacturer.py src/mame_curator/parser/models.py tests/parser/test_manufacturer.py tests/parser/test_models.py
git commit -m "feat(parser): Machine model and manufacturer split"
```

---

## Task 4: DAT parser (`parse_dat`)

**Files:**
- Create: `src/mame_curator/parser/errors.py`
- Create: `src/mame_curator/parser/dat.py`
- Create: `tests/parser/test_dat.py`
- Modify: `src/mame_curator/parser/__init__.py` (add re-export)

- [ ] **Step 1: Write `tests/parser/test_dat.py` (failing)**

```python
"""Tests for parse_dat."""

import zipfile
from pathlib import Path

import pytest

from mame_curator.parser.dat import parse_dat
from mame_curator.parser.errors import DATError
from mame_curator.parser.models import DriverStatus


def test_parse_dat_returns_dict_keyed_by_short_name(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert set(machines.keys()) == {
        "pacman", "pacmanf", "neogeo", "z80", "3bagfull", "brokensim"
    }


def test_parent_clone_relationship_populated(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert machines["pacman"].cloneof is None
    assert machines["pacmanf"].cloneof == "pacman"
    assert machines["pacmanf"].romof == "pacman"


def test_bios_device_mechanical_flags(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert machines["neogeo"].is_bios is True
    assert machines["z80"].is_device is True
    assert machines["z80"].runnable is False
    assert machines["3bagfull"].is_mechanical is True


def test_unparseable_year_becomes_none(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert machines["brokensim"].year is None
    assert machines["pacman"].year == 1980


def test_manufacturer_split(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert machines["pacman"].publisher == "Namco"
    assert machines["pacman"].developer == "Midway"
    assert machines["neogeo"].publisher == "SNK"
    assert machines["neogeo"].developer == "SNK"


def test_driver_status_parsed(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    assert machines["pacman"].driver_status is None  # absent in fixture
    assert machines["pacmanf"].driver_status is DriverStatus.IMPERFECT
    assert machines["brokensim"].driver_status is DriverStatus.PRELIMINARY


def test_roms_attached_to_machine(mini_dat: Path) -> None:
    machines = parse_dat(mini_dat)
    pacman_roms = machines["pacman"].roms
    assert len(pacman_roms) == 1
    assert pacman_roms[0].name == "pacman.6e"
    assert pacman_roms[0].size == 4096
    assert pacman_roms[0].crc == "c1e6ab10"


def test_parse_dat_handles_zip_wrapper(mini_dat: Path, tmp_path: Path) -> None:
    zipped = tmp_path / "wrapped.zip"
    with zipfile.ZipFile(zipped, "w") as zf:
        zf.write(mini_dat, arcname="mini.dat.xml")
    machines = parse_dat(zipped)
    assert "pacman" in machines


def test_zip_with_no_xml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "empty.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("notxml.txt", "hello")
    with pytest.raises(DATError, match="zero"):
        parse_dat(bad)


def test_zip_with_multiple_xmls_raises(tmp_path: Path, mini_dat: Path) -> None:
    bad = tmp_path / "two.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.write(mini_dat, arcname="a.xml")
        zf.write(mini_dat, arcname="b.xml")
    with pytest.raises(DATError, match="multiple"):
        parse_dat(bad)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(DATError, match="not exist"):
        parse_dat(tmp_path / "nope.xml")


def test_malformed_xml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_text("<datafile><machine name='x'><description>y")
    with pytest.raises(DATError):
        parse_dat(bad)
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/parser/test_dat.py -v
```

Expected: ModuleNotFoundError on `parse_dat`.

- [ ] **Step 3: Create `src/mame_curator/parser/errors.py`**

```python
"""Typed parser exceptions. Each carries the source path."""

from __future__ import annotations

from pathlib import Path


class ParserError(Exception):
    """Base for all parser-related errors."""

    def __init__(self, message: str, path: Path | None = None) -> None:
        self.path = path
        super().__init__(f"{message} (path={path})" if path else message)


class DATError(ParserError):
    """Malformed DAT XML or unsupported wrapper."""


class INIError(ParserError):
    """Malformed INI file."""


class ListxmlError(ParserError):
    """Malformed `mame -listxml` output."""
```

- [ ] **Step 4: Implement `src/mame_curator/parser/dat.py`**

```python
"""Stream a MAME non-merged DAT XML into Machine records.

Uses lxml.iterparse so the 48 MB XML never lives in memory in full.
Each <machine> element is processed and then cleared.
"""

from __future__ import annotations

import logging
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from lxml import etree

from mame_curator.parser.errors import DATError
from mame_curator.parser.manufacturer import split_manufacturer
from mame_curator.parser.models import BiosSet, DriverStatus, Machine, Rom

logger = logging.getLogger(__name__)


def parse_dat(path: Path) -> dict[str, Machine]:
    """Parse a MAME non-merged DAT XML into a dict of Machine records.

    Accepts either a `.xml` file or a `.zip` containing a single `.xml`.
    """
    if not path.exists():
        raise DATError("DAT path does not exist", path=path)

    with _resolve_xml(path) as xml_path:
        return _stream_machines(xml_path)


@contextmanager
def _resolve_xml(path: Path) -> Iterator[Path]:
    """Yield a Path to the actual XML, extracting from .zip if needed."""
    if path.suffix.lower() != ".zip":
        yield path
        return
    with zipfile.ZipFile(path) as zf:
        xml_members = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if len(xml_members) == 0:
            raise DATError("DAT zip contains zero .xml files", path=path)
        if len(xml_members) > 1:
            raise DATError(f"DAT zip contains multiple .xml files: {xml_members}", path=path)
        with tempfile.TemporaryDirectory() as tmp:
            extracted = zf.extract(xml_members[0], path=tmp)
            yield Path(extracted)


def _stream_machines(xml_path: Path) -> dict[str, Machine]:
    machines: dict[str, Machine] = {}
    try:
        for _event, elem in etree.iterparse(
            str(xml_path), events=("end",), tag="machine"
        ):
            machine = _machine_from_element(elem)
            if machine.name in machines:
                raise DATError(f"duplicate machine name: {machine.name}", path=xml_path)
            machines[machine.name] = machine
            elem.clear()
    except etree.XMLSyntaxError as exc:
        raise DATError(f"XML parse failed: {exc}", path=xml_path) from exc
    return machines


def _machine_from_element(elem: Any) -> Machine:
    name = elem.get("name")
    if not name:
        raise DATError("machine element missing required 'name' attribute")
    description_elem = elem.find("description")
    if description_elem is None or not description_elem.text:
        raise DATError(f"machine '{name}' missing required <description>")

    raw_manufacturer = _text(elem, "manufacturer")
    publisher, developer = split_manufacturer(raw_manufacturer)

    return Machine(
        name=name,
        description=description_elem.text,
        year=_year_or_none(_text(elem, "year")),
        manufacturer_raw=raw_manufacturer,
        publisher=publisher,
        developer=developer,
        cloneof=elem.get("cloneof"),
        romof=elem.get("romof"),
        is_bios=elem.get("isbios") == "yes",
        is_device=elem.get("isdevice") == "yes",
        is_mechanical=elem.get("ismechanical") == "yes",
        runnable=elem.get("runnable") != "no",
        roms=tuple(_rom_from_element(r) for r in elem.findall("rom")),
        biossets=tuple(_biosset_from_element(b) for b in elem.findall("biosset")),
        driver_status=_driver_status_from_element(elem.find("driver")),
        sample_of=elem.get("sampleof"),
    )


def _text(elem: Any, child: str) -> str | None:
    found = elem.find(child)
    if found is None or not found.text:
        return None
    return str(found.text)


def _year_or_none(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _rom_from_element(elem: Any) -> Rom:
    return Rom(
        name=elem.get("name", ""),
        size=int(elem.get("size")) if elem.get("size") else None,
        crc=elem.get("crc"),
        sha1=elem.get("sha1"),
    )


def _biosset_from_element(elem: Any) -> BiosSet:
    return BiosSet(
        name=elem.get("name", ""),
        description=elem.get("description"),
        default=elem.get("default") == "yes",
    )


def _driver_status_from_element(elem: Any) -> DriverStatus | None:
    if elem is None:
        return None
    status = elem.get("status")
    if status is None:
        return None
    try:
        return DriverStatus(status)
    except ValueError:
        logger.warning("unknown driver status: %s", status)
        return None
```

- [ ] **Step 5: Update `src/mame_curator/parser/__init__.py` to re-export**

```python
"""DAT XML and INI reference-file parsers.

Public API surface — see spec.md for the full contract.
"""

from mame_curator.parser.dat import parse_dat
from mame_curator.parser.errors import DATError, INIError, ListxmlError, ParserError
from mame_curator.parser.manufacturer import split_manufacturer
from mame_curator.parser.models import BiosSet, DriverStatus, Machine, Rom

__all__ = [
    "BiosSet",
    "DATError",
    "DriverStatus",
    "INIError",
    "ListxmlError",
    "Machine",
    "ParserError",
    "Rom",
    "parse_dat",
    "split_manufacturer",
]
```

- [ ] **Step 6: Run all parser tests**

```bash
uv run pytest tests/parser/ -v
```

Expected: all pass (manufacturer + models + dat).

- [ ] **Step 7: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/parser/ tests/parser/test_dat.py
git commit -m "feat(parser): streaming DAT parser via lxml.iterparse"
```

---

## Task 5: INI parsers (`catver`, `languages`, `bestgames`, `mature`, `series`)

**Files:**
- Create: `src/mame_curator/parser/ini.py`
- Create: `tests/parser/test_ini.py`
- Modify: `src/mame_curator/parser/__init__.py` (add re-exports)

The five files share a common shape: section headers + `key=value` pairs + comments. We extract `_parse_simple_ini()` once and compose the five public functions on top.

- [ ] **Step 1: Write `tests/parser/test_ini.py`**

```python
"""Tests for INI parsers."""

from pathlib import Path

import pytest

from mame_curator.parser.errors import INIError
from mame_curator.parser.ini import (
    parse_bestgames,
    parse_catver,
    parse_languages,
    parse_mature,
    parse_series,
)


def test_parse_catver(catver_ini: Path) -> None:
    cats = parse_catver(catver_ini)
    assert cats["pacman"] == "Maze / Collect"
    assert cats["3bagfull"] == "Casino / Slot Machine"
    assert "neogeo" in cats


def test_parse_catver_skips_comments_and_section_headers(catver_ini: Path) -> None:
    cats = parse_catver(catver_ini)
    # neither the leading comment nor [Category] should appear as a key
    assert ";" not in "".join(cats.keys())
    assert "[Category]" not in cats


def test_parse_languages_multivalue(languages_ini: Path) -> None:
    langs = parse_languages(languages_ini)
    assert langs["pacman"] == ["English"]
    assert langs["mahjongx"] == ["Japanese", "English"]


def test_parse_languages_includes_machines_not_in_dat(languages_ini: Path) -> None:
    langs = parse_languages(languages_ini)
    # mahjongx isn't in our DAT fixture; that's fine — INI is independent
    assert "mahjongx" in langs


def test_parse_bestgames_tier_per_machine(bestgames_ini: Path) -> None:
    tiers = parse_bestgames(bestgames_ini)
    assert tiers["pacman"] == "Best"
    assert tiers["neogeo"] == "Great"
    assert tiers["3bagfull"] == "Good"
    assert tiers["brokensim"] == "Average"


def test_parse_mature_returns_set(mature_ini: Path) -> None:
    mature = parse_mature(mature_ini)
    assert mature == {"brokensim"}


def test_parse_series(series_ini: Path) -> None:
    series = parse_series(series_ini)
    assert series["pacman"] == "Pac-Man"
    assert series["pacmanf"] == "Pac-Man"
    assert series["neogeo"] == "Neo-Geo"


def test_parse_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(INIError, match="not exist"):
        parse_catver(tmp_path / "nope.ini")


def test_parse_handles_blank_lines(tmp_path: Path) -> None:
    f = tmp_path / "blank.ini"
    f.write_text("[Cat]\n\n\npacman=Maze\n\n")
    assert parse_catver(f) == {"pacman": "Maze"}
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/parser/test_ini.py -v
```

Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `src/mame_curator/parser/ini.py`**

```python
"""Parsers for the five progettoSnaps reference INI files.

All five share section + key=value structure with `;` or `#` comments.
A shared `_parse_simple_ini` walker emits (section, key, value) triples;
each public parser interprets them differently.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

from mame_curator.parser.errors import INIError

logger = logging.getLogger(__name__)


def parse_catver(path: Path) -> dict[str, str]:
    """Return {shortname: category} from progettoSnaps catver.ini.

    Section headers are ignored; only `name=value` lines are kept.
    """
    return {key: value for _section, key, value in _parse_simple_ini(path)}


def parse_languages(path: Path) -> dict[str, list[str]]:
    """Return {shortname: [lang, ...]} from languages.ini.

    Comma-separated values are split and stripped.
    """
    out: dict[str, list[str]] = {}
    for _section, key, value in _parse_simple_ini(path):
        out[key] = [part.strip() for part in value.split(",") if part.strip()]
    return out


def parse_bestgames(path: Path) -> dict[str, str]:
    """Return {shortname: tier} from bestgames.ini.

    The bestgames format uses tier *sections* (`[Best]`, `[Great]`, ...) with
    shortname keys whose values are empty. We map each shortname to its section.
    """
    valid_tiers = {"Best", "Great", "Good", "Average", "Bad", "Awful"}
    out: dict[str, str] = {}
    for section, key, _value in _parse_simple_ini(path):
        if section in valid_tiers:
            out[key] = section
    return out


def parse_mature(path: Path) -> set[str]:
    """Return the set of shortnames listed under [Mature]."""
    return {key for section, key, _v in _parse_simple_ini(path) if section == "Mature"}


def parse_series(path: Path) -> dict[str, str]:
    """Return {shortname: series_name} from series.ini.

    Each section header is the series name; the keys are member shortnames.
    """
    out: dict[str, str] = {}
    for section, key, _v in _parse_simple_ini(path):
        if section:
            out[key] = section
    return out


def _parse_simple_ini(path: Path) -> Iterator[tuple[str, str, str]]:
    """Yield (section, key, value) for every `key=value` line.

    Section is "" when no header has been seen. Comments (`;`, `#`) and
    blank lines are skipped. Lines without `=` are skipped silently.
    """
    if not path.exists():
        raise INIError("INI path does not exist", path=path)
    section = ""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith((";", "#")):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1].strip()
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if not key:
                    continue
                yield (section, key, value)
    except OSError as exc:
        raise INIError(f"failed to read INI: {exc}", path=path) from exc
```

- [ ] **Step 4: Update `src/mame_curator/parser/__init__.py` to add INI re-exports**

Replace its content with:

```python
"""DAT XML and INI reference-file parsers.

Public API surface — see spec.md for the full contract.
"""

from mame_curator.parser.dat import parse_dat
from mame_curator.parser.errors import DATError, INIError, ListxmlError, ParserError
from mame_curator.parser.ini import (
    parse_bestgames,
    parse_catver,
    parse_languages,
    parse_mature,
    parse_series,
)
from mame_curator.parser.manufacturer import split_manufacturer
from mame_curator.parser.models import BiosSet, DriverStatus, Machine, Rom

__all__ = [
    "BiosSet",
    "DATError",
    "DriverStatus",
    "INIError",
    "ListxmlError",
    "Machine",
    "ParserError",
    "Rom",
    "parse_bestgames",
    "parse_catver",
    "parse_dat",
    "parse_languages",
    "parse_mature",
    "parse_series",
    "split_manufacturer",
]
```

- [ ] **Step 5: Run, expect pass**

```bash
uv run pytest tests/parser/ -v
```

Expected: all parser tests pass.

- [ ] **Step 6: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/parser/ini.py src/mame_curator/parser/__init__.py tests/parser/test_ini.py
git commit -m "feat(parser): five INI parsers via shared simple-INI walker"
```

---

## Task 6: Listxml CHD detector (`parse_listxml_disks`)

**Files:**
- Create: `src/mame_curator/parser/listxml.py`
- Create: `tests/parser/test_listxml.py`
- Modify: `src/mame_curator/parser/__init__.py` (add re-export)

- [ ] **Step 1: Write `tests/parser/test_listxml.py`**

```python
"""Tests for parse_listxml_disks."""

from pathlib import Path

import pytest

from mame_curator.parser.errors import ListxmlError
from mame_curator.parser.listxml import parse_listxml_disks


def test_returns_machines_with_disk_elements(listxml_with_disks: Path) -> None:
    chd_required = parse_listxml_disks(listxml_with_disks)
    assert chd_required == {"kinst", "kinst2"}


def test_machines_without_disk_excluded(listxml_with_disks: Path) -> None:
    chd_required = parse_listxml_disks(listxml_with_disks)
    assert "pacman" not in chd_required


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ListxmlError, match="not exist"):
        parse_listxml_disks(tmp_path / "nope.xml")


def test_malformed_xml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_text("<mame><machine name='x'>")
    with pytest.raises(ListxmlError):
        parse_listxml_disks(bad)
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/parser/test_listxml.py -v
```

- [ ] **Step 3: Implement `src/mame_curator/parser/listxml.py`**

```python
"""CHD detection from MAME's official `-listxml` output.

The Pleasuredome ROM-set DAT does not include <disk> entries; this module
reads the official MAME XML to identify which machines require a CHD.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from mame_curator.parser.errors import ListxmlError


def parse_listxml_disks(path: Path) -> set[str]:
    """Return the set of machine shortnames that have at least one <disk> child."""
    if not path.exists():
        raise ListxmlError("listxml path does not exist", path=path)

    chd_required: set[str] = set()
    try:
        for _event, elem in etree.iterparse(str(path), events=("end",), tag="machine"):
            if elem.find("disk") is not None:
                name = elem.get("name")
                if name:
                    chd_required.add(name)
            elem.clear()
    except etree.XMLSyntaxError as exc:
        raise ListxmlError(f"XML parse failed: {exc}", path=path) from exc
    return chd_required
```

- [ ] **Step 4: Update `__init__.py` to re-export `parse_listxml_disks`**

Replace `src/mame_curator/parser/__init__.py` in full with:

```python
"""DAT XML and INI reference-file parsers.

Public API surface — see spec.md for the full contract.
"""

from mame_curator.parser.dat import parse_dat
from mame_curator.parser.errors import DATError, INIError, ListxmlError, ParserError
from mame_curator.parser.ini import (
    parse_bestgames,
    parse_catver,
    parse_languages,
    parse_mature,
    parse_series,
)
from mame_curator.parser.listxml import parse_listxml_disks
from mame_curator.parser.manufacturer import split_manufacturer
from mame_curator.parser.models import BiosSet, DriverStatus, Machine, Rom

__all__ = [
    "BiosSet",
    "DATError",
    "DriverStatus",
    "INIError",
    "ListxmlError",
    "Machine",
    "ParserError",
    "Rom",
    "parse_bestgames",
    "parse_catver",
    "parse_dat",
    "parse_languages",
    "parse_listxml_disks",
    "parse_mature",
    "parse_series",
    "split_manufacturer",
]
```

(A literal find-and-replace on a single import line would produce duplicate imports — so we rewrite the file in full instead.)

- [ ] **Step 5: Run, expect pass**

```bash
uv run pytest tests/parser/ -v
```

- [ ] **Step 6: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/parser/listxml.py src/mame_curator/parser/__init__.py tests/parser/test_listxml.py
git commit -m "feat(parser): listxml CHD detector"
```

---

## Task 7: CLI `mame-curator parse <dat-path>`

**Files:**
- Create: `src/mame_curator/main.py`
- Create: `src/mame_curator/cli.py`
- Create: `tests/parser/test_cli_parse.py`

The CLI uses `argparse` (stdlib — no extra dep) with subcommands. Phase 2 will add `filter`; Phase 3 will add `copy`.

- [ ] **Step 1: Write `tests/parser/test_cli_parse.py`**

```python
"""End-to-end test for `mame-curator parse <dat>`."""

from pathlib import Path

from mame_curator.cli import build_parser, run


def test_parse_command_prints_summary(mini_dat: Path, capsys: object) -> None:
    parser = build_parser()
    args = parser.parse_args(["parse", str(mini_dat)])
    exit_code = run(args)
    assert exit_code == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    output = captured.out
    assert "machines: 6" in output
    assert "parents: 5" in output
    assert "clones: 1" in output
    assert "bios:" in output
    assert "devices:" in output
    assert "mechanical:" in output


def test_parse_command_unknown_path_returns_nonzero(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(["parse", str(tmp_path / "nope.xml")])
    exit_code = run(args)
    assert exit_code != 0
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/parser/test_cli_parse.py -v
```

- [ ] **Step 3: Implement `src/mame_curator/cli.py`**

```python
"""mame-curator command-line interface.

Subcommands (added incrementally as phases land):
    parse <dat-path>   — parse the DAT and print summary stats (Phase 1)
    filter <config>    — Phase 2
    copy ...           — Phase 3
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console

from mame_curator.parser import ParserError, parse_dat

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser with all subcommands."""
    parser = argparse.ArgumentParser(prog="mame-curator", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser("parse", help="Parse a DAT and print summary stats")
    parse_cmd.add_argument("dat", type=Path, help="Path to DAT XML or .zip")

    return parser


def run(args: argparse.Namespace) -> int:
    """Dispatch to the chosen subcommand. Returns process exit code."""
    if args.command == "parse":
        return _cmd_parse(args)
    return 1  # unreachable: argparse `required=True` enforces a subcommand


def _cmd_parse(args: argparse.Namespace) -> int:
    console = Console()
    try:
        machines = parse_dat(args.dat)
    except ParserError as exc:
        console.print(f"[red]error:[/red] {exc}")
        return 2

    parents = sum(1 for m in machines.values() if m.cloneof is None)
    clones = sum(1 for m in machines.values() if m.cloneof is not None)
    bios = sum(1 for m in machines.values() if m.is_bios)
    devices = sum(1 for m in machines.values() if m.is_device)
    mechanical = sum(1 for m in machines.values() if m.is_mechanical)

    console.print(f"DAT: {args.dat}")
    console.print(f"  machines: {len(machines)}")
    console.print(f"  parents: {parents}")
    console.print(f"  clones: {clones}")
    console.print(f"  bios: {bios}")
    console.print(f"  devices: {devices}")
    console.print(f"  mechanical: {mechanical}")
    return 0
```

- [ ] **Step 4: Implement `src/mame_curator/main.py`**

```python
"""Entrypoint for the `mame-curator` script (per pyproject.toml [project.scripts])."""

from __future__ import annotations

import logging
import sys

from mame_curator.cli import build_parser, run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> int:
    """CLI entry: parses argv and dispatches."""
    parser = build_parser()
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run, expect pass**

```bash
uv run pytest tests/parser/ -v
```

Expected: all parser tests including the CLI test pass.

- [ ] **Step 6: Manually try the CLI on the fixture**

```bash
uv run mame-curator parse tests/parser/fixtures/mini.dat.xml
```

Expected output (rich-formatted):

```
DAT: tests/parser/fixtures/mini.dat.xml
  machines: 6
  parents: 5
  clones: 1
  bios: 1
  devices: 1
  mechanical: 1
```

- [ ] **Step 7: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/cli.py src/mame_curator/main.py tests/parser/test_cli_parse.py
git commit -m "feat(cli): mame-curator parse subcommand prints summary stats"
```

---

## Task 8: Smoke run against the user's real DAT

**Files:** none modified — verification only.

This is the live "does it actually work on 43,579 machines in <30 s?" test. We are NOT modifying any code in this task; we are confirming the implementation scales.

- [ ] **Step 1: Time the parse on the real DAT**

```bash
cd /mnt/Storage/Scripts/Linux/MAME_Curator
time uv run mame-curator parse "/mnt/Games/MAME/MAME 0.284 ROMs (non-merged).zip"
```

Expected:
- `machines: ~43,579` (Pleasuredome 0.284 set)
- `parents` + `clones` ≈ `machines` (every record is one or the other)
- `bios:` is roughly 30-100 (BIOS-only entries)
- `devices:` is in the thousands (lots of sub-device emulator entries)
- `mechanical:` is in the hundreds
- Real time: under 30 seconds on any reasonable machine (the user's box should do it in a few seconds).

- [ ] **Step 2: Sanity-check the numbers**

If `machines` is 0, the iterparse tag may not have matched. If a `DATError` fires on a duplicate name, that means the Pleasuredome DAT has dupes — investigate which and reconsider whether to keep the strict-mode check.

- [ ] **Step 3: Record the observed numbers in the commit message of Task 9**

Note them for Task 9's commit body.

---

## Task 9: Coverage check + final phase commit

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run the full suite with coverage and confirm parser/ ≥ 90%**

```bash
uv run pytest --cov=mame_curator.parser --cov-report=term-missing tests/parser/ -v
```

Expected: every test passes, and the `Cover` column for files under `src/mame_curator/parser/` is ≥ 90%. The `Missing` column should be empty or near-empty.

If a file falls short, write the missing test(s) before continuing. Common shortfalls:
- An exception branch with no test — add one using `pytest.raises`.
- A "no driver element" branch in `_driver_status_from_element` — add a fixture machine with no `<driver>`.

- [ ] **Step 2: Run the full project suite (regression check)**

```bash
uv run pytest -v
```

Expected: every test passes (parser tests + the Phase 0 smoke tests).

- [ ] **Step 3: Run all gates**

```bash
uv run ruff check
uv run ruff format --check
uv run mypy
uv run bandit -c pyproject.toml -r src
uv run pre-commit run --all-files
```

Expected: every gate green.

- [ ] **Step 4: Confirm no public function exceeds 50 lines**

```bash
awk '/^def / {name=$2; start=NR} /^[a-zA-Z_]/ && name && NR>start+50 {print FILENAME":"start" "name" exceeds 50 lines"; name=""}' src/mame_curator/parser/*.py src/mame_curator/cli.py
```

Expected: no output (every public function fits).

If any function is too long, split it before continuing.

- [ ] **Step 5: Update `CHANGELOG.md`**

Edit the `[Unreleased] / Added` section to add:

```markdown
- **Phase 1 complete** — DAT and INI parsers (`parser/`):
  - Streaming DAT parser (`lxml.iterparse`) tolerant of `.xml` or `.zip` input.
  - Five INI parsers (catver / languages / bestgames / mature / series) sharing a single small walker.
  - CHD detector via official MAME `-listxml`.
  - `Machine` Pydantic model (frozen, validated) with `Rom`, `BiosSet`, and `DriverStatus`.
  - Manufacturer split for `"Foo (Bar license)"` → `(publisher, developer)`.
  - CLI subcommand `mame-curator parse <dat>` prints summary stats; runs against the real 43,579-machine DAT in well under 30 s.
```

- [ ] **Step 6: Final phase commit**

```bash
git add CHANGELOG.md
git commit -m "$(cat <<'EOF'
chore(parser): phase-1 DAT and INI parsers complete

Smoke run against the user's real MAME 0.284 (non-merged) DAT:
- machines parsed: <fill in observed number>
- parents/clones/bios/devices/mechanical: <fill in>
- elapsed: <fill in> seconds (< 30 s acceptance gate)

Coverage on src/mame_curator/parser/ ≥ 90%.
Every public function ≤ 50 lines.
All gates green: ruff, ruff format, mypy, bandit, pytest, pre-commit.
EOF
)"
```

Replace the `<fill in ...>` placeholders with the actual numbers from Task 8.

- [ ] **Step 7: Verify the commit landed**

```bash
git log --oneline -10
```

---

## Phase 1 Acceptance — final checklist

Re-confirm each item from the roadmap:

- [ ] Every test in this plan passes (`uv run pytest tests/parser/`).
- [ ] `src/mame_curator/parser/spec.md` matches the implementation (no public symbol in code that's not in spec; no spec contract that's not in code).
- [ ] Coverage on `parser/` ≥ 90%.
- [ ] CLI smoke run on user's real DAT completes in < 30 s and prints sane numbers (~43,579 machines).
- [ ] No public function exceeds 50 lines.
- [ ] All Phase 0 acceptance gates still pass.

If every box is ticked, **stop here.** Per roadmap anti-jump rule #1, do not start Phase 2 until the user confirms Phase 1 is complete.

## Per-phase review questions to ask the user

1. Did the smoke-run summary numbers look sane against the user's real DAT?
2. Spot-check: open one parsed Machine record (e.g. via `uv run python -c "from mame_curator.parser import parse_dat; print(parse_dat(<path>)['kinst'])"`) — does it match what the design spec describes?
3. Anything to refine before Phase 2 (filter)? E.g., a manufacturer string variant we missed.
