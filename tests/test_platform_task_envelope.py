"""PR-006 frozen iOS logo catalog and confirmation-policy tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.platform_task_envelope import (
    CATALOG,
    EVIDENCE_KIND_INFORMATION,
    IOS_LOGO_BACKUP_INPUT,
    IOS_LOGO_ENVELOPE,
    IOS_LOGO_PRODUCTION_INPUT,
    IOS_LOGO_SCOPES,
    IOS_LOGO_TARGET_MARK,
    IOS_LUMOS_REPO,
    STEP_WRITE_LOCAL,
    EnvelopeRejected,
    assert_paths_allowed,
    claim_fields,
    format_work_packet,
    resolve_platform_task,
)
from lumos_board.coordination_gateway import EventKind
from lumos_board.task_claim import TaskClaimStore
from policy.confirmation_policy import REQUIRES_CONFIRMATION_ACTIONS
from task_engine.profiles import STEP_TYPE_WRITE_LOCAL

ACCEPT_CHAT = "iOS logosunu ChatLumos işaretine çek"
ROOT = Path(__file__).resolve().parents[1]
FROZEN_REPO = "candasoz01-cmd/Lumos"
FROZEN_SCOPES = (
    "brand/ios-export/Assets.xcassets/AppIcon.appiconset",
    "ios/LumosApp/Assets.xcassets/AppIcon.appiconset",
)
NON_APPICON_PATHS = (
    "brand/source/logo001.png",
    "web/static/brand/logo001.png",
    "ui/public/chat-lumos-mark.svg",
    "ios/Assets.xcassets/AppIcon.appiconset",
    "ios/LumosApp/Assets.xcassets/LaunchImage.imageset",
    "Resources/Assets.xcassets/AppIcon.appiconset",
    "ios/LumosApp/NetworkClient.swift",
    ".github/workflows/ios-appstore.yml",
)


def test_catalog_has_only_ios_logo() -> None:
    assert tuple(CATALOG) == ("ios-logo",)


def test_frozen_repo_and_appicon_scopes() -> None:
    assert IOS_LUMOS_REPO == FROZEN_REPO
    assert IOS_LOGO_SCOPES == FROZEN_SCOPES
    assert IOS_LOGO_ENVELOPE.repo == FROZEN_REPO
    assert IOS_LOGO_ENVELOPE.scopes == FROZEN_SCOPES
    decision = resolve_platform_task(ACCEPT_CHAT)
    assert decision.matched
    envelope = decision.envelope
    assert envelope is not None
    assert envelope is IOS_LOGO_ENVELOPE
    assert envelope.repo == FROZEN_REPO
    assert envelope.scopes == FROZEN_SCOPES
    fields = claim_fields(envelope)
    assert fields["task_id"] == "ios-logo"
    assert fields["repo"] == FROZEN_REPO
    assert fields["scopes"] == list(FROZEN_SCOPES)
    assert resolve_platform_task("lumos-core ci").status == "STOP"


def test_recorded_inputs_are_not_write_scopes() -> None:
    assert IOS_LOGO_PRODUCTION_INPUT == "brand/source/logo001.png"
    assert IOS_LOGO_BACKUP_INPUT == "web/static/brand/logo001.png"
    assert IOS_LOGO_TARGET_MARK == "ui/public/chat-lumos-mark.svg"
    packet = format_work_packet(IOS_LOGO_ENVELOPE)
    assert "brand/source/logo001.png" in packet
    assert "web/static/brand/logo001.png" in packet
    assert "ui/public/chat-lumos-mark.svg" in packet
    assert "mevcut üretici bunu henüz tüketmiyor" in packet
    assert "çalışan bağlantı değildir" in packet
    for path in (
        IOS_LOGO_PRODUCTION_INPUT,
        IOS_LOGO_BACKUP_INPUT,
        IOS_LOGO_TARGET_MARK,
    ):
        assert path not in IOS_LOGO_SCOPES
        with pytest.raises(EnvelopeRejected, match="kapsam dışı|DOKUNMA"):
            assert_paths_allowed([path], IOS_LOGO_ENVELOPE)


@pytest.mark.parametrize("path", NON_APPICON_PATHS)
def test_non_appicon_paths_are_rejected(path: str) -> None:
    with pytest.raises(EnvelopeRejected, match="kapsam dışı|DOKUNMA"):
        assert_paths_allowed([path], IOS_LOGO_ENVELOPE)


@pytest.mark.parametrize(
    "path",
    (
        "brand/ios-export/Assets.xcassets/AppIcon.appiconset/Contents.json",
        "ios/LumosApp/Assets.xcassets/AppIcon.appiconset/Contents.json",
        "ios/LumosApp/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png",
    ),
)
def test_files_inside_frozen_appicon_sets_are_allowed(path: str) -> None:
    assert_paths_allowed([path], IOS_LOGO_ENVELOPE)


def test_work_packet_is_frozen_catalog_not_parser() -> None:
    packet = format_work_packet(IOS_LOGO_ENVELOPE)
    assert packet.startswith("HEDEF:")
    assert "KAPSAM:" in packet
    assert "DOKUNMA:" in packet
    assert "KANIT:" in packet
    assert "PR-006" in packet
    assert "donmuş" in packet
    assert "parser" not in packet
    assert "LUMOS_CHECKOUT_ROOT" not in packet
    assert "LUMOS_IOS_ROOT" not in packet
    assert "ios/Assets.xcassets/AppIcon.appiconset" not in packet
    for scope in FROZEN_SCOPES:
        assert scope in packet
    assert "açık insan onayı" in packet
    assert FROZEN_REPO in packet
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


def test_write_local_requires_human_approval_gate() -> None:
    assert IOS_LOGO_ENVELOPE.risk_step == STEP_TYPE_WRITE_LOCAL
    assert IOS_LOGO_ENVELOPE.confirmation_action_key == STEP_WRITE_LOCAL
    assert "write_local" in REQUIRES_CONFIRMATION_ACTIONS
    assert IOS_LOGO_ENVELOPE.confirmation_action_key in REQUIRES_CONFIRMATION_ACTIONS
    classified = resolve_platform_task("ios logo güncelle")
    assert classified.matched
    assert classified.envelope is not None
    assert classified.envelope.confirmation_action_key == "write_local"
    assert classified.envelope.confirmation_action_key in REQUIRES_CONFIRMATION_ACTIONS


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
    assert claim.claim.repo == FROZEN_REPO
    assert tuple(claim.claim.scopes) == FROZEN_SCOPES
    assert "Resources/Assets.xcassets" not in claim.claim.scopes


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


def test_apple_touch_and_launch_are_not_ios_logo_scopes() -> None:
    index = (ROOT / "ui" / "src" / "pages" / "index.astro").read_text(encoding="utf-8")
    panel = (ROOT / "ui" / "src" / "pages" / "panel.astro").read_text(encoding="utf-8")
    assert 'rel="apple-touch-icon"' in index
    assert 'rel="apple-touch-icon"' in panel
    assert (ROOT / "ui" / "public" / "chat-lumos-mark.svg").is_file()
    assert not (ROOT / "Resources" / "Assets.xcassets").exists()
    assert resolve_platform_task("apple-touch-icon güncelle").status == "STOP"
    with pytest.raises(EnvelopeRejected, match="kapsam dışı|DOKUNMA"):
        assert_paths_allowed(["web/static/apple-touch-icon.png"], IOS_LOGO_ENVELOPE)
    with pytest.raises(EnvelopeRejected, match="kapsam dışı|DOKUNMA"):
        assert_paths_allowed(
            ["ios/LumosApp/Assets.xcassets/LaunchImage.imageset"],
            IOS_LOGO_ENVELOPE,
        )
    packet = format_work_packet(IOS_LOGO_ENVELOPE)
    assert "LaunchImage" not in packet
    assert "LaunchScreen" not in packet


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
    assert decision.envelope.scopes == FROZEN_SCOPES
