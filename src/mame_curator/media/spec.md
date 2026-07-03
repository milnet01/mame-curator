# media/ spec

## Contents

- [Contract](#contract)
- [Module layout](#module-layout)
- [Public surface](#public-surface)
- [Public types](#public-types)
- [Public functions](#public-functions)
- [Source contracts](#source-contracts)
- [Cache layout](#cache-layout)
- [Errors](#errors)
- [Edge cases handled](#edge-cases-handled)
- [Consumers / out of scope](#consumers--out-of-scope)
- [Architecture notes](#architecture-notes)
- [Anti-jump compliance](#anti-jump-compliance)

## Contract

Given a parsed `Machine`, this module produces a verified on-disk image path
for any `(machine, kind)` request and lazily caches fetched bytes / text to
disk. Specifically:

- **Build libretro-thumbnails URLs** (boxart / title / snap) from a
  `Machine`, applying libretro's filename escape rule verbatim.
- **Walk a multi-source fallback chain** — for one `(machine, kind)` request
  try the configured sources in order; the first source that yields a real
  image wins. A 404, rate-limit, or network error from one source falls
  through to the next.
- **Fetch with cache** — every image URL feeds `fetch_with_cache`; every
  text / JSON body **except MobyGames' own auth-probe** (see "MobyGames
  divergence") feeds `fetch_text_with_cache`. Both are SHA-256-keyed,
  flat, atomic (`.tmp` + `os.replace`), 404-returns-`None`, non-200-raises.
- **Resolve Wikipedia flavor text** — `resolve_wikipedia_extract` returns a
  frozen `WikipediaExtract` (title / extract / url / license) for the
  Alternatives-drawer "About" paragraph.
- **Per-source rate limiting** — an in-process `TokenBucket` per
  *rate-limited* network source (arcadeDB / wikipediaImage / mobyGames);
  libretro is unthrottled (raw GitHub, no bucket). Exhaustion raises
  `MediaRateLimited` and the chain moves on. No retries; no persistent state
  (buckets reset on server restart).

The module depends on `parser/` (for `Machine`) and `_atomic.fsync_parent_dir`
only. It MUST NOT import from `api/`, `filter/`, `copy/`, or `updates/` (the
four sibling top-level packages). The module is **HTTP-agnostic**: callers
pass in a lifespan-managed `httpx.AsyncClient` and translate exceptions; route
wiring, the `MediaConfig` schema, the readiness API, and the frontend all live
outside `media/` (see "Consumers / out of scope").

## Module layout

Source files under `src/mame_curator/media/`:

| File | Contents |
|---|---|
| `urls.py` | `escape_libretro`, `urls_for`, `MediaUrls` (frozen), the `_BASE_URL` / `_KIND_FOLDER` / `_ESCAPE_CHARS` constants. |
| `cache.py` | `fetch_with_cache`, `cache_path_for`, `MediaError`, `MediaFetchError`, `DEFAULT_MAX_BYTES` (16 MiB), the `http`/`https`-only scheme guard. |
| `cache_text.py` | `fetch_text_with_cache`, `DEFAULT_TEXT_MAX_BYTES` (256 KiB), and its own independent copy of the same `http`/`https`-only scheme guard. |
| `rate_limit.py` | `TokenBucket`, `MediaRateLimited`. |
| `sources.py` | `Kind`, `MediaSource` (Protocol), `LibretroSource`, `ProgettoSnapsSource`, `ArcadeDBSource`, `WikipediaImageSource`, `MediaSourceRegistry`. |
| `mobygames.py` | `MobyGamesSource`, `SourceDisabledFlag`, `mobygames_key_path`. Split out so `sources.py` stays under the 500-line hard cap. |
| `wikipedia.py` | `WikipediaExtract` (frozen), `resolve_wikipedia_extract`. |
| `resolve.py` | `resolve_image` (orchestrator), `build_registry`, `build_all_sources`. The composition root — constructs concrete sources with injected deps. |
| `__init__.py` | Re-exports the public surface; defines `_build_user_agent`. |

## Public surface

Re-exported from `mame_curator.media.__init__` (`__all__`):

| Name | Kind | Source file |
|---|---|---|
| `Kind` | `Literal["boxart", "title", "snap"]` | `sources.py` |
| `MediaSource` | `Protocol` (`@runtime_checkable`) | `sources.py` |
| `MediaSourceRegistry` | class | `sources.py` |
| `LibretroSource` | source class | `sources.py` |
| `ProgettoSnapsSource` | source class | `sources.py` |
| `ArcadeDBSource` | source class | `sources.py` |
| `WikipediaImageSource` | source class | `sources.py` |
| `MobyGamesSource` | source class | `mobygames.py` |
| `SourceDisabledFlag` | class | `mobygames.py` |
| `mobygames_key_path` | function | `mobygames.py` |
| `resolve_image` | async function | `resolve.py` |
| `build_registry` | function | `resolve.py` |
| `build_all_sources` | function | `resolve.py` |
| `resolve_wikipedia_extract` | async function | `wikipedia.py` |
| `WikipediaExtract` | frozen Pydantic model | `wikipedia.py` |
| `MediaUrls` | frozen Pydantic model | `urls.py` |
| `escape_libretro` | function | `urls.py` |
| `urls_for` | function | `urls.py` |
| `cache_path_for` | function | `cache.py` |
| `fetch_with_cache` | async function | `cache.py` |
| `fetch_text_with_cache` | async function | `cache_text.py` |
| `DEFAULT_TEXT_MAX_BYTES` | `int` (256 KiB) | `cache_text.py` |
| `TokenBucket` | class | `rate_limit.py` |
| `MediaError` | exception | `cache.py` |
| `MediaFetchError` | exception | `cache.py` |
| `MediaRateLimited` | exception | `rate_limit.py` |
| `_build_user_agent` | function (impl helper) | `__init__.py` |

## Public types

### `Kind` (typed alias)

```python
Kind = Literal["boxart", "title", "snap"]
```

The **source-chain** vocabulary. Deliberately excludes `video`: `MediaUrls`
has no `video` field, so no source can ever cover it. The route's own
`_VALID_KINDS` set (which includes `video`, still 404-ing) is the *user-input*
gate — a separate concern from this alias.

### `class MediaSource(Protocol)` (`@runtime_checkable`)

Every source implements this shape:

```python
name: ClassVar[str]                    # config key — "libretro", "arcadeDB", ...
license_compatible: ClassVar[bool]     # future P11 contribute-back gate
kinds: ClassVar[frozenset[Kind]]       # which kinds this source covers
disabled_reason: str | None            # instance-level; non-None → gated off

async def prepare(self, machine: Machine, *, client: httpx.AsyncClient) -> None
def url_for(self, machine: Machine, kind: Kind) -> str | None
```

`@runtime_checkable` verifies *attribute presence* only (PEP 544) — signature
correctness is a `mypy` build-time gate, not a runtime one. The runtime check
is defence-in-depth against malformed extensions.

- **`prepare`** — populate any per-machine lookup state. Two-step sources
  (ArcadeDB) hit their JSON endpoint here; single-shot sources
  (Libretro, ProgettoSnaps) implement it as a one-line `return`. The
  Protocol's `...` is a typing stub, **not** an inheritable default — every
  implementer provides the method. May raise `MediaRateLimited` (empty
  bucket) or `MediaFetchError` (network / parse) — both are the orchestrator's
  fall-through signals.
- **`url_for`** — SYNC by design, so the orchestrator iterates candidates
  without a per-source `await`. Returns the candidate URL, or `None` (the
  deterministic "this source has no candidate for this lookup" signal — a kind
  it doesn't cover, or a lookup-cache miss). Distinct from a fetch-time 404.
- **`disabled_reason`** — instance-level (not `ClassVar`): the same class can
  be ready on one process and disabled on another (missing key / absent pack).
  Non-`None` means the registry filters it out of the chain *before* any
  `prepare` / `url_for` call, and the readiness endpoint surfaces the string.

### `class MediaSourceRegistry`

```python
def __init__(self, configured: tuple[str, ...], available: Mapping[str, MediaSource]) -> None
def chain_for(self, kind: Kind) -> tuple[MediaSource, ...]
```

A pure filter/orderer — no app-state, no HTTP, so tests build one from fake
sources directly. The composition root (`build_registry`) constructs concrete
instances (injecting the app-state limiters + the `SourceDisabledFlag`) and
hands the registry a `name → instance` map plus the configured-order tuple.

`chain_for(kind)` returns the sources covering `kind` **and** ready, in
configured order. Filtering, in order:

1. `"libretro"` is appended to the name list if absent from `configured` (it
   is the baseline; `build_registry` always includes it in `available`). This
   happens before the per-name loop below.
2. Unknown names (absent from `available`) are dropped with a **one-time**
   WARNING, deduped process-wide (a module-level `set` — the registry is
   rebuilt per request, so without the dedup a misconfigured name would log on
   every request). `_reset_unknown_source_warn_dedup()` clears it in tests.
3. Sources whose `kinds` don't cover `kind` are filtered out.
4. Sources with a non-`None` `disabled_reason` are filtered out.

### `class MediaUrls` (frozen Pydantic)

`boxart: str`, `title: str`, `snap: str`. `frozen=True, extra="forbid"`. No
`video` field by design — callers dispatching on `kind` MUST short-circuit
`video` before invoking `urls_for`.

### `class WikipediaExtract` (frozen Pydantic)

```python
title: str      # post-redirect page title  (data["title"])
extract: str    # ~1-2 sentence summary       (data["extract"])
url: str        # canonical page URL          (data["content_urls"]["desktop"]["page"])
license: str = "CC-BY-SA-4.0"   # client-side constant — REST summary has no license field
```

`license` is a plain `str` (not `Literal`) so a future CC-BY-SA bump isn't a
schema-breaking change. `frozen=True, extra="forbid"`.

### `class TokenBucket`

```python
def __init__(self, *, rate: float, capacity: int, time_fn: Callable[[], float] = time.monotonic)
def acquire(self) -> bool
```

Classic in-memory single-process token bucket. Tokens accrue at `rate`/sec up
to `capacity`; `acquire()` consumes one, returning `False` when empty. `rate`
and `capacity` must be positive (else `ValueError`). `time_fn` is injectable so
tests advance time without `time.sleep`; the clock anchor advances
unconditionally so a backward (non-monotonic) step can't wedge refill.

### `class SourceDisabledFlag`

A process-wide mutable holder (`reason: str | None`) for a source's
runtime-disabled reason. Injected into `MobyGamesSource` at construction and
owned by the lifespan on `app.state`. It exists because `media/` is
HTTP-agnostic: `prepare` receives only an httpx client, so it can't write a
disabled reason back onto `app.state` directly. The holder is the indirection
that keeps `media/` free of any `api/` import while letting a 401/403 persist
across the per-request source instances.

### Exceptions

```python
class MediaError(Exception): ...              # base
class MediaFetchError(MediaError): ...         # non-200 (≠404) / network / parse / oversize / decode
class MediaRateLimited(MediaError): ...        # a source's TokenBucket is empty (or upstream 429)
```

`resolve_image` swallows both `MediaFetchError` and `MediaRateLimited`
internally (the chain is the recovery path); `resolve_wikipedia_extract`
*raises* them and the route catches `MediaError` → `null`.

## Public functions

### `escape_libretro(name: str) -> str`

Replaces every character in `& * / : \ < > ? | "` (10 chars) with `_`;
everything else (apostrophes, spaces, parens, hyphens, unicode) passes
through. Idempotent (`_` isn't in the set). Applied **before** percent-encoding.

### `urls_for(machine: Machine) -> MediaUrls`

Builds all three libretro URLs from `machine.description`: `escape_libretro`
→ `urllib.parse.quote` → `f"{_BASE_URL}/{folder}/{encoded}.png"`. `_BASE_URL`
is `https://raw.githubusercontent.com/libretro-thumbnails/MAME/master`.

### `cache_path_for(url: str, cache_dir: Path) -> Path`

Pure (no I/O): `cache_dir / f"{sha256(url).hexdigest()}{ext}"` where
`ext = Path(urlparse(url).path).suffix`. A URL with no path suffix yields a
bare-hex filename. Used by both cache helpers and by parse-before-trust
unlink paths.

### `async fetch_with_cache(url, cache_dir, *, client, max_bytes=DEFAULT_MAX_BYTES) -> Path | None`

`DEFAULT_MAX_BYTES = 16 MiB` (a module-internal constant — unlike its text
sibling `DEFAULT_TEXT_MAX_BYTES`, it is deliberately *not* re-exported in
`__all__`; a caller overriding the image cap passes an explicit `max_bytes`).
Returns the cached path on hit; otherwise streams the body to a `.tmp` sibling
and `os.replace`s it in. Guards, in
order:

- Non-`http`/`https` scheme → `MediaFetchError` **before any I/O** (blocks
  `file://` / `data:` — the security gate the `file://` short-circuit relies
  on, FP27 B4).
- 404 → `None` (sentinel; no negative caching).
- non-200 → `MediaFetchError("upstream {status} ...")`.
- streamed bytes exceed `max_bytes` → abort + `MediaFetchError("BodyTooLarge ...")`.
- 200 + empty body → `MediaFetchError("empty body ...")` (caching a zero-byte
  response would poison the slot forever — `raw.githubusercontent.com`
  rate-limit interstitials return `200 + Content-Length: 0`).
- `httpx.HTTPError` → `MediaFetchError` chained via `__cause__`.

Concurrent same-URL calls are safe (unique `.tmp` + `os.replace` never tears
the file); the wasted second download is accepted at single-user scale.

### `async fetch_text_with_cache(url, cache_dir, *, client, max_bytes=DEFAULT_TEXT_MAX_BYTES) -> str | None`

The text / JSON sibling. `DEFAULT_TEXT_MAX_BYTES = 256 KiB`. Carries its own
copy of the same `http`/`https` scheme guard (not imported from `cache.py`),
plus the 404 sentinel, oversize / empty / network handling of `fetch_with_cache`.
Additionally validates UTF-8 **before** committing the cache file — a
non-decodable body raises `MediaFetchError("decode failed ...")` and never
poisons the slot. Returns the body as `str` so callers `json.loads` it
themselves (the layer is content-agnostic — no `Content-Type` enforcement).

### `async resolve_image(machine, kind, *, registry, cache_dir, client) -> Path | None`

The orchestrator. Walks `registry.chain_for(kind)`; for each source: `await
prepare` (swallow `MediaRateLimited` → INFO, `MediaFetchError` → WARNING, both
fall through); read `url_for`; if `None`, next source; if a `file://` URL,
short-circuit (see below); else `fetch_with_cache` (swallow `MediaFetchError`
→ WARNING, fall through). First real `Path` wins; every source missing →
`None`. **Returns `Path | None` only — never raises for an upstream failure.**

**`file://` short-circuit** (local snap pack). `fetch_with_cache`'s scheme
guard rejects `file://` by design, so the orchestrator serves the path
directly via `Path(url2pathname(urlparse(url).path))` (`url2pathname` handles
the Windows `/C:/…` form). Hardened (FP33 H1): **only `ProgettoSnapsSource`
is trusted** to emit `file://`. A *network* source returning `file://` (e.g. a
MITM injecting `file:///etc/passwd` on ArcadeDB's plaintext hop) is logged and
dropped — never served.

### `async resolve_wikipedia_extract(machine, *, cache_dir, client, limiter) -> WikipediaExtract | None`

Standalone (no source object), so the `limiter: TokenBucket` is an explicit
kwarg — the route passes the **same** `app.state.wikipedia_limiter` +
`cache_dir` the `WikipediaImageSource` uses, so an image lookup and an
extract lookup share one courtesy budget and one cache slot (same URL → same
SHA-256 key). Acquires one token first (empty → `MediaRateLimited` before any
upstream hit), canonicalises the description, fetches the REST summary, and
parses it. Returns `None` on a genuine 404, an empty canonical title, a
valid-but-non-object JSON body (unlinked, but degraded to `None` since the
About paragraph is non-essential), or a summary missing a field it surfaces.
A `JSONDecodeError` **raises** `MediaFetchError` after unlinking the poisoned
slot (parse-before-trust — see § "Source contracts" for the full two-class model).

### `build_registry(*, configured, cache_dir, arcadedb_limiter, wikipedia_limiter, mobygames_limiter, mobygames_disabled, snap_dir=_DEFAULT_SNAP_DIR) -> MediaSourceRegistry`

The composition root for the image chain. Constructs **only** the sources
named in `configured` (∪ the `libretro` baseline), injecting the app-state
limiters + the `SourceDisabledFlag`, and wraps them in a `MediaSourceRegistry`.
Building only the configured subset means dropping `mobyGames` from
`media.sources` also suppresses its keyless-startup WARNING. Keeping the
factory in `media/` (deps passed explicitly) honours the anti-jump rule.
`snap_dir` defaults to `_DEFAULT_SNAP_DIR` for direct callers, but the API
route passes `world.config.media.snaps_dir / "snap"` so the progettoSnaps
read-path tracks the configured pack folder (mame-curator-1081).

### `build_all_sources(*, cache_dir, arcadedb_limiter, wikipedia_limiter, mobygames_limiter, mobygames_disabled, snap_dir=_DEFAULT_SNAP_DIR) -> dict[str, MediaSource]`

Constructs **all five** known sources regardless of config — the readiness
endpoint must report every source's real state, including ones the user
removed from `media.sources`. Shares the `_source_factories` table with
`build_registry`.

### `mobygames_key_path(secrets_dir=Path("data/secrets")) -> Path`

`secrets_dir / "mobygames.key"`. Single source of truth for the dotfile
location — shared by `MobyGamesSource._resolve_key` (read) and the readiness
route's secret-write (write) so the written key is exactly what the next
construction reads.

### `_build_user_agent() -> str`

Implementation helper (underscore-prefixed but re-exported for the lifespan
constructor + UA tests). Returns
`mame-curator/{__version__} (+https://github.com/milnet01/mame-curator)` per
Wikipedia's API:Etiquette.

## Source contracts

| `name` | `license_compatible` | `kinds` | Network? | Can disable? |
|---|---|---|---|---|
| `libretro` | `True` | `{boxart, title, snap}` | yes (raw GitHub) | never |
| `progettoSnaps` | `True` | `{snap}` | no (local pack) | pack absent/empty |
| `arcadeDB` | `True` | `{boxart, title, snap}` | yes | never |
| `wikipediaImage` | `False` | `{boxart}` | yes | never |
| `mobyGames` | `False` | `{boxart}` | yes | no/bad key |

- **libretro** — baseline. `prepare` is a no-op; `url_for` delegates to
  `urls_for` and always returns a URL. No auth, no rate limit.
- **progettoSnaps** — serves `<snap_dir>/<name>.png` as a `file://` URL when
  present, else `None`; only covers `snap`. Never hits the network.
  Self-disables at construction if `snap_dir` isn't a readable non-empty
  directory (the whole probe is wrapped in `except OSError` — FP33 M1 — so an
  inaccessible dir self-disables instead of 500-ing every media request).
  Per-request existence checks are memoised (`_present` / `_missing` sets) so
  repeated `url_for` calls don't re-`stat()`.
- **arcadeDB** — two-step. `prepare` acquires a token (empty → `MediaRateLimited`),
  fetches `service_scraper.php?ajax=query_mame&game_name={name}` (HTTP 301 →
  HTTPS handled by `follow_redirects=True`) via `fetch_text_with_cache`, and
  parses `{"release": N, "result": [...]}` (the module reads only `result`;
  `release` is upstream's integer match-count, unused here). Maps
  `result[0]`'s `url_image_flyer` → `boxart`,
  `url_image_title` → `title`, `url_image_ingame` → `snap` (redirector-form
  URLs `fetch_with_cache` follows). Empty `result` → no cache entry →
  `url_for` returns `None`. Rate limit configurable via
  `media.arcadedb_rate_limit_per_min` (default 30).
- **wikipediaImage** — one-step, `boxart` only (the REST summary's
  `thumbnail.source` is the only reliably-located image field; degrading to it
  for other kinds would let a wrong-shaped image win over a downstream
  candidate). Canonicalises `machine.description` (drops a trailing
  parenthesised qualifier: `"Pac-Man (Midway)"` → `"Pac-Man"`) before the
  lookup. Rate limit 60/min courtesy cap.
- **mobyGames** — `boxart` only, requires an API key. Resolves it from
  `MOBYGAMES_API_KEY` (env, wins) then a **mode-0600** `data/secrets/mobygames.key`
  dotfile (POSIX-only mode check — Windows reports a synthetic 0o666, so the
  key is accepted there on mode grounds). Any of missing / mode-wrong /
  unreadable → `disabled_reason` set (FP34 M1 treats an unreadable-but-present
  key as missing rather than crashing). A **missing** key emits one
  process-wide-deduped WARNING. A **mode-wrong or unreadable** key logs its own
  (non-deduped) WARNING per construction, then falls through the missing-key
  path — so the *first* bad-key construction emits **two** WARNINGs (its own +
  the one-time missing-key line) and each later per-request rebuild re-emits
  only the non-deduped one. Rate limit configurable via
  `media.mobygames_rate_limit_per_min` (default 5).

**Parse-before-trust** (arcadeDB / wikipediaImage / `resolve_wikipedia_extract`)
distinguishes two failure classes:

- **Top-level parse failure** — a `JSONDecodeError`, or a valid-but-non-object
  body (`[]` / `null` / a bare string). The handler unlinks the poisoned cache
  slot (`cache_path_for(url, cache_dir).unlink(missing_ok=True)`) so the next
  request re-fetches, then: a `JSONDecodeError` raises `MediaFetchError`
  everywhere; a non-object body raises `MediaFetchError` from a source
  `prepare` but degrades to `None` in `resolve_wikipedia_extract` (the About
  paragraph is non-essential).
- **Nested-shape drift** — a valid object whose inner shape is wrong (`result`
  not a list, `result[0]` not a dict, a URL field not a string, `thumbnail`
  not a dict). This is a **silent no-match**: the handler returns with no
  candidate — **no unlink, no raise**. The container types are guarded
  (FP33 H2) only so an `AttributeError`/`TypeError` can never escape to the
  route as a 500.

**MobyGames divergence from the shared text-cache path.** `MobyGamesSource.prepare`
makes its **own** `client.get` (not `fetch_text_with_cache`) for two reasons:
it must tell 401/403 (disable) from 429 (rate-limit) from other non-200s —
distinctions the shared helper collapses into one generic `MediaFetchError` —
and the API key rides in the query string, so every error / log message
redacts it (`_redact`). A 401/403 flips the injected `SourceDisabledFlag`
(one WARNING; persists until restart); 429 → `MediaRateLimited`; 404 →
no candidate.

## Cache layout

- **Directory:** injected as `cache_dir: Path`; `media/` reads no config. The
  route passes `world.config.media.cache_dir` (default `./data/media-cache`).
- **Filename:** `<sha256(url).hexdigest()><ext>`, flat (no subdirs). Image and
  text bodies share the directory but never the slot (different URLs → different
  hashes).
- **Write:** stream to a unique `.tmp` sibling in the same directory →
  `os.replace` → `fsync_parent_dir`. In-filesystem rename, so EXDEV never
  applies.
- **Read:** `Path.exists()` → return. No mtime / checksum / LRU. The cache is
  permanent by design; no negative caching (a 404 is never written).

## Errors

Typed hierarchy rooted at `MediaError` (see "Exceptions"). Library code uses
`logging.getLogger(__name__)`; `print()` is forbidden (CLAUDE.md). Never raises
bare `Exception`.

## Edge cases handled

- Non-`http`/`https` URL into either cache helper → `MediaFetchError` before
  any I/O. Backstops the `file://` short-circuit's own trust check.
- `200 + empty body` → `MediaFetchError`, `.tmp` removed (poison-cache guard).
- Body exceeds `max_bytes` mid-stream → abort + `MediaFetchError`, `.tmp` removed.
- Non-UTF-8 text body → `MediaFetchError("decode failed ...")`, slot never written.
- Malformed JSON / non-object body → poisoned slot unlinked, then raise
  (`prepare`) or, for the non-object case, `None` (`resolve_wikipedia_extract`).
  Nested-shape drift (a wrong-typed inner field) → silent no-match: no unlink,
  no raise.
- A `file://` URL from any source other than `progettoSnaps` → logged + dropped.
- A `progettoSnaps` pack file that vanishes between `url_for` and the serve →
  falls through to the next source.
- `snap_dir` that is a regular file / unreadable / execute-but-not-read → the
  source self-disables (`except OSError`), never crashes `build_registry`.
- MobyGames key file unreadable / corrupt / TOCTOU-deleted after `stat` →
  treated as missing (self-disable), never crashes construction.
- Empty canonical Wikipedia title (description was all-parenthetical) → `None`,
  no upstream hit.

## Consumers / out of scope

The following are **caller-side** and live outside `media/`:

- **Route wiring** — `GET /media/{name}/{kind}` (calls `resolve_image`;
  `None` → 404), `GET /media/{name}/wiki` (calls `resolve_wikipedia_extract`;
  catches `MediaError` → `null`), `GET /api/media/sources` (readiness),
  `PUT /api/media/sources/{name}/secret` (paste-key write) — all in
  `api/routes/media.py`. **A single source's 5xx / transport failure no longer
  maps to a `502`** — `resolve_image` swallows it and advances the chain; a
  whole-chain miss is the existing `404 media_upstream_not_found`.
- **`MediaConfig` schema** (`fetch_videos`, `cache_dir`, `snaps_dir`, `sources`,
  `arcadedb_rate_limit_per_min`, `mobygames_rate_limit_per_min`) + the
  `SourceReadinessRow` / `SourceReadiness` / `SourceSecret` wire models —
  `api/schemas.py`.
- **Lifespan wiring** — the shared `httpx.AsyncClient` (UA header, `timeout=10`,
  `follow_redirects=True`), the three `TokenBucket`s, and the
  `SourceDisabledFlag` are constructed on `app.state` in `api/app.py`.
- **The `refresh-snaps` CLI** that downloads + extracts the progettoSnaps pack
  — `updates/snaps.py` + `cli/`. When `--dest` is omitted it reads
  `media.snaps_dir` from `--config`, so the download folder and this source's
  read-path (`snaps_dir/snap`) can't diverge (mame-curator-1081).
- **Frontend** — Settings → Media tab, `AboutSection`, `useMediaSources`, etc.

Also deferred (out of `media/`'s current scope):

- **Video thumbnails**, **EmuMovies**, **per-image license inspection**,
  **`keyring`-stored keys**, **source-specific retries**, **plugin
  auto-discovery** — all post-P10 per `docs/specs/P10.md` § "Out of scope (deferred)".
- **MobyGames 200-path cover parse + JSON-body caching** — deferred to
  `mame-curator-1079`. Until then a valid key validates but yields no covers
  (`_url_cache` stays empty; `url_for` → `None`).

## Architecture notes

- **Protocol over inheritance.** `MediaSource` is a `Protocol`; the five
  implementations share no base class, no `super()`, no MRO. The orchestrator
  depends only on the protocol surface.
- **Two-phase per-source dispatch:** async `prepare` then sync `url_for`. The
  orchestrator awaits `prepare` once per `(source, machine)` before reading
  candidates. No async lock around per-source lookup caches — the on-disk
  atomic write is the concurrency backstop; a wasted second parse is accepted
  at single-user scale.
- **Per-source limiter as constructor injection.** The `TokenBucket` holds
  process-wide state that must survive per-request source re-creation, so it
  lives on `app.state` and is injected — which also lets tests substitute a
  fake bucket without monkey-patching app state.
- **The registry is per-request.** The route rebuilds it (via `build_registry`,
  from `world.config.media.sources`) on each request and passes it into
  `resolve_image` — which *receives* a registry, it does not build one. So a
  `PATCH /api/config` reorder takes effect on the next request with no restart. Per-request source `_url_cache`s are
  dropped at request end; process-wide state (buckets, the MobyGames disabled
  flag) lives on the limiters / `app.state`, not the sources.

## Anti-jump compliance

- The only out-of-package symbols imported are `parser.models.Machine` and
  `_atomic.fsync_parent_dir` (the `updates` snap-extraction path is named in a
  comment for provenance, not imported) — the sibling-package import ban stated
  in § Contract holds.
- `httpx` + `pydantic` already in `[project.dependencies]`; no new runtime deps.
- `keyring` deliberately NOT added — deferred to P11.
