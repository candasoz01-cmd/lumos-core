"""PR-006 dry-run: chat sentence → catalog envelope, claim fields, DOKUNMA reject."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.platform_task_envelope import (
    CATALOG,
    EVIDENCE_KIND_INFORMATION,
    IOS_LOGO_ENVELOPE,
    IOS_LOGO_PIPELINE_FILES,
    IOS_LUMOS_REPO,
    LUMOS_CORE_SOURCE_MARK,
    STEP_WRITE_LOCAL,
    EnvelopeRejected,
    assert_paths_allowed,
    claim_fields,
    format_work_packet,
    ios_logo_scopes,
    lumos_checkout_root,
    parse_ios_logo_scopes_from_lumos,
    resolve_platform_task,
)
from lumos_board.coordination_gateway import EventKind
from lumos_board.task_claim import TaskClaimStore
from policy.confirmation_policy import REQUIRES_CONFIRMATION_ACTIONS
from task_engine.profiles import STEP_TYPE_WRITE_LOCAL


ACCEPT_CHAT = "iOS logosunu ChatLumos işaretine çek"
ROOT = Path(__file__).resolve().parents[1]
FAKE_RESOURCES = "Resources/Assets.xcassets"


def test_catalog_has_only_ios_logo() -> None:
    assert tuple(CATALOG) == ("ios-logo",)


def test_accept_chat_maps_to_ios_logo_claim_fields() -> None:
    decision = resolve_platform_task(ACCEPT_CHAT)
    assert decision.matched
    envelope = decision.envelope
    assert envelope is not None
    assert envelope.task_key == "ios-logo"
    assert envelope.repo == "candasoz01-cmd/Lumos"
    assert envelope.repo == IOS_LUMOS_REPO
    assert FAKE_RESOURCES not in envelope.scopes
    assert all("Resources/Assets.xcassets" not in scope for scope in envelope.scopes)
    assert all("apple-touch" not in scope.lower() for scope in envelope.scopes)
    assert all("launch" not in scope.lower() for scope in envelope.scopes)
    assert envelope.scopes == ios_logo_scopes()
    assert envelope.scopes
    assert all(scope.startswith("ios/") or scope.endswith("chat-lumos-mark.svg") for scope in envelope.scopes)
    fields = claim_fields(envelope)
    assert fields["task_id"] == "ios-logo"
    assert fields["repo"] == "candasoz01-cmd/Lumos"
    assert fields["scopes"] == list(envelope.scopes)


def test_work_packet_matches_code_scope_and_excludes_apple_touch_launch() -> None:
    packet = format_work_packet(IOS_LOGO_ENVELOPE)
    assert packet.startswith("HEDEF:")
    assert "KAPSAM:" in packet
    assert "DOKUNMA:" in packet
    assert "KANIT:" in packet
    assert "AppIcon" in packet
    assert LUMOS_CORE_SOURCE_MARK in packet
    assert "candasoz01-cmd/Lumos" in packet
    for rel in IOS_LOGO_PIPELINE_FILES[:3]:
        assert rel in packet
    assert "apple-touch web varlığıdır" in packet
    assert "ayrı platform anahtarı" in packet
    assert "Resources/Assets.xcassets" not in packet
    assert "Swift" in packet
    assert "conductor" in packet
    assert "Network" in packet
    assert ".github" in packet
    assert "lumos-tree-logo" in packet
    assert "INFORMATION" in packet
    assert "RESULT" in packet


def test_evidence_reuses_information_user_relevant_not_result() -> None:
    assert IOS_LOGO_ENVELOPE.evidence_kind == EventKind.INFORMATION.value
    assert IOS_LOGO_ENVELOPE.evidence_kind == EVIDENCE_KIND_INFORMATION
    assert IOS_LOGO_ENVELOPE.user_relevant is True
    assert IOS_LOGO_ENVELOPE.evidence_kind != EventKind.RESULT.value


def test_risk_reuses_existing_write_local_and_cu4() -> None:
    assert IOS_LOGO_ENVELOPE.risk_step == STEP_TYPE_WRITE_LOCAL
    assert IOS_LOGO_ENVELOPE.confirmation_action_key == STEP_WRITE_LOCAL
    assert IOS_LOGO_ENVELOPE.confirmation_action_key in REQUIRES_CONFIRMATION_ACTIONS


def test_claim_fields_are_accepted_by_existing_store(tmp_path: Path) -> None:
    envelope = IOS_LOGO_ENVELOPE
    store = TaskClaimStore(tmp_path)
    fields = claim_fields(envelope)
    claim = store.claim(
        task_id=str(fields["task_id"]),
        repo=str(fields["repo"]),
        branch="cursor/ios-logo-dry-run",
        worktree="/worktrees/ios-logo",
        owner="ios-github-agent",
        scopes=list(envelope.scopes),
    )
    assert claim.accepted
    assert claim.claim is not None
    assert claim.claim.repo == "candasoz01-cmd/Lumos"
    assert FAKE_RESOURCES not in claim.claim.scopes


def test_generated_appicon_path_is_allowed() -> None:
    scope = IOS_LOGO_ENVELOPE.scopes[0]
    assert_paths_allowed([f"{scope}/AppIcon-1024.png"], IOS_LOGO_ENVELOPE)


def test_swift_conductor_network_workflow_and_brand_are_dokunma() -> None:
    with pytest.raises(EnvelopeRejected, match="DOKUNMA"):
        assert_paths_allowed(["App/UI/SplashView.swift"], IOS_LOGO_ENVELOPE)
    with pytest.raises(EnvelopeRejected, match="DOKUNMA"):
        assert_paths_allowed(["App/AI/Conductor.swift"], IOS_LOGO_ENVELOPE)
    with pytest.raises(EnvelopeRejected, match="DOKUNMA"):
        assert_paths_allowed(["App/Network/Client.swift"], IOS_LOGO_ENVELOPE)
    with pytest.raises(EnvelopeRejected, match="DOKUNMA"):
        assert_paths_allowed([".github/workflows/ios.yml"], IOS_LOGO_ENVELOPE)
    with pytest.raises(EnvelopeRejected, match="DOKUNMA"):
        assert_paths_allowed(["ui/public/lumos-tree-logo.svg"], IOS_LOGO_ENVELOPE)
    with pytest.raises(EnvelopeRejected, match="kapsam dışı|DOKUNMA"):
        assert_paths_allowed(
            ["Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png"],
            IOS_LOGO_ENVELOPE,
        )
    with pytest.raises(EnvelopeRejected, match="kapsam dışı|DOKUNMA"):
        assert_paths_allowed(
            ["Resources/Assets.xcassets/LaunchImage.imageset/launch.png"],
            IOS_LOGO_ENVELOPE,
        )
    with pytest.raises(EnvelopeRejected, match="kapsam dışı|DOKUNMA"):
        assert_paths_allowed(["ios/App/UI/ChatShellView.swift"], IOS_LOGO_ENVELOPE)


def test_apple_touch_is_web_not_ios_appicon() -> None:
    index = (ROOT / "ui" / "src" / "pages" / "index.astro").read_text(encoding="utf-8")
    panel = (ROOT / "ui" / "src" / "pages" / "panel.astro").read_text(encoding="utf-8")
    assert 'rel="apple-touch-icon"' in index
    assert 'href="/chat-lumos-mark.svg"' in index
    assert 'rel="apple-touch-icon"' in panel
    mark = ROOT / "ui" / "public" / "chat-lumos-mark.svg"
    assert mark.is_file()
    assert not (ROOT / "Resources" / "Assets.xcassets").exists()
    assert not (ROOT / "Resources" / "apple-touch-icon.png").exists()
    assert resolve_platform_task("apple-touch-icon güncelle").status == "STOP"


def test_unknown_platform_and_questions_stop() -> None:
    assert resolve_platform_task("Drive'da dosyayı paylaş").status == "STOP"
    assert resolve_platform_task("GitHub'da PR aç").status == "STOP"
    assert resolve_platform_task("logo değiştir").status == "STOP"
    assert resolve_platform_task("neden iOS logosu böyle?").status == "STOP"
    assert resolve_platform_task("").status == "STOP"
    assert resolve_platform_task("iOS uygulamasında sohbeti düzelt").status == "STOP"


def test_english_ios_logo_matches() -> None:
    decision = resolve_platform_task("change the iOS app icon to ChatLumos")
    assert decision.matched
    assert decision.envelope is not None
    assert decision.envelope.task_key == "ios-logo"
    assert decision.envelope.repo == IOS_LUMOS_REPO


def test_lumos_pipeline_scopes_when_checkout_present(tmp_path: Path) -> None:
    (tmp_path / "ios").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "ios" / "README.md").write_text(
        "AppIcon lives in ios/Lumos/Assets.xcassets/AppIcon.appiconset\n"
        "apple-touch is web; not this catalog.\n",
        encoding="utf-8",
    )
    (tmp_path / "scripts" / "build_ios_logo_assets.py").write_text(
        'OUT = "ios/Lumos/Assets.xcassets/AppIcon.appiconset"\n'
        'SOURCE = "ios/brand/chat-lumos-mark.svg"\n',
        encoding="utf-8",
    )
    (tmp_path / "scripts" / "sync_ios_assets.py").write_text(
        'DEST = "ios/Lumos/Assets.xcassets/AppIcon.appiconset"\n',
        encoding="utf-8",
    )
    (tmp_path / "Makefile").write_text("ios-logo:\n\tpython3 scripts/build_ios_logo_assets.py\n", encoding="utf-8")
    parsed = parse_ios_logo_scopes_from_lumos(tmp_path)
    assert "ios/Lumos/Assets.xcassets/AppIcon.appiconset" in parsed
    assert "ios/brand/chat-lumos-mark.svg" in parsed
    assert all("Resources/Assets.xcassets" not in item for item in parsed)
    assert all("apple-touch" not in item for item in parsed)
    live = ios_logo_scopes(lumos_root=tmp_path)
    assert live == parsed


def test_product_rules_table_matches_envelope() -> None:
    text = (ROOT / "docs" / "product-rules.md").read_text(encoding="utf-8")
    assert "candasoz01-cmd/Lumos" in text
    assert "uydurma" in text
    assert "| `Resources/Assets.xcassets" not in text
    assert "apple-touch" in text
    for scope in IOS_LOGO_ENVELOPE.scopes:
        assert scope in text
    checkout = lumos_checkout_root()
    if checkout is not None:
        assert (checkout / "scripts" / "build_ios_logo_assets.py").is_file()
