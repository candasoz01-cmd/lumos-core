"""bridge.llm observe-slice: dashboard-health-v1 mapping + unmeasured≠green."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from dashboard_health.bridge_llm import (
    CARD_ID,
    TTL_SECONDS,
    apply_freshness,
    card_from_http,
    pill_modifier,
    unprobed_card,
)

_NOW = datetime(2026, 8, 20, 9, 40, tzinfo=timezone.utc)
_REPO = Path(__file__).resolve().parents[1]


def test_unprobed_is_unknown_not_healthy() -> None:
    card = unprobed_card()
    assert card["id"] == CARD_ID
    assert card["state"] == "unknown"
    assert card["checked_at"] is None
    assert card["reason_code"] == "not_checked"
    assert pill_modifier(card["state"]) != "ready"


def test_200_ok_is_healthy() -> None:
    card = apply_freshness(card_from_http(200, {"status": "ok"}, fetched_at=_NOW), _NOW)
    assert card["state"] == "healthy"
    assert card["checked_at"] == "2026-08-20T09:40:00Z"
    assert card["evidence"].endswith("200")
    assert pill_modifier(card["state"]) == "ready"


def test_503_unconfigured_is_not_configured() -> None:
    card = apply_freshness(
        card_from_http(503, {"status": "unconfigured"}, fetched_at=_NOW), _NOW
    )
    assert card["state"] == "not_configured"
    assert card["reason_code"] == "unconfigured"
    assert pill_modifier(card["state"]) == "off"


def test_401_is_unknown_not_failed() -> None:
    card = apply_freshness(card_from_http(401, {"error": "unauthorized"}, fetched_at=_NOW), _NOW)
    assert card["state"] == "unknown"
    assert card["reason_code"] == "unauthorized"
    assert pill_modifier(card["state"]) != "ready"


def test_controlled_500_is_failed_without_credentials() -> None:
    card = apply_freshness(card_from_http(500, {"error": "boom"}, fetched_at=_NOW), _NOW)
    assert card["state"] == "failed"
    assert card["reason_code"] == "probe_rejected"
    assert pill_modifier(card["state"]) == "failed"


def test_network_miss_is_unknown_null_checked_at() -> None:
    card = apply_freshness(card_from_http(None, None, fetched_at=_NOW), _NOW)
    assert card["state"] == "unknown"
    assert card["checked_at"] is None
    assert card["reason_code"] == "probe_unreachable"


def test_unmapped_200_is_unknown_never_healthy() -> None:
    card = apply_freshness(card_from_http(200, {"status": "weird"}, fetched_at=_NOW), _NOW)
    assert card["state"] == "unknown"
    assert card["reason_code"] == "unmapped_value"
    assert pill_modifier(card["state"]) != "ready"


def test_freshness_expires_to_stale_keeps_last_known() -> None:
    probed = card_from_http(200, {"status": "ok"}, fetched_at=_NOW)
    later = apply_freshness(probed, _NOW + timedelta(seconds=TTL_SECONDS + 1))
    assert later["state"] == "stale"
    assert later["last_known"] == "healthy"
    assert later["reason_code"] == "freshness_expired"
    still = apply_freshness(probed, _NOW + timedelta(seconds=TTL_SECONDS - 1))
    assert still["state"] == "healthy"


def test_failed_freshness_expires_keeps_last_known_failed() -> None:
    probed = card_from_http(500, {"error": "boom"}, fetched_at=_NOW)
    later = apply_freshness(probed, _NOW + timedelta(seconds=TTL_SECONDS + 1))
    assert later["state"] == "stale"
    assert later["last_known"] == "failed"


def test_pill_modifiers_are_unique() -> None:
    mods = {state: pill_modifier(state) for state in (
        "not_configured", "unknown", "healthy", "failed", "stale"
    )}
    assert len(set(mods.values())) == 5
    assert mods["not_configured"] != mods["unknown"]
    assert mods["healthy"] == "ready"
    assert mods["stale"] != mods["healthy"]


def test_healthy_without_checked_at_cannot_stay_green() -> None:
    fake = unprobed_card()
    fake["state"] = "healthy"
    out = apply_freshness(fake, _NOW)
    assert out["state"] == "unknown"
    assert out["checked_at"] is None


def test_panel_wires_only_bridge_llm_card() -> None:
    astro = (_REPO / "ui/src/pages/panel.astro").read_text(encoding="utf-8")
    assert astro.count('data-health-card="bridge.llm"') == 1
    assert astro.count("data-health-card=") == 1
    assert 'data-health-state="unknown"' in astro
    assert 'lumos-status-pill--unknown' in astro
    assert "BridgeLlmHealthCard" in astro
    sohbet = astro.split('data-module="sohbet"', 1)[1].split("</button>", 1)[0]
    assert "lumos-status-pill--ready" not in sohbet
    assert 'data-i18n="panel.health.bridgeLlm.unknown"' in sohbet
    gorevler = astro.split('data-module="gorevler"', 1)[1].split("</button>", 1)[0]
    assert "lumos-status-pill--ready" in gorevler
    root = astro.split('id="panel-root-status"', 1)[1].split("</details>", 1)[0]
    assert "data-health-card" not in root


def test_health_i18n_keys_live_at_panel_root() -> None:
    tr = (_REPO / "ui/src/i18n/messages/panel/tr.ts").read_text(encoding="utf-8")
    en = (_REPO / "ui/src/i18n/messages/panel/en.ts").read_text(encoding="utf-8")
    for text in (tr, en):
        assert "health: {" in text
        assert "bridgeLlm:" in text
        assert "neverChecked:" in text
        assert "healthyAria:" in text
    assert "◌ Bilinmiyor — hiç kontrol edilmedi" in tr
    assert "⚪ Kurulmadı" in tr
    assert "◌ Unknown — never checked" in en
    assert "⚪ Not configured" in en


def test_observe_card_does_not_drive_header_or_conn_badge() -> None:
    card = (_REPO / "ui/src/components/panel/BridgeLlmHealthCard.astro").read_text(
        encoding="utf-8"
    )
    assert "panel-root-status" not in card
    assert "panel-conn-badge" not in card
    assert "data-health-card" in card


def test_js_mapper_stays_in_lockstep() -> None:
    js = (_REPO / "ui/src/lib/dashboard-health/bridge-llm.js").read_text(encoding="utf-8")
    py = (_REPO / "src/dashboard_health/bridge_llm.py").read_text(encoding="utf-8")
    assert 'export const CARD_ID = "bridge.llm"' in js
    assert "export const TTL_SECONDS = 120" in js
    assert "unmeasured must not render healthy" in js
    assert "ttlSeconds" not in js
    assert 'CARD_ID = "bridge.llm"' in py
    assert "checked_at" in py
    card_py = py.split("def unprobed_card", 1)[1].split("def card_from_http", 1)[0]
    assert "datetime.now" not in card_py
    assert "now()" not in card_py