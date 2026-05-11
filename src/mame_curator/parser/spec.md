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
| `year` | `int \| None` | DAT `<year>` (parsed; `"????"`, unparseable, and out-of-range values → `None`; see "Edge cases handled") |
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

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | non-empty (`min_length=1`); a `<rom>` with missing or empty `name` is corruption → `DATError` |
| `size` | `int \| None` | non-negative (`ge=0`); negative sizes are nonsense and rejected by the model |
| `crc` | `str \| None` | |
| `sha1` | `str \| None` | |

### `class BiosSet` (frozen)

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | non-empty (`min_length=1`); same discipline as `Rom.name` |
| `description` | `str \| None` | |
| `default` | `bool` | |

### `class DriverStatus` (str enum)

Values: `GOOD`, `IMPERFECT`, `PRELIMINARY`. String representation matches the DAT attribute exactly.

The enum is **open-membership**: `<driver status="...">` values not in this set log a `logger.warning` and produce `Machine.driver_status = None`. They do *not* raise `DATError`. Rationale: MAME's schema has historically extended the set (`protection`, `palette`-style attributes); a closed enum would break parsing on every future MAME version. The warning is rate-limited to one log line per unique status string seen in a parse run (avoids log floods on a 43k-machine DAT).

## Public functions

### `parse_dat(path: Path) -> dict[str, Machine]`

- Accepts `.xml` or `.zip`. For `.zip`, extracts to a temp file (single XML inside) and parses that.
- Streams via `lxml.iterparse(events=("end",), tag="machine", **HARDENED_ITERPARSE_KWARGS)` — never loads the full tree. Uses the canonical fast-iter idiom (`Element.clear()` plus `getprevious()` + `del parent[0]`) so the spine of empty siblings does not accumulate across the parse.
- **`HARDENED_ITERPARSE_KWARGS`** (FP20-A, defined in `parser/dat.py` and re-exported to `listxml.py`) pins four safety knobs at every `iterparse` call site:
  - `resolve_entities=False` — blocks Billion Laughs internal-entity expansion (lol1→lol2→…→lol5 DoS) AND the XXE `file://` entity-content leak that `no_network=True` alone does not block.
  - `no_network=True` — already the lxml default; pinned explicitly so a future lxml default-change can't silently relax the contract.
  - `huge_tree=False` — refuses pathologically deep XML trees.
  - `load_dtd=False` — refuses external DTD subset fetches.
- **Zip-bomb protection** (FP20-A): before `zf.extract`, reads `zf.getinfo(member).file_size` from the central directory (metadata only, no decompression) and refuses extraction if it exceeds `_MAX_DAT_BYTES` (256 MiB — ~5× headroom over the real ~50 MiB Pleasuredome DAT). A malicious 100 KB upload declaring gigabytes in its central directory raises `DATError` before any payload touches the tempdir.
- **Zip-slip protection**: rejects any `.zip` member whose path is absolute or contains `..` components → `DATError`. Defense in depth even when the threat model nominally trusts the source, because Phase 4's API exposes `parse_dat` to network-controlled inputs.
- Returns a dict keyed by `Machine.name`. Two machines with the same name is a `ParserError`.
- Raises `ParserError` on malformed XML, missing root element, missing required attributes, or duplicate `name`.

### `parse_catver(path: Path) -> dict[str, str]`

- Returns `{shortname: category}`.
- Tolerates blank lines, lines starting with `;` or `#`, and section headers in `[brackets]`.
- Excludes progettoSnaps configuration-metadata sections (see "Metadata-section handling" below).

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

### `parse_listxml_cloneof(path: Path) -> dict[str, str]`

- Returns `{clone_short_name: parent_short_name}` for every machine with a non-empty `cloneof` attribute. Parents and standalone machines are absent from the map.
- Used by `filter/` to reconstruct parent/clone relationships that the Pleasuredome DAT strips.
- Same `lxml.iterparse` streaming pattern as `parse_listxml_disks` (clear element + detach previous siblings to keep memory bounded across the 43k-machine listxml). Every iterparse call site in `listxml.py` splats the same `HARDENED_ITERPARSE_KWARGS` (XXE / Billion Laughs / `file://` URI defence — see `parse_dat` above).

### `split_manufacturer(raw: str | None) -> tuple[str | None, str | None]`

- Returns `(publisher, developer)`.
- `None` or empty input → `(None, None)`.
- `"Capcom"` → `("Capcom", "Capcom")`.
- `"Capcom (Sega license)"` → `("Capcom", "Sega")` — last `( ... license)` parenthetical is the developer.
- `"Bally / Midway"` → `("Bally / Midway", "Bally / Midway")` — slashes are kept verbatim; we do not attempt to split co-publisher cases.

