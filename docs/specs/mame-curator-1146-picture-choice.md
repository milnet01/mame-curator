<!-- ants-spec-format: 1 -->
# mame-curator-1146 — Let the user choose a game's picture, step by step

**Status:** accepted (2026-11-10).
**Kind:** accessibility.
**Source:** ROADMAP mame-curator-1146 (user, 2026-10-30: wizards for "fix a game's picture or version").

**Pairs with:** the version half of mame-curator-1146, built without a spec on the `/fix/:shortName` route. **Builds on:** mame-curator-1144 (`GuideStep`, `GuideAction`).

**Layman:** A game sometimes shows the wrong picture, or none. A short guide shows every picture the app can find for that game, in large images, and the user picks one. That version of the game keeps that picture until the user changes it back.

## 1. Goal

From a game's version guide, a user can choose which picture the game shows. The guide asks one question per screen. It shows each picture it found, large, with a plain label and where it came from. The choice is saved, shows on the Library at once, survives a restart, travels in a Backup export, and can be undone with "Use the usual picture".

## 2. Problem

1. **No choice exists.** `media_proxy` in `src/mame_curator/api/routes/media.py` serves whatever `resolve_image` (`src/mame_curator/media/resolve.py`) finds first, walking `media.sources` in order. Nothing stores a per-game preference.
2. **Nothing lists more than one picture.** `resolve_image` stops at the first hit. Each source can be asked for one `(source, kind)` pair through `prepare` and `url_for` (`MediaSource` in `src/mame_curator/media/sources.py`), but no function or route does that.
3. **Some sources cost.** `ArcadeDBSource.prepare` and `WikipediaImageSource.prepare` take a token from their `TokenBucket` on every call, even when the lookup is cached. `MobyGamesSource` needs an API key and has the smallest default bucket (`mobygames_rate_limit_per_min`, 5). Asking every source for every kind on each visit would spend those limits.
4. **The browser keeps the old picture.** `media_proxy` answers with `Cache-Control: public, max-age=2592000, immutable`. `GameCard.tsx` and `AlternativesDrawer.tsx` request `/media/{short_name}/boxart` with no other part, so a new choice behind the same address would not show for 30 days.
5. **Backups are strict.** `ConfigExportBundle` (`src/mame_curator/api/schemas.py`) and `ConfigExportBundleSchema` (`frontend/src/api/schemas.ts`) both reject unknown keys. A backup is a breaking surface (`docs/standards/versioning-overrides.md` item 2).
6. **Two files are at their size cap.** `api/routes/config.py` and `api/routes/games.py` are near the 500-line hard cap (`wc -l`, 2026-11-05: 492 and 450). New code cannot go in either without a split.

## 3. Scope decisions (agreed with the user)

From the user, 2026-10-30: four wizards, one of them "fix a game's picture or version"; a guide is one question per screen in large text, with extras behind "More options".

The user is away. Every call below is the author's (2026-11-05), open to the user:

- **One guide for both halves.** The version route gains a first screen, "What would you like to fix?", once this half ships.
- **The choice is a `(source, kind)` pair**, stored per short name in a new file, `data/pictures.json`. Not a URL, not a copied image.
- **The choice applies to the game's picture**: what `/media/{name}/boxart` serves, which is what every card and the versions list show. The `title` and `snap` addresses are unchanged; nothing in the app shows them.
- **Free sources first; "Look in more places" asks the limited ones.** The first list asks only sources with no rate limit. The limited ones are one press away, because ArcadeDB is the only limited source covering all three kinds (`media/spec.md` § Source contracts), so hiding it would hide most alternatives for games the local folders do not cover.
- **A saved choice is not checked by fetching it.** The save checks only that the source is in use and covers the kind; the server falls back if the pair stops resolving (§4.3).
- **A backup without `pictures` means no choices.** Export leaves the key out when there are none, so such a backup still opens in an older release. Importing one clears current choices; the snapshot taken first keeps them.

## 4. Design

### 4.1 Where the code lives

