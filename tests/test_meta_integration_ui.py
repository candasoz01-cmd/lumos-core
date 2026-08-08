from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "ui/src/pages/integrations.astro"
PAGE = ROOT / "ui/src/pages/integrations/meta.astro"
START = ROOT / "api/auth/meta/start.js"
CALLBACK = ROOT / "api/auth/meta/callback.js"


def test_meta_catalog_entries_open_connection_status_surface():
    text = HUB.read_text(encoding="utf-8")
    for provider in ("whatsapp", "instagram", "facebook"):
        assert f'id: "{provider}"' in text
    assert text.count('href: "/integrations/meta"') == 3


def test_meta_status_surface_uses_only_existing_server_side_routes():
    text = PAGE.read_text(encoding="utf-8")
    assert '"/api/integrations/meta/token"' in text
    assert '"/api/integrations/meta/sync"' in text
    assert "/auth/meta/start?provider=" in text
    assert "access_token" not in text
    assert "vault_ref" not in text
    assert 'data-meta-action="sync"' in text
    assert 'data-meta-action="refresh"' in text
    assert 'data-meta-action="revoke"' in text


def test_meta_status_surface_keeps_external_writes_out_of_scope():
    text = PAGE.read_text(encoding="utf-8")
    assert "Mesaj gönderme veya yayınlama yetkisi içermez" in text
    assert 'method: "POST"' in text
    assert 'const endpoint = action === "sync" ? "/api/integrations/meta/sync" : "/api/integrations/meta/token"' in text


def test_meta_action_state_preserves_valid_connection_and_expiry():
    text = PAGE.read_text(encoding="utf-8")
    assert "const connected = state.connected ??" in text
    assert 'const canConnect = new Set(["notConnected", "revokedLocal"])' in text
    assert 'response.status === 401 ? "sessionRequired" : "actionFailed"' in text
    assert text.count("connected: prior?.connected") >= 3
    assert 'status: "unavailable", connected: prior?.connected' in text
    assert 'status: "synced", connected: true, expiresAt: prior?.expiresAt' in text


def test_meta_oauth_returns_to_status_surface():
    assert '"Location", `/integrations/meta?meta_error=' in START.read_text(encoding="utf-8")
    assert '"Location", `/integrations/meta?${query.toString()}`' in CALLBACK.read_text(encoding="utf-8")
