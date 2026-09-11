"""PR-006 dry-run: chat sentence → catalog envelope, claim fields, DOKUNMA reject."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.platform_task_envelope import (
    CATALOG,
    EVIDENCE_KIND_INFORMATION,
    IOS_LOGO_ENVELOPE,
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


def test_catalog_has_only_ios_logo() -> None:
    assert tuple(CATALOG) == ("ios-logo",)


def test_accept_chat_maps_to_ios_logo_claim_fields() -> None:
    decision = resolve_platform_task(ACCEPT_CHAT)
    assert decision.matched
    envelope = decision.envelope
    assert envelope is not None
    assert envelope.task_key == "ios-logo"
    assert envelope.repo == "Lumos"
    assert envelope.scopes == (
        "Resources/Assets.xcassets/AppIcon.appiconset",
        "Resources/Assets.xcassets/AppIcon",
    )
    fields = claim_fields(envelope)
    assert fields["task_id"] == "ios-logo"
    assert fields["repo"] == "Lumos"
    assert fields["scopes"] == list(envelope.scopes)


def test_work_packet_uses_agents_md_template() -> None:
    packet = format_work_packet(IOS_LOGO_ENVELOPE)
    assert packet.startswith("HEDEF:")
    assert "KAPSAM:" in packet
    assert "DOKUNMA:" in packet
    assert "KANIT:" in packet
    assert "App/ Swift" in packet
    assert "#842" in packet
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
    assert claim.claim.repo == "Lumos"
    assert "Resources/Assets.xcassets/AppIcon.appiconset" in claim.claim.scopes


def test_iconset_path_is_allowed() -> None:
    assert_paths_allowed(
        ["Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png"],
        IOS_LOGO_ENVELOPE,
    )


def test_swift_and_conductor_paths_are_dokunma() -> None:
    with pytest.raises(EnvelopeRejected, match="DOKUNMA"):
        assert_paths_allowed(["App/UI/SplashView.swift"], IOS_LOGO_ENVELOPE)
    with pytest.raises(EnvelopeRejected, match="DOKUNMA"):
        assert_paths_allowed(["App/AI/Conductor.swift"], IOS_LOGO_ENVELOPE)
    with pytest.raises(EnvelopeRejected, match="kapsam dışı"):
        assert_paths_allowed(
            ["Resources/Assets.xcassets/LaunchImage.imageset/launch.png"],
            IOS_LOGO_ENVELOPE,
        )


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