```
src/mame_curator/media/candidates.py      resolve_pair, resolve_image_found, list_candidates, LIMITED_SOURCES
src/mame_curator/api/pictures.py          PictureChoices model, load_pictures, write_pictures
src/mame_curator/api/schemas_pictures.py  wire models (§4.4)
src/mame_curator/api/routes/pictures.py   the three /api/games/{name}/picture routes
src/mame_curator/api/routes/backup.py     export and import, moved out of config.py (§2 item 6)
frontend/src/lib/pictureSrc.ts            the card's image address (§4.5)
frontend/src/components/guide/steps/      one file per picture step (§4.6)
frontend/src/strings_guide.ts             picture text, under strings.guide.fix.picture
```

`WorldState` (`api/state.py`) gains `pictures: PictureChoices`, loaded in `build_world` beside `notes`, and `replace_world` gains a `pictures` argument.

### 4.2 The stored choice

```python
# api/pictures.py
class PictureChoice(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: str = Field(min_length=1, max_length=64)   # a media.sources name
    kind: Kind                                         # "boxart" | "title" | "snap"

class PictureChoices(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    pictures: dict[Annotated[str, Field(max_length=64)], PictureChoice] = {}
```

```json
{"pictures": {"pacman": {"source": "esde", "kind": "title"}}}
```

- **Path:** `world.data_dir / "pictures.json"`, written as that literal so `versioning-overrides.md` item 2's grep finds it.
- **Write:** `write_json_atomic`, after `snapshot_files` copies the current file (when it exists), as `_persist_overrides` does in `api/routes/curate.py`.
- **Load:** `load_pictures(path)`. A missing file is no choices. An unreadable or invalid file is also no choices, with one WARNING naming the path. The file is left on disk; the next save snapshots it, when it can be read, before replacing it. A picture is cosmetic, so a bad file must not stop the app.
- **`source` is any name, not a known one.** A source a later release renames or drops then falls back (§4.3) instead of making the file fail to load.

### 4.3 The picture address

`GET /media/{name}/{kind}` keeps every current behaviour, plus:

| Request | Serves | On a miss | `Cache-Control` |
|---|---|---|---|
| `?source=S` | only the pair `(S, kind)`; no choice, no fallback | 404 `media_upstream_not_found`, also when S is rate-limited or fails | as today |
| `kind=boxart`, no `source`, a choice stored for `name` | the chosen pair | today's chain for `boxart` | as today only when the chosen pair served and `v` equals the choice's `<source>.<kind>`; otherwise `no-store` |
| `kind=boxart`, no `source`, no choice stored, `v` present | today's chain | 404, as today | `no-store` |
| anything else | today's chain | 404, as today | as today |

- `S` must be a source in `registry.chain_for(kind)`: in `media.sources` (or `libretro`), ready, and covering `kind`. Otherwise 422 `media_source_unknown` (`MediaSourceUnknownError`). A stored choice failing the same test for its own `kind` falls back.
- A rate limit or fetch error on the chosen pair falls back, as one source's failure does in `resolve_image`.
- `no-store` on a fallback means the card shows the chosen picture again once it resolves.
- The server reads the card's `v` (§4.5) only to choose `Cache-Control`. An address is cached for good only when it names what it served: the plain address with no choice stored, or a `v` naming the choice served. Any other query part is ignored.

```python
# media/candidates.py
LIMITED_SOURCES: frozenset[str] = frozenset({"arcadeDB", "wikipediaImage", "mobyGames"})

@dataclass(frozen=True)
class Found:
    source: str
    kind: Kind
    path: Path

async def resolve_pair(machine, source: str, kind: Kind, *, registry, cache_dir, client) -> Path | None
async def resolve_image_found(machine, kind: Kind, *, registry, cache_dir, client) -> Found | None
async def list_candidates(machine, *, registry, ask_limited: bool, cache_dir, client) -> CandidateList
```

- `resolve_pair` asks one source for one kind, using the same `prepare`, `url_for`, local-folder and `fetch_with_cache` steps as `resolve_image`, including the rule that only `progettoSnaps`, `esde` and `retroarchThumbnails` may answer with `file://`. It returns `None` when the source is not in `registry.chain_for(kind)`, has no candidate, or the upstream answers 404. It raises `MediaRateLimited` and `MediaFetchError`; callers decide.
- `resolve_image_found` is `resolve_image` reporting which source answered. `resolve_image` keeps its signature and returns `found.path`.
- `list_candidates` walks `boxart`, `title` and `snap` in that order and, for each, every source in `registry.chain_for(kind)`, skipping `LIMITED_SOURCES` unless `ask_limited`. It takes `resolve_pair`'s steps, but calls each source's `prepare` at most once per listing, so a limited source spends one token however many kinds it covers. A source whose `prepare` raised is not asked again for a later kind. It drops a candidate whose file bytes equal an earlier one's. It returns the found pairs, the limited sources it skipped (`not_asked`), and the sources that raised (`not_answered`).

