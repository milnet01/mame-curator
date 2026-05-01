"""L15 — paths in responses are safe (repr-quoted across error paths).

Per ``docs/specs/P04.md`` § Tests L15: continuation of the FP06–FP08
contract — every user-controlled string in error bodies is interpolated via
``repr()`` so control bytes can't spoof error messages or break JSON.
"""

from __future__ import annotations

from typing import Any


def test_paths_in_responses_are_safe(client: Any) -> None:
    """L15 — error-detail strings have no literal LF / control chars in them."""
    # Trigger several error paths with control-char-laden inputs.
    # NB: control chars must be percent-encoded in the URL — httpx (and the
    # WSGI/ASGI URL parser the TestClient delegates to) rejects raw `\n`
    # before the request reaches the server. The bytes still arrive at the
    # handler decoded back to `\n`; the assertion is that the resulting
    # error body never contains a literal LF.
    cases = [
        ("/api/fs/list?path=/etc/with%0Anewline", 403),  # fs_sandboxed
        ("/api/games/with%0Anewline_name", 404),  # game_not_found
        ("/api/help/UPPERCASE", 404),  # help_topic_not_found
    ]
    for url, expected_status in cases:
        response = client.get(url)
        assert response.status_code == expected_status
        body = response.json()
        # Detail must be a single line — no embedded literal LF in raw JSON value.
        assert "\n" not in body["detail"], f"unsafe LF in error detail for {url!r}"
        # Code must be non-empty and machine-readable.
        assert body["code"], "error envelope missing code"


def test_session_name_validation_quotes_input(client: Any) -> None:
    """L15 (variant) — invalid session name with control char is repr-quoted."""
    response = client.post(
        "/api/sessions",
        json={
            "name": "bad\nname",
            "session": {"include_genres": ["X"]},
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "\n" not in detail, "session-name validation must repr-quote input"
