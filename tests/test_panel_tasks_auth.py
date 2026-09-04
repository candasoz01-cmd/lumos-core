"""TD-24 Faz-2: panel tasks kimlik kütüphanesi (HTTP yok, Faz-1 dosyasına dokunmaz)."""

from __future__ import annotations

import pytest

from panel_tasks_auth import AuthError, PanelTasksAuth, pkce_challenge_s256, pkce_verifier


def test_missing_secret_is_fail_closed() -> None:
    auth = PanelTasksAuth(secret="")
    with pytest.raises(AuthError) as exc:
        auth.mint_service_token()
    assert exc.value.code == "missing_secret"
    with pytest.raises(AuthError) as exc:
        auth.authenticate({"Authorization": "Bearer x"})
    assert exc.value.code == "missing_secret"


def test_pkce_exchange_issues_bearer_and_rejects_replay() -> None:
    auth = PanelTasksAuth(secret="panel-secret")
    verifier = pkce_verifier()
    code = auth.mint_exchange_code(code_challenge=pkce_challenge_s256(verifier))
    session = auth.exchange(code=code, code_verifier=verifier)
    assert auth.authenticate({"Authorization": f"Bearer {session}"}) == "ok"
    assert auth.authenticate({"X-Kando-Token": session}) == "ok"
    with pytest.raises(AuthError) as exc:
        auth.exchange(code=code, code_verifier=verifier)
    assert exc.value.code == "replay"


def test_pkce_mismatch_does_not_consume_nothing_usable() -> None:
    auth = PanelTasksAuth(secret="panel-secret")
    verifier = pkce_verifier()
    code = auth.mint_exchange_code(code_challenge=pkce_challenge_s256(verifier))
    with pytest.raises(AuthError) as exc:
        auth.exchange(code=code, code_verifier="wrong-verifier-value-xxxxxxxx")
    assert exc.value.code == "pkce_mismatch"
    session = auth.exchange(code=code, code_verifier=verifier)
    auth.authenticate({"Authorization": f"Bearer {session}"})


def test_bearer_preferred_over_x_kando_token() -> None:
    auth = PanelTasksAuth(secret="panel-secret")
    good = auth.mint_service_token()
    other = auth.mint_service_token()
    auth.authenticate(
        {
            "Authorization": f"Bearer {good}",
            "X-Kando-Token": other,
        }
    )


def test_revoke_and_rotate() -> None:
    auth = PanelTasksAuth(secret="panel-secret")
    token = auth.mint_service_token()
    auth.revoke(token)
    with pytest.raises(AuthError) as exc:
        auth.authenticate({"X-Kando-Token": token})
    assert exc.value.code == "invalid_token"
    fresh = auth.mint_service_token()
    rotated = auth.rotate(fresh)
    with pytest.raises(AuthError):
        auth.authenticate({"Authorization": f"Bearer {fresh}"})
    auth.authenticate({"Authorization": f"Bearer {rotated}"})


def test_expired_exchange_rejected() -> None:
    clock = {"t": 1_000.0}

    def now() -> float:
        return clock["t"]

    auth = PanelTasksAuth(secret="s", now=now, exchange_ttl_s=10)
    verifier = pkce_verifier()
    code = auth.mint_exchange_code(code_challenge=pkce_challenge_s256(verifier))
    clock["t"] = 1_020.0
    with pytest.raises(AuthError) as exc:
        auth.exchange(code=code, code_verifier=verifier)
    assert exc.value.code == "invalid_token"


def test_expired_session_rejected() -> None:
    clock = {"t": 1_000.0}
    auth = PanelTasksAuth(secret="s", now=lambda: clock["t"], session_ttl_s=10)
    token = auth.mint_service_token()
    clock["t"] = 1_020.0
    with pytest.raises(AuthError) as exc:
        auth.authenticate({"X-Kando-Token": token})
    assert exc.value.code == "invalid_token"


def test_token_size_cap() -> None:
    auth = PanelTasksAuth(secret="s")
    huge = "a" * 600
    with pytest.raises(AuthError) as exc:
        auth.authenticate({"X-Kando-Token": huge})
    assert exc.value.code == "too_large"


def test_rate_limit_on_mint() -> None:
    auth = PanelTasksAuth(secret="s", rate_max=3, rate_window_s=60)
    for _ in range(3):
        auth.mint_service_token(rate_key="cli")
    with pytest.raises(AuthError) as exc:
        auth.mint_service_token(rate_key="cli")
    assert exc.value.code == "rate_limited"


def test_unknown_token() -> None:
    auth = PanelTasksAuth(secret="s")
    with pytest.raises(AuthError) as exc:
        auth.authenticate({"Authorization": "Bearer not-issued"})
    assert exc.value.code == "invalid_token"


def test_missing_header() -> None:
    auth = PanelTasksAuth(secret="s")
    with pytest.raises(AuthError) as exc:
        auth.authenticate({})
    assert exc.value.code == "invalid_token"
