"""Typed filter exceptions."""

from __future__ import annotations


class FilterError(Exception):
    """Base for all filter-related errors."""


class ConfigError(FilterError):
    """Invalid FilterConfig values."""


class OverridesError(FilterError):
    """Malformed overrides.yaml."""


class SessionsError(FilterError):
    """Malformed or empty session configuration."""