### 4.4 The routes

All three live in `api/routes/pictures.py`. Unknown `name` is 404 `game_not_found` on each.

| Method | Path | Body | Reply | Mut. |
|---|---|---|---|---|
| GET | `/api/games/{name}/picture/candidates?further=false` | | `PictureCandidates` | |
| PUT | `/api/games/{name}/picture` | `PictureChoice` | `PictureChoiceView` | ✓ |
| DELETE | `/api/games/{name}/picture` | | `PictureChoiceView` | ✓ |

```python
# api/schemas_pictures.py — all frozen, extra="forbid"
class PictureCandidate(BaseModel):
    source: str
    kind: Kind
    in_use: bool

class PictureCandidates(BaseModel):
    short_name: str
    chosen: PictureChoice | None
    chosen_found: bool                 # False only when a stored choice did not resolve now
    candidates: tuple[PictureCandidate, ...]
    not_asked: tuple[str, ...]
    not_answered: tuple[str, ...]

class PictureChoiceView(BaseModel):
    short_name: str
    chosen: PictureChoice | None
```

**Candidates.** `further=true` passes `ask_limited=True`. The route also finds the picture in use: the stored choice when it resolves, else `resolve_image_found` for `boxart`. That one chain walk is the card's own request, and it can reach a limited source only when every source before it misses. A stored choice from a limited source costs that source one `prepare`, as the card's own request does. The candidate whose bytes equal the in-use file gets `in_use: true` and comes first. The in-use picture is added when the list lacks it. The rest keep `list_candidates`' order.

**Save.** The body's `source` must pass §4.3's `registry.chain_for(kind)` test, else 422 `media_source_unknown`. The route fetches nothing. It then takes `world_lock`, writes the file (§4.2), and swaps the world. `GameCard.picture` carries the choice from then on.

**Clear.** Removes the entry, writes and swaps under `world_lock` as Save does. Clearing a game with no choice writes nothing and replies `chosen: null`.

### 4.5 The card's image address

`GameCard` (`api/schemas_games.py`, built only in `_card` in `api/routes/games.py`) gains `picture: PictureChoice | None`. `GameCardSchema` gains `picture: PictureChoiceSchema.nullable()`.

```ts
// frontend/src/lib/pictureSrc.ts
export function pictureSrc(card: { short_name: string; picture: PictureChoice | null }): string
// no choice → /media/<name>/boxart
// a choice  → /media/<name>/boxart?v=<source>.<kind>
```

`GameCard.tsx` and `AlternativesDrawer.tsx` use it. A new choice is a new address, so the browser fetches it. Clearing returns to the plain address, which holds the usual picture.

### 4.6 The guide

The version half's route, `/fix/:shortName`, gains these screens. They act on the version in use when they open: the `in_use` of `GET /api/games/{shortName}/alternatives`, as `FixVersionPage` reads it, or `shortName` when `in_use` is null. After a version save that reply is reloaded, so they act on the saved version. Each renders through `GuideStep`, with every action a `GuideAction`, so mame-curator-1144 INV-2 (focus) and INV-3's exit rule hold here unchanged.

