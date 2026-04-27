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
- DAT containing zero `<machine>` elements (valid XML but wrong root, or genuinely empty) → `DATError("DAT contained no <machine> elements")`. Without this, the user gets a confusing silent `{}` instead of a clear "wrong file?" signal.
- DAT attribute combinations: `isbios + isdevice` is allowed (some entries have both); we record both.
- **Pleasuredome DATs strip `cloneof` and `romof`.** Verified empirically: both the merged and non-merged Pleasuredome 0.284 DATs contain zero `cloneof=` / `romof=` attributes. As a consequence, parsing the Pleasuredome DAT alone yields `cloneof=None` for every machine. Parent/clone relationships come from the official MAME `-listxml` (downloaded separately for CHD detection — see §6.7 update channel) and are joined onto Pleasuredome machines by short name in Phase 2's filter. The parser itself is faithful to the DAT and does not synthesize relationships.
- INI shortname appearing twice → last write wins; warn via `logger.warning`.
- INI line with no `=` separator → skipped silently (matches progettoSnaps' own tolerance).

## Out of scope

- Filtering or picking — handled by `filter/`.
- Downloading the INI / listxml files — handled by the shared `downloads.py` primitive (introduced with `updates/`) and the wizard (`setup/`).
- Acquiring the official MAME `-listxml` itself — the parser consumes it once it's on disk; how it got there is the wizard's problem (see design §6.1 "Where `-listxml` comes from").
- Verifying that DAT short names match a known set — handled by API startup validation.
- Software-list routing (post-v1, see design §13).
