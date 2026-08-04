"""`config.yaml` layer of `mame-curator serve`'s host/port resolution.

`tests/cli/test_serve_port_env.py` pins the flag and `$PORT` layers. This
module pins the one below them — `server:` in `config.yaml` — plus the
failure modes reading it introduces:

* Port: `--port` → `$PORT` → `server.port` → 8080, first present wins.
* Host: `--host` → `server.host` → `127.0.0.1`. No environment layer.
* The `server:` block is read **once and unconditionally**, so a malformed
  one fails the command even when every relevant flag was supplied.
* Only `server:` is parsed — a config whose *other* sections are invalid
  still starts.

The two `8080`-against-`9000` cases are the precedence-inversion
regression: an implementation that infers "nothing was set" from
`_resolve_port` returning `DEFAULT_PORT` passes every other case here and
still lets `server.port` beat an explicit `--port 8080`.

See `src/mame_curator/cli/spec.md` § "`serve` host, port and browser
resolution".
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from mame_curator.api.schemas import ServerConfig
from mame_curator.cli.commands.serve import DEFAULT_PORT, _cmd_serve


def _serve_args(
    config: Path,
    *,
    host: str | None = None,
    port: int | None = None,
    no_open_browser: bool = True,
) -> argparse.Namespace:
    """Build a `serve` Namespace.

    `no_open_browser` defaults to True here (unlike the argparse default):
    these tests mock `uvicorn.run`, so nothing ever binds, and a live
    browser poller would spend its full budget probing a port that some
    unrelated process on the developer's machine may well be serving.
    """
    return argparse.Namespace(config=config, host=host, port=port, no_open_browser=no_open_browser)


def _config(tmp_path: Path, body: str = "paths: {}\n") -> Path:
    config = tmp_path / "config.yaml"
    config.write_text(body)
    return config


def _serve(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    """Run `_cmd_serve` with the server mocked; return (rc, uvicorn kwargs)."""
    with (
        patch("mame_curator.api.create_app"),
        patch("uvicorn.run") as run_mock,
    ):
        rc = _cmd_serve(args)
    kwargs: dict[str, Any] = dict(run_mock.call_args.kwargs) if run_mock.call_args else {}
    return rc, kwargs


# ---- Port: the config layer and its precedence -----------------------


def test_config_port_is_used_when_nothing_else_is_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Layer 3 — `server.port` wins over the 8080 default."""
    monkeypatch.delenv("PORT", raising=False)
    _, kwargs = _serve(_serve_args(_config(tmp_path, "server: {port: 9000}\n")))
    assert kwargs["port"] == 9000