1. **What would you like to fix?** Two actions: "A different version" (the version half's screens) and "A different picture". Shown only when the game has more than one version; otherwise the guide opens at step 2.
2. **Which picture would you like?** While the list loads: "Looking for pictures…" in a `role="status"` element. Then one column of candidates, each one `GuideAction` holding the image, loaded from `/media/<name>/<kind>?source=<source>`, at the column's width and, under it, its label and place, for example "Title screen, from your ES-DE pictures". The in-use one also says "In use now" in text. The image's `alt` is empty, because the text beside it says the same.
   - Under the heading: "Your choice is for this version only."
   - "Look in more places" when `not_asked` or `not_answered` is not empty; it reloads with `further=true`.
   - When `not_answered` is not empty: "Some places did not answer. Try again in a minute."
   - When `chosen_found` is false: "The picture you chose cannot be found now."
   - "Use the usual picture" when `chosen` is set.
   - No candidates: "We found no pictures for this game.", with "Look in more places" if offered, and "Back to the Library".
3. **Done.** "Your game now shows this picture." with the image from `pictureSrc`, or "Your game shows its usual picture again." after a clear. "Back to the Library".

Choosing the candidate in use saves nothing and says "You are already using this picture." A failed save or clear shows the version half's failure screen: the heading "Your choice was not saved.", the error in a `role="alert"` element, "Nothing has changed.", "Try again" and Back. After a save or clear, the guide invalidates the `["games"]` and `["alternatives"]` queries.

The entry link in `AlternativesDrawer` shows for every game, not only those with several versions, and reads "Fix this game's picture or version, step by step".

| `kind` | Label | `source` | Place |
|---|---|---|---|
| `boxart` | Box or flyer | `esde` | from your ES-DE pictures |
| `title` | Title screen | `retroarchThumbnails` | from your RetroArch pictures |
| `snap` | In-game screen | `progettoSnaps` | from your Progetto-SNAPS pack |
| | | `libretro` | from libretro-thumbnails, online |
| | | `arcadeDB` | from ArcadeDB, online |
| | | `wikipediaImage` | from Wikipedia, online |
| | | `mobyGames` | from MobyGames, online |

A source not in the table shows its own name.

### 4.7 Backup and restore

- `ConfigExportBundle` gains `pictures: dict[str, Any] | None = None`, holding the whole `pictures.json` object, `{"pictures": {...}}`. `ConfigExportBundleSchema` gains `pictures: z.record(z.string(), z.unknown()).optional()`.
- **Export** includes `pictures` only when at least one choice exists. Every other key is unchanged, including `null` values inside `config`.
- **Import** validates `pictures` with `PictureChoices` (invalid → `ConfigError` 422, "config import: invalid pictures", nothing written). Absent → no choices. `pictures.json` joins the import's `targets`, so it is snapshotted first and put back if a later write fails.
- **Restore** adds `"pictures.json": world.data_dir / "pictures.json"` to its `targets` and reloads it with `load_pictures`. A snapshot taken before this release does not cover the name, so `restore_snapshot` leaves the file alone.

## 5. Invariants

- **INV-1** — A save writes `data/pictures.json` in §4.2's shape, after snapshotting the previous file, and a restart loads the same choice.
  *Test:* `tests/api/test_mame_curator_1146_picture_choice.py`: PUT, assert the file's JSON and a new snapshot holding the old file, rebuild the world, assert `GameCard.picture`.
  *Breaks when:* the write skips the snapshot, or `build_world` does not load the file.

- **INV-2** — An unreadable, non-JSON or invalid `pictures.json` loads as no choices, logs one WARNING, and leaves the file's bytes unchanged until a save.
  *Test:* same file, one fixture per case; the app starts and `/api/games` answers 200.
  *Breaks when:* a bad file raises out of `build_world`, or the loader rewrites it.

- **INV-3** — With a choice stored, `/media/{name}/boxart` serves the chosen pair's bytes. When that pair is outside `chain_for(kind)`, has no candidate, 404s, is rate-limited or fails, it serves the chain's `boxart` with `Cache-Control: no-store`. The immutable header goes only on a reply whose address names what it served (§4.3).
  *Test:* `tests/api/test_mame_curator_1146_picture_choice.py` with fake sources: a choice of `(B, title)` where source A, first in the chain, has a `boxart` of other bytes. Then the same with B removed from `media.sources`, and with B raising `MediaRateLimited`. Then, with the choice stored, a request with no `v` and one with `v=A.boxart` → `no-store`; with no choice stored, `v=B.title` → `no-store`.
  *Breaks when:* the route ignores the choice (A's bytes come back), a fallback keeps the immutable header, or the plain address is cached holding the chosen picture.

- **INV-4** — A choice changes only `/media/{name}/boxart` without `source`. `title`, `snap`, other games and `?source=` requests answer as they did before.
  *Test:* same file: with a choice stored, `title` and `snap` for that game equal their bytes with no choice stored.
  *Breaks when:* the choice is applied by name for every kind.

- **INV-5** — `?source=S` serves only `(S, kind)`: 404 when it misses, is rate-limited or fails, with no fallback; 422 `media_source_unknown` when S is outside `chain_for(kind)`.
  *Test:* same file: S with no candidate while the chain has one → 404; S raising `MediaRateLimited` → 404; S = `nosuch` → 422; S = `wikipediaImage` with `kind=title` → 422.
  *Breaks when:* a miss falls back to the chain.

- **INV-6** — Without `further`, the candidates route calls `prepare` on a source in `LIMITED_SOURCES` only through the one `boxart` chain walk, which reaches a limited source only when every source before it misses `boxart`, or through resolving a stored choice from that source. With `further=true`, every ready limited source in the chain is asked for each kind it covers. `list_candidates` calls each source's `prepare` at most once.
  *Test:* `tests/media/test_mame_curator_1146_candidates.py`, with fake sources counting `prepare` calls: a free source holding `boxart` → limited counts stay 0; `ask_limited=True` → each limited source asked, with one `prepare` for a source covering three kinds. The route test adds a free source missing `boxart` → exactly one limited `prepare`; and a stored `(L, title)` choice from limited source L that resolves → exactly one `prepare` on L.
  *Breaks when:* the default list asks every source.

- **INV-7** — Candidates with equal bytes appear once, the earliest kept. The in-use picture is in the list, first, and is the only one marked `in_use`.
  *Test:* `test_mame_curator_1146_candidates.py`: two sources serving the same bytes → one candidate. The route test: an in-use picture from a limited source with `further=false` → listed first, marked.
  *Breaks when:* duplicates show twice, or the in-use picture is missing when it came from a skipped source.

- **INV-8** — A source that raises during the listing is named in `not_answered` and does not end the listing; each skipped limited source is named in `not_asked`.
  *Test:* `test_mame_curator_1146_candidates.py`: one source raising `MediaRateLimited`, one raising `MediaFetchError`, one free source answering → both named, the answer listed.
  *Breaks when:* an error is swallowed silently, or aborts the list.

- **INV-9** — The save accepts only a source in `chain_for(kind)` and fetches nothing. The clear removes the entry and is safe to repeat. Both run under `world_lock`.
  *Test:* `test_mame_curator_1146_picture_choice.py`: PUT `{"source": "nosuch", "kind": "boxart"}` → 422 and no file; PUT `{"source": "wikipediaImage", "kind": "snap"}` → 422; a valid PUT with a fake source whose `prepare` raises → 200, `prepare` never called; DELETE twice → 200 both times, `chosen: null`.
  *Breaks when:* the save resolves the pair, or accepts a source the card could never serve.

- **INV-10** — Export holds `pictures` exactly when a choice exists, and keeps every other key and value, `null`s included. Import of a bundle without `pictures` leaves no choices; with an invalid one, replies 422 and changes no file. Restore puts `pictures.json` back from a snapshot that covers it and leaves it alone otherwise.
  *Test:* `tests/api/test_mame_curator_1146_backup.py`: export with and without a choice, asserting a `null` config value survives; import a pre-1146 bundle fixture; import a full bundle whose `pictures` is `{"pictures": {"pacman": {"source": "esde"}}}` and compare every target's bytes before and after; restore an old and a new snapshot.
  *Breaks when:* export always sends the key, a `null` in `config` is dropped, or an invalid `pictures` writes the other files.

- **INV-11** — A card's image address is `/media/<name>/boxart` with no choice, and `/media/<name>/boxart?v=<source>.<kind>` with one. After a save or clear in the guide, the Library shows the new address without a reload.
  *Test:* `frontend/src/lib/__tests__/pictureSrc.test.ts`; `GameCard.test.tsx` and `AlternativesDrawer.test.tsx` assert the `img` `src`; the guide test asserts both queries are invalidated.
  *Breaks when:* a choice keeps the plain address, so the browser shows the cached old image.

- **INV-12** — The guide shows "What would you like to fix?" only for a game with several versions. It marks the in-use picture in text, offers "Use the usual picture" only when a choice is stored, offers "Look in more places" only when §4.6 says, and sends no request when the in-use picture is chosen. A failed save or clear says so in a `role="alert"` element and changes nothing.
  *Test:* `frontend/src/pages/__tests__/FixPicture.test.tsx`, with handlers for each reply.
  *Breaks when:* a one-version game shows the version choice, or a failure leaves the screen silently unchanged.

- **INV-13** — Trust boundary: `name`, `source` and the stored file are user input. `name` is only a key into `world.machines`; `source` is only a key into the registry. Neither becomes a path or a URL. `resolve_pair` keeps `resolve_image`'s rule that only the three local sources may answer `file://`, and the local folders' refusal of a path outside the folder.
  *Test:* `test_mame_curator_1146_candidates.py`: a fake network source answering `file:///etc/passwd` through `resolve_pair` → `None`. `test_mame_curator_1146_picture_choice.py`: PUT with `source` `../../etc` → 422.
  *Breaks when:* `resolve_pair` is written without the `_LOCAL_SOURCES` check.

## 6. Failure modes

- **The chosen source is removed from `media.sources`, loses its key, or its folder is unmounted:** the server falls back with `no-store` (INV-3). A browser that already holds the chosen picture keeps showing it until its cache expires. The guide says the choice cannot be found (§4.6). The choice stays stored, so it returns when the source does.
- **A source answers more slowly than the user waits:** the list shows nothing until every asked source finishes. The free sources are local folders and libretro; each network fetch is bounded by the shared `media_client`'s timeout.
- **A limited source is out of tokens:** it is named in `not_answered`; "Look in more places" stays offered.
- **A choice is stored for a game the DAT no longer has:** it stays in the file, unused. The routes 404 for that name.
- **Two tabs save at once:** `world_lock` orders them; the later wins, as for notes.
- **The write fails (disk full, read-only folder):** the route raises before swapping the world, so the choice in memory and on disk stay as they were. The guide shows the failed-save screen.
- **A newer backup holding choices is imported into an older release:** both `ConfigExportBundleSchema` and `ConfigExportBundle` refuse it, and nothing changes. A backup with no choices still loads there.
- **An old backup is imported after choices were made:** the choices are cleared. The snapshot taken first, listed in Settings, brings them back.
- **The upstream image changes behind the same URL:** the disk cache keeps the first copy, as today.

## 7. Tests

| Invariant | Test |
|---|---|
| INV-1, INV-2, INV-3, INV-4, INV-5, INV-9 | `tests/api/test_mame_curator_1146_picture_choice.py` |
| INV-6, INV-7, INV-8, INV-13 | `tests/media/test_mame_curator_1146_candidates.py`, plus the route cases in `test_mame_curator_1146_picture_choice.py` |
| INV-10 | `tests/api/test_mame_curator_1146_backup.py` |
| INV-11 | `frontend/src/lib/__tests__/pictureSrc.test.ts`, `GameCard.test.tsx`, `AlternativesDrawer.test.tsx` |
| INV-12 | `frontend/src/pages/__tests__/FixPicture.test.tsx` |

**Existing tests that change:** `makeGameCard` in `frontend/src/pages/__tests__/_libraryPageFixtures.tsx` and any other `GameCard` fixture gain `picture: null`. The version half's `AlternativesDrawer` test that hides the entry for one version reverses (§4.6). Export and import tests in `tests/api/test_routes_config.py` follow the routes to `routes/backup.py`.

Each new test must be seen to fail before its code exists.

## 8. Alternatives considered (and rejected)

- **Store the image URL.** Local sources answer `file://` URLs holding the user's own paths, and ArcadeDB's are redirector URLs. A `(source, kind)` pair survives a folder move or a re-scrape.
- **Copy the chosen image into a user folder.** Duplicates bytes, needs its own clean-up, and a backup would have to carry images.
- **Store the choice in `overrides.yaml`.** `Overrides` is the filter's input, read by `run_filter`. A picture does not change which game wins.
- **Let the card ask for the pair itself (`?source=`), with the server unaware of choices.** The fallback would need a second request from every caller, and each new caller would have to know about choices.
- **Drop the immutable cache header on `boxart`.** Every card would ask the server again on each page.
- **Ask every source on the first screen.** Spends MobyGames' and ArcadeDB's limits on every visit and makes the first screen slow.
- **Offer only the free sources.** Hides ArcadeDB, the only limited source with title and in-game pictures.
- **Check a save by fetching the pair.** Spends a token and a network wait inside a save, for a picture the user has just seen.
- **A separate picture guide.** The user asked for one wizard for "picture or version".
- **Always export `pictures`, and read its absence as "leave current choices".** Every new backup would then fail to open in an older release, and a backup would no longer restore the state it was taken from.

## 9. Out of scope

- Uploading your own picture — deferred; not yet queued.
- Choosing the pictures RetroArch shows in its playlist — deferred; not yet queued.
- Contributing pictures upstream — tracked by mame-curator-1007.
- Remembering that a game has no picture — tracked by mame-curator-1143.
- Choosing among several MobyGames covers; `_front_cover` keeps one — deferred; not yet queued.
- Choices for the `title` and `snap` addresses — deferred; not yet queued. Nothing in the app shows them.

## 10. What checks this

| Rule | What catches a breach |
|------|----------------------|
| INV-1 to INV-5, INV-9 | `test_mame_curator_1146_picture_choice.py` |
| INV-6 to INV-8, INV-13 | `test_mame_curator_1146_candidates.py` |
| INV-10 | `test_mame_curator_1146_backup.py` |
| INV-11 | `pictureSrc.test.ts`, `GameCard.test.tsx`, `AlternativesDrawer.test.tsx` |
| INV-12 | `FixPicture.test.tsx` |
| The real browser fetches a new picture after a choice | **nothing** automatic — jsdom has no HTTP cache; a manual check on the running app |
| Labels and large images read well for this user | **nothing** — only the user can judge this, on the running app |
| Real upstream sources answer as the fakes do | **nothing** — the tests use fake sources; a manual run of "Look in more places" on a real game |

## 11. Cross-doc impact

- `src/mame_curator/media/spec.md`: § Public functions gains `resolve_pair`, `resolve_image_found`, `list_candidates` and `LIMITED_SOURCES`.
- `src/mame_curator/api/spec.md`: § Route inventory gains the three routes and moves export and import to `routes/backup.py`; § Media proxy gains §4.3's table; § Config persistence + snapshots gains `pictures.json` for restore, import and export.
- `docs/standards/versioning-overrides.md`: no edit; item 2's grep finds the new file.
- `docs/help/02-choosing-games.md`: how to change a game's picture.
- `CHANGELOG.md`: a user-facing entry.

## 12. Cold-eyes loop log

Rows live in `../reviews/mame-curator-1146-picture-choice-loop-log.md`.

## 13. Resource cost

- `pictures.json` holds one small entry per chosen game, bounded by the DAT's machine count.
- Each save or clear writes one snapshot. `MAX_SNAPSHOTS` prunes the oldest, so a long run of picture choices can push out older settings snapshots, as override saves already do.
- Tokens: "Look in more places" costs at most one per limited source for the listing, and one more for a source holding the game's stored choice. Each preview from ArcadeDB or Wikipedia, and each card load of a choice from them, costs one more, because their `prepare` takes a token even on a cached lookup. MobyGames reads its cached lookup before taking a token (`MobyGamesSource._get_json`).
- Disk: previews the user does not choose stay in `media.cache_dir`, which has no eviction, as today.

## 14. Migration / compatibility

- No `pictures.json` → no choices. Nothing to migrate.
- A backup from before this release has no `pictures` key and imports as no choices.
- Under `versioning-overrides.md`, this is a MINOR change: an optional key, a new file, and an internal API change. The rule protects reading what an earlier release wrote. A newer backup with choices failing in an older release is a downgrade, which the rule does not cover; §4.7 keeps backups without choices readable there.
- `pictures.json` becomes a breaking surface from this release (item 2).

## 15. Open questions

None. The user answered the draft's four on 2026-11-10, each as recommended:

1. Importing an older backup clears picture choices; the snapshot taken first keeps them.
2. "Look in more places" asks the online sources with limits, one press away.
3. The entry link reads "Fix this game's picture or version, step by step".
4. A picture choice belongs to one version's short name and does not follow a version change. The guide says so (§4.6 step 2).