## Metadata-section handling (all five INI parsers)

progettoSnaps INI files ship under section headers `[FOLDER_SETTINGS]` and `[ROOT_FOLDER]` containing tool configuration (icons, sort orders, UI hints). These keys are not machine shortnames and must not pollute the parsed output. **All five INI parsers** filter these section names from their input via the shared `_META_SECTIONS = frozenset({"FOLDER_SETTINGS", "ROOT_FOLDER"})` deny-list. New metadata sections introduced by future progettoSnaps versions should be added to `_META_SECTIONS`, not handled per-parser.

## Encoding policy (all five INI parsers)

INI files are read as UTF-8. Files containing bytes that aren't valid UTF-8 trigger a `logger.warning("invalid UTF-8 in <path>; falling back to latin-1")` and are then re-decoded with `errors="replace"`. The parser never silently substitutes U+FFFD without surfacing the warning, and never refuses to load a real-world progettoSnaps file just because some character was mojibake.

## Errors

- `ParserError(Exception)` — raised on malformed input. Sub-classes: `DATError`, `INIError`, `ListxmlError`. All carry the source path and a one-sentence cause.

## Edge cases handled

- DAT `.zip` containing zero or multiple `.xml` files → `DATError` with the count.
- DAT `<year>` is `"????"` or `"19??"` → `Machine.year = None`.
- DAT `<machine>` with no `<description>` → `DATError` (description is required).
- DAT containing zero `<machine>` elements (valid XML but wrong root, or genuinely empty) → `DATError("DAT contained no <machine> elements")`. Without this, the user gets a confusing silent `{}` instead of a clear "wrong file?" signal.
- DAT `<rom>` or `<biosset>` with missing or empty `name` attribute → `DATError`. Empty names are corruption (downstream dedup-by-name would silently collide). Mirrors the `<machine>` discipline.
- DAT `<year>` outside `[1970, 2100]` → `Machine.year = None`. MAME's earliest video output (Computer Space) is 1971; values like `<year>1</year>` or `<year>9999</year>` are typos in the DAT, not legitimate dates. Bound is conservative on both ends to leave room for re-released or compilation entries.
- DAT attribute combinations: `isbios + isdevice` is allowed (some entries have both); we record both.
- **Pleasuredome DATs strip `cloneof` and `romof`.** Verified empirically: both the merged and non-merged Pleasuredome 0.284 DATs contain zero `cloneof=` / `romof=` attributes. As a consequence, parsing the Pleasuredome DAT alone yields `cloneof=None` for every machine. Parent/clone relationships come from the official MAME `-listxml` (acquired separately — see design §6.1 "Where `-listxml` comes from" for the tiered acquisition flow, and ADR-0003 for the rationale) and are joined onto Pleasuredome machines by short name in Phase 2's filter. The parser itself is faithful to the DAT and does not synthesize relationships.
- INI shortname appearing twice → last write wins; warn via `logger.warning`.
- INI line with no `=` separator → skipped silently (matches progettoSnaps' own tolerance).
- INI keys before the first `[Section]` header → skipped (their section name is `""`, not in any parser's allow-list).
- INI section header with an inline trailing comment (`[Mature] ; old format`, `[Best]# tier`) → recognized as `Mature` / `Best`. The walker truncates at the first `]` rather than requiring it as the last character. Without this tolerance, an inline-commented `[FOLDER_SETTINGS]` header silently fails to filter and its keys leak into the parsed output. A `[…` line with no closing bracket is malformed and skipped.
- INI file with non-UTF-8 bytes → see "Encoding policy" above (warn + fall back to latin-1, never silent).
- DAT zip member with absolute path or `..` component → `DATError` ("zip-slip"). The threat model nominally trusts the source, but Phase 4 will expose `parse_dat` to network-controlled paths; defense in depth.
- DAT `.zip` that is corrupt or truncated (the file is not a valid zip archive) → `DATError("DAT zip is corrupt or truncated: ..."`, path attached). The parser MUST NOT propagate `zipfile.BadZipFile` to the caller — every CLI-visible error path stays inside `ParserError` so the CLI's catch boundary holds and the user sees a structured message rather than a Python traceback.

## Out of scope

- Filtering or picking — handled by `filter/`.
- Downloading the INI / listxml files — handled by the shared `downloads.py` primitive (introduced with `updates/`) and the wizard (`setup/`).
- Acquiring the official MAME `-listxml` itself — the parser consumes it once it's on disk; how it got there is the wizard's problem (see design §6.1 "Where `-listxml` comes from").
- Verifying that DAT short names match a known set — handled by API startup validation.
- Software-list routing (post-v1, see design §13).