def test_flag_beats_config_port(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Layer 1 beats layer 3."""
    monkeypatch.delenv("PORT", raising=False)
    _, kwargs = _serve(_serve_args(_config(tmp_path, "server: {port: 9000}\n"), port=9500))
    assert kwargs["port"] == 9500


def test_env_beats_config_port(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Layer 2 beats layer 3."""
    monkeypatch.setenv("PORT", "9600")
    _, kwargs = _serve(_serve_args(_config(tmp_path, "server: {port: 9000}\n")))
    assert kwargs["port"] == 9600


def test_flag_equal_to_default_still_beats_config_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The precedence inversion — `--port 8080` is explicit, not absent.

    An implementation that re-reads `server.port` whenever `_resolve_port`
    returned `DEFAULT_PORT` cannot distinguish "no port was named" from
    "the port named happens to be 8080", and binds 9000 here.
    """
    monkeypatch.delenv("PORT", raising=False)
    _, kwargs = _serve(_serve_args(_config(tmp_path, "server: {port: 9000}\n"), port=DEFAULT_PORT))
    assert kwargs["port"] == DEFAULT_PORT


def test_env_equal_to_default_still_beats_config_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same inversion via the environment layer."""
    monkeypatch.setenv("PORT", str(DEFAULT_PORT))
    _, kwargs = _serve(_serve_args(_config(tmp_path, "server: {port: 9000}\n")))
    assert kwargs["port"] == DEFAULT_PORT


def test_server_block_without_port_falls_to_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Every `ServerConfig` field has its own default, so a partial block is valid."""
    monkeypatch.delenv("PORT", raising=False)
    _, kwargs = _serve(_serve_args(_config(tmp_path, "server: {host: 0.0.0.0}\n")))
    assert kwargs["port"] == DEFAULT_PORT


def test_default_port_tracks_server_config_default() -> None:
    """`DEFAULT_PORT` mirrors `ServerConfig.port`; nothing may drift them apart."""
    assert ServerConfig.model_fields["port"].default == DEFAULT_PORT


# ---- Host ------------------------------------------------------------


def test_config_host_is_used_when_flag_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("PORT", raising=False)
    _, kwargs = _serve(_serve_args(_config(tmp_path, "server: {host: 0.0.0.0}\n")))
    # S104: asserting how a wildcard is *resolved*; nothing here binds a socket.
    assert kwargs["host"] == "0.0.0.0"  # noqa: S104


def test_host_flag_beats_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PORT", raising=False)
    _, kwargs = _serve(_serve_args(_config(tmp_path, "server: {host: 0.0.0.0}\n"), host="10.0.0.1"))
    assert kwargs["host"] == "10.0.0.1"


def test_empty_host_flag_falls_through_to_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`--host ""` counts as absent, matching the previous `args.host or ...`."""
    monkeypatch.delenv("PORT", raising=False)
    _, kwargs = _serve(_serve_args(_config(tmp_path, "server: {host: 0.0.0.0}\n"), host=""))
    # S104: asserting how a wildcard is *resolved*; nothing here binds a socket.
    assert kwargs["host"] == "0.0.0.0"  # noqa: S104


def test_host_defaults_to_loopback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PORT", raising=False)
    _, kwargs = _serve(_serve_args(_config(tmp_path)))
    assert kwargs["host"] == "127.0.0.1"


# ---- Reading the block: the failures it introduces -------------------


def test_unreadable_config_exits_1_naming_the_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A directory where config.yaml should be — `exists()` passes, the read does not."""
    monkeypatch.delenv("PORT", raising=False)
    config = tmp_path / "config.yaml"
    config.mkdir()

    rc, kwargs = _serve(_serve_args(config))

    assert rc == 1
    assert not kwargs
    assert "config.yaml" in capsys.readouterr().err


def test_non_mapping_config_exits_1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PORT", raising=False)
    rc, _ = _serve(_serve_args(_config(tmp_path, "- a\n- b\n")))

    assert rc == 1
    assert "mapping" in capsys.readouterr().err


def test_unparseable_config_exits_1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PORT", raising=False)
    rc, _ = _serve(_serve_args(_config(tmp_path, "server: {port: [unclosed\n")))

    assert rc == 1
    assert "config.yaml" in capsys.readouterr().err


@pytest.mark.parametrize(
    "body",
    [
        'server: {port: "not-a-number"}\n',  # int coercion fails
        "server: {bogus_key: 1}\n",  # extra="forbid"
        "server: 3\n",  # not a mapping at all
    ],
)
def test_invalid_server_block_exits_1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], body: str
) -> None:
    monkeypatch.delenv("PORT", raising=False)
    rc, kwargs = _serve(_serve_args(_config(tmp_path, body)))

    assert rc == 1
    assert not kwargs, "a malformed server: block must not reach the bind"
    assert capsys.readouterr().err.strip(), "the failure must be reported, not silent"


def test_malformed_config_fails_even_when_every_flag_is_supplied(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The block is read unconditionally, not lazily when a layer is needed.

    Supplying `--host`, `--port` and `--no-open-browser` means nothing from
    the file would be consumed — and those scripted callers are exactly the
    ones whose config rots longest before anyone looks at it.
    """
    monkeypatch.delenv("PORT", raising=False)
    rc, kwargs = _serve(
        _serve_args(
            _config(tmp_path, "server: {bogus_key: 1}\n"),
            host="127.0.0.1",
            port=9000,
            no_open_browser=True,
        )
    )

    assert rc == 1
    assert not kwargs


def test_other_sections_may_be_invalid(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Only `server:` is parsed here — full validation is the API lifespan's job."""
    monkeypatch.delenv("PORT", raising=False)
    rc, kwargs = _serve(
        _serve_args(_config(tmp_path, "server: {port: 9001}\npaths: 3\nfilter: [nonsense]\n"))
    )

    assert rc != 1
    assert kwargs["port"] == 9001


# ---- The bind, and the errors it can raise ---------------------------


def test_out_of_range_resolved_port_exits_1_not_traceback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`socket.bind` raises `OverflowError`, which is not an `OSError`.

    Reachable from `--port 99999` and from a `server.port` of the same,
    neither of which is range-checked.
    """
    monkeypatch.delenv("PORT", raising=False)
    with (
        patch("mame_curator.api.create_app"),
        patch("uvicorn.run", side_effect=OverflowError("bind(): port must be 0-65535")),
    ):
        rc = _cmd_serve(_serve_args(_config(tmp_path), port=99999))

    assert rc == 1
    assert "99999" in capsys.readouterr().err


def test_config_sourced_out_of_range_port_exits_1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`server.port` is unconstrained too — the same catch has to cover it."""
    monkeypatch.delenv("PORT", raising=False)
    with (
        patch("mame_curator.api.create_app"),
        patch("uvicorn.run", side_effect=OverflowError("bind(): port must be 0-65535")),
    ):
        rc = _cmd_serve(_serve_args(_config(tmp_path, "server: {port: 99999}\n")))

    assert rc == 1


# ---- Error messages: every interpolated value survives rich markup ----


def test_config_not_found_path_survives_rich_markup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A path with brackets in it is named verbatim, not eaten as a style tag."""
    monkeypatch.delenv("PORT", raising=False)
    rc = _cmd_serve(_serve_args(tmp_path / "[abc].yaml"))

    assert rc == 1
    assert "[abc]" in capsys.readouterr().err


def test_bind_failure_message_survives_rich_markup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The exception text is user-facing input for markup purposes too."""
    monkeypatch.delenv("PORT", raising=False)
    with (
        patch("mame_curator.api.create_app"),
        patch("uvicorn.run", side_effect=OSError("address in use [abc]")),
    ):
        rc = _cmd_serve(_serve_args(_config(tmp_path)))

    assert rc == 1
    assert "[abc]" in capsys.readouterr().err


def test_create_app_failure_message_survives_rich_markup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PORT", raising=False)
    from mame_curator.api.errors import ConfigError

    with (
        patch("mame_curator.api.create_app", side_effect=ConfigError("bad [abc] value")),
        patch("uvicorn.run") as run_mock,
    ):
        rc = _cmd_serve(_serve_args(_config(tmp_path)))

    assert rc == 1
    run_mock.assert_not_called()
    assert "[abc]" in capsys.readouterr().err
