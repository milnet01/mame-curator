"""Typed API exceptions + FastAPI exception handler.

Per ``docs/specs/P04.md`` § Error envelope. ``ApiException`` is the throwable;
``ApiErrorBody`` is the wire shape rendered by the global handler.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


class FieldError(BaseModel):
    """One field-level validation error inside an ApiErrorBody."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    loc: str
    msg: str
    type: str


class ApiErrorBody(BaseModel):
    """Wire shape of every non-2xx response."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    detail: str
    code: str
    fields: tuple[FieldError, ...] = ()


class ApiException(Exception):
    """Base for all typed API exceptions; rendered into ApiErrorBody by the handler."""

    code: ClassVar[str] = "internal"
    status_code: ClassVar[int] = 500

    def __init__(self, detail: str, *, fields: tuple[FieldError, ...] = ()) -> None:
        """Build an ApiException with a single-line ``detail`` and optional field list."""
        super().__init__(detail)
        self.detail = detail
        self.fields = fields


class ConfigError(ApiException):
    """422 — config validation failed (PATCH /api/config, import, etc.)."""

    code = "config_invalid"
    status_code = 422


class FsSandboxError(ApiException):
    """403 — requested path is outside the allowlist."""

    code = "fs_sandboxed"
    status_code = 403


class FsAlreadyCoveredError(ApiException):
    """409 — granted path is already covered by an existing root."""

    code = "fs_already_covered"
    status_code = 409


class FsPathInvalidError(ApiException):
    """400 — empty / NUL-byte / non-directory path."""

    code = "fs_path_invalid"
    status_code = 400


class FsNotFoundError(ApiException):
    """404 — path does not exist on disk."""

    code = "fs_not_found"
    status_code = 404


class FsRootNotFoundError(ApiException):
    """404 — allowlist root id unknown."""

    code = "fs_root_not_found"
    status_code = 404


class FsConfigRootNotRevocableError(ApiException):
    """400 — config-derived roots cannot be deleted via the grant API."""

    code = "fs_config_root_not_revocable"
    status_code = 400


class JobAlreadyRunningError(ApiException):
    """409 — another copy job is already in flight."""

    code = "job_already_running"
    status_code = 409


class JobNotFoundError(ApiException):
    """404 — no active copy job for the requested operation."""

    code = "job_not_found"
    status_code = 404


class PlaylistConflictCancelledError(ApiException):
    """409 — CANCEL strategy aborted the start because a playlist exists."""

    code = "playlist_conflict_cancelled"
    status_code = 409


class SnapshotNotFoundError(ApiException):
    """404 — snapshot id unknown."""

    code = "snapshot_not_found"
    status_code = 404


class GameNotFoundError(ApiException):
    """404 — short_name not present in the loaded DAT."""

    code = "game_not_found"
    status_code = 404


class OverrideNotFoundError(ApiException):
    """404 — no override registered for the requested parent."""

    code = "override_not_found"
    status_code = 404


class SessionNotFoundError(ApiException):
    """404 — session name unknown."""

    code = "session_not_found"
    status_code = 404


class SessionNameInvalidError(ApiException):
    """422 — session name fails the leading-character regex."""

    code = "session_name_invalid"
    status_code = 422


class HelpTopicNotFoundError(ApiException):
    """404 — help topic slug unknown or path-traversal-shaped."""

    code = "help_topic_not_found"
    status_code = 404


class MediaKindInvalidError(ApiException):
    """400 — media kind not in the supported set."""

    code = "media_kind_invalid"
    status_code = 400


class MediaUpstreamError(ApiException):
    """502 — upstream libretro-thumbnails request failed."""

    code = "media_upstream_error"
    status_code = 502


class MediaUpstreamNotFoundError(ApiException):
    """404 — upstream returned 404 for the requested media."""

    code = "media_upstream_not_found"
    status_code = 404


def _render(exc: ApiException) -> JSONResponse:
    body = ApiErrorBody(detail=exc.detail, code=exc.code, fields=exc.fields)
    return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))


def install_handlers(app: FastAPI) -> None:
    """Register the global ApiException + fallback Exception handlers on the app."""

    async def _api_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        if not isinstance(exc, ApiException):  # pragma: no cover - guard
            raise exc
        return _render(exc)

    async def _fallback_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled API error", exc_info=exc)
        body = ApiErrorBody(detail="internal error", code="internal")
        return JSONResponse(status_code=500, content=body.model_dump(mode="json"))

    async def _validation_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        from fastapi.exceptions import RequestValidationError

        if not isinstance(exc, RequestValidationError):  # pragma: no cover - guard
            raise exc
        fields = tuple(
            FieldError(
                loc=".".join(str(p) for p in err["loc"] if p != "body"),
                msg=err.get("msg", ""),
                type=err.get("type", ""),
            )
            for err in exc.errors()
        )
        body = ApiErrorBody(
            detail="request validation failed",
            code="validation_error",
            fields=fields,
        )
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))

    app.add_exception_handler(ApiException, _api_exception_handler)
    app.add_exception_handler(Exception, _fallback_exception_handler)

    # FastAPI's default RequestValidationError handler returns the standard
    # `{detail: [...]}` shape; we override to return our envelope.
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(RequestValidationError, _validation_exception_handler)


def field_errors_from_pydantic(errors: Any) -> tuple[FieldError, ...]:
    """Convert Pydantic ``ValidationError.errors()`` output into FieldError tuple.

    Typed as ``Any`` because Pydantic v2's ``ErrorDetails`` TypedDict isn't
    re-exported from ``pydantic`` in a stable way; consumers always pass the
    direct return of ``exc.errors()``.
    """
    return tuple(
        FieldError(
            loc=".".join(str(p) for p in err["loc"]),
            msg=err.get("msg", ""),
            type=err.get("type", ""),
        )
        for err in errors
    )
