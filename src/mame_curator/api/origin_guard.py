"""Cross-site request guard (mame-curator-1083).

The API binds 127.0.0.1 and authenticates nothing, so the residual risk
is a hostile page in the user's own browser: a cross-site request that
changes state (CSRF), or a hostile domain re-pointed at 127.0.0.1 so the
browser treats it as same-origin (DNS rebinding). Contract:
``api/spec.md`` § Cross-site guard.

Only browser requests are judged — those carrying ``Origin`` or
``Sec-Fetch-Site``. The CLI, curl and test clients send neither and
pass untouched.

A pure ASGI middleware rather than ``BaseHTTPMiddleware``, which buffers
responses and would stall the SSE progress stream.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Receive, Scope, Send

from mame_curator.api.errors import CrossSiteBlockedError, render_error

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_LOOPBACK_NAMES = frozenset({"localhost"})
# `none` is a URL the user typed or bookmarked, not a page's request.
_ALLOWED_FETCH_SITES = frozenset({"same-origin", "none"})


def _hostname(authority: str) -> str | None:
    """`host[:port]` or a full origin URL → lower-cased hostname, IPv6 unbracketed."""
    if "//" not in authority:
        authority = "//" + authority
    try:
        return urlsplit(authority).hostname
    except ValueError:
        return None


def _ip(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None


class OriginGuard:
    """Refuse browser requests that come from another site or a rebound name."""

    def __init__(self, app: ASGIApp, *, bind_host: str | None = None) -> None:
        """Wrap ``app``; ``bind_host`` is the address ``serve`` listens on, also trusted."""
        self.app = app
        self._bind_host = _hostname(bind_host) if bind_host else None

    def _is_local(self, hostname: str | None) -> bool:
        if hostname is None:
            return False
        if hostname in _LOOPBACK_NAMES or hostname == self._bind_host:
            return True
        ip = _ip(hostname)
        return ip is not None and ip.is_loopback

    def _refusal(self, headers: dict[str, str], method: str) -> str | None:
        """Why this request is refused, or ``None`` to let it through."""
        origin = headers.get("origin")
        fetch_site = headers.get("sec-fetch-site")
        if origin is None and fetch_site is None:
            return None  # not a browser
        host = _hostname(headers.get("host", ""))
        # DNS rebinding needs a NAME; an IP literal cannot be re-pointed.
        if not (self._is_local(host) or (host is not None and _ip(host) is not None)):
            return f"Refused a browser request addressed to host {headers.get('host')!r}."
        if method not in _UNSAFE_METHODS:
            return None  # a cross-site read cannot see the response without CORS
        if origin is not None:
            origin_host = _hostname(origin)  # "null" parses to an untrusted name
            if origin_host is not None and (self._is_local(origin_host) or origin_host == host):
                return None
            return f"Refused a change requested by another site ({origin!r})."
        if fetch_site not in _ALLOWED_FETCH_SITES:
            return f"Refused a change requested by another site (Sec-Fetch-Site {fetch_site!r})."
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI entry point."""
        if scope["type"] == "http":
            headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]}
            reason = self._refusal(headers, scope["method"])
            if reason is not None:
                await render_error(CrossSiteBlockedError(reason))(scope, receive, send)
                return
        await self.app(scope, receive, send)
