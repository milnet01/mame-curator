"""Media-source protocol + concrete implementations for the P10 fallback chain.

Per ``docs/specs/P10.md`` § "Public API" + § "Source contracts". Chunk 2
lands the protocol, the ``Kind`` literal, and ``LibretroSource`` (the
P05 baseline carried under the new shape). Chunk 3b adds
``ProgettoSnapsSource`` (file:// model, snap kind only — upstream no
longer publishes flyers / titles; see 2026-05-18 spec amendment).
Later chunks add ``ArcadeDBSource``, ``WikipediaImageSource``,
``MobyGamesSource``.

Every concrete source implements two methods:

- ``async prepare(machine, *, client)`` — populate any per-machine lookup
  state the source needs (two-step sources hit JSON endpoints here).
  Single-shot sources implement it as a one-line ``return``. The
  Protocol's ``...`` body is a typing stub, not an inheritable default.
- ``def url_for(machine, kind)`` — sync. Returns the candidate URL for
  ``(machine, kind)`` or ``None`` if the source has no candidate for
  this lookup (distinct from a 404 at fetch time).

Sources also carry an instance-level ``disabled_reason: str | None``;
the orchestrator's registry filters out sources where it's non-None
so the readiness endpoint can surface the reason to the UI without
ever attempting a fetch.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Literal, Protocol, runtime_checkable

import httpx

from mame_curator.media.urls import urls_for
from mame_curator.parser.models import Machine

# The source-chain kind vocabulary. Excludes ``video`` deliberately —
# ``MediaUrls`` has no video field (P05 spec § "class MediaUrls"), so no
# source can ever cover that kind. The route's ``_VALID_KINDS`` set
# (which includes ``video``) is the user-input gate, not the source-chain
# vocabulary; the two are separate by design.
Kind = Literal["boxart", "title", "snap"]


@runtime_checkable
class MediaSource(Protocol):
    """Common shape every source in ``media.sources`` implements.

    ``@runtime_checkable`` lets the registry call ``isinstance(x, MediaSource)``
    at registration time — per PEP 544 this verifies attribute presence
    only (the four names below exist on the object), not method signatures
    or ``ClassVar`` types. Signature correctness is enforced by ``mypy`` at
    build time; the runtime check is defence-in-depth against truly-
    malformed extensions, not a typed contract.
    """

    name: ClassVar[str]
    license_compatible: ClassVar[bool]
    kinds: ClassVar[frozenset[Kind]]

    disabled_reason: str | None
    """Non-None means the source is gated off — registry filters it out
    of the fallback chain; readiness endpoint surfaces the string to UI.
    """

    async def prepare(self, machine: Machine, *, client: httpx.AsyncClient) -> None:
        """Populate any per-machine lookup state the source needs."""
        ...

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        """Return the candidate URL for ``(machine, kind)``, or ``None``."""
        ...


class LibretroSource:
    """libretro-thumbnails MAME catalog — the P05 baseline.

    No per-machine lookup; ``prepare`` is a one-line no-op. ``url_for``
    delegates to ``urls_for(machine)`` (the existing P05 helper) and
    returns the URL matching the requested kind. ``disabled_reason``
    is permanently ``None`` — this source has no config that could
    be missing.
    """

    name: ClassVar[str] = "libretro"
    license_compatible: ClassVar[bool] = True
    kinds: ClassVar[frozenset[Kind]] = frozenset({"boxart", "title", "snap"})

    def __init__(self) -> None:
        """Construct a LibretroSource. No config to read — never disabled."""
        self.disabled_reason: str | None = None

    async def prepare(
        self,
        machine: Machine,
        *,
        client: httpx.AsyncClient,
    ) -> None:
        """No-op: libretro is a direct-URL source with no per-machine state."""
        return

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        """Return the libretro thumbnail URL for ``kind`` on ``machine``.

        Always returns a string (every kind is covered); the ``str | None``
        in the signature exists for sources that may not have a candidate.
        """
        urls = urls_for(machine)
        # MediaUrls has exactly ``boxart`` / ``title`` / ``snap`` attributes
        # by construction (P05 spec). ``Kind`` is the exact same set.
        url: str = getattr(urls, kind)
        return url


# P10 chunk 3b — progettoSnaps local-pack source. Snap kind only; flyers
# and titles aren't published upstream anymore (see 2026-05-18 spec
# amendment in ``docs/specs/P10.md`` § "1. progettoSnaps — local pack
# model"). The pack is downloaded by ``mame-curator refresh-snaps``
# (chunk 3a) into ``<dest>/snap/<name>.png``.


class ProgettoSnapsSource:
    """Serves progettoSnaps snap PNGs from a local pack directory.

    Never hits the network; ``prepare`` is a no-op. ``url_for`` returns a
    ``file://`` URL when ``<snap_dir>/<machine.name>.png`` exists, else
    ``None``. The orchestrator's ``file://`` short-circuit (P10 spec §
    "Orchestrator amendment") returns the path directly without routing
    through ``fetch_with_cache`` (whose ``_ALLOWED_URL_SCHEMES`` guard
    rejects ``file://`` by design).

    ``disabled_reason`` is set at construction if ``snap_dir`` doesn't
    exist or is empty — the registry filters disabled sources out of the
    chain, and the readiness endpoint surfaces the reason to the UI as
    a prompt to run ``mame-curator refresh-snaps``.

    Existence checks against per-machine PNGs are cached on the instance
    so repeated ``url_for`` calls within one request don't ``stat()``
    repeatedly. Cache lifetime matches the per-request source-instance
    model (see § Architecture notes).
    """

    name: ClassVar[str] = "progettoSnaps"
    license_compatible: ClassVar[bool] = True
    kinds: ClassVar[frozenset[Kind]] = frozenset({"snap"})

    _DISABLED_REASON = (
        "Pack not downloaded. Run `mame-curator refresh-snaps` to fetch "
        "the latest progettoSnaps snap pack."
    )

    def __init__(self, *, snap_dir: Path) -> None:
        """Bind the source to ``snap_dir`` (typically ``data/snaps/snap``).

        Construction probes the directory once; if absent or empty, the
        source self-disables via ``disabled_reason``. The path is
        resolved to an absolute form so the produced ``file://`` URLs are
        unambiguous regardless of the caller's CWD.
        """
        self._snap_dir = snap_dir.resolve() if snap_dir.exists() else snap_dir
        self._present: set[str] = set()
        self._missing: set[str] = set()

        if not snap_dir.exists() or not any(snap_dir.iterdir()):
            self.disabled_reason: str | None = self._DISABLED_REASON
        else:
            self.disabled_reason = None

    async def prepare(
        self,
        machine: Machine,
        *,
        client: httpx.AsyncClient,
    ) -> None:
        """No-op: progettoSnaps is a disk-only source."""
        return

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        """Return ``file://<abs-snap_dir>/<machine.name>.png`` if present.

        Returns ``None`` when ``kind != "snap"`` (this source only covers
        snap), or when the file isn't on disk for this machine.
        """
        if kind != "snap":
            return None

        name = machine.name
        if name in self._missing:
            return None

        if name not in self._present:
            candidate = self._snap_dir / f"{name}.png"
            if candidate.is_file():
                self._present.add(name)
            else:
                self._missing.add(name)
                return None

        return (self._snap_dir / f"{name}.png").as_uri()
