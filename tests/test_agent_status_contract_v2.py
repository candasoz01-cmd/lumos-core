"""Reader-v2: Agent Status sözleşmesi v2 — doğrulama, sürüm kuralı, türetme.

v1 davranışı `tests/test_agent_status_contract.py` içinde birebir korunur;
burada yalnız v2 kuralları, sürüm dağıtımı ve doküman ↔ kod türetmesi test
edilir. Türetme testleri `docs/contracts/agent-status-v2.md` tablolarını
kaynak alır: doküman ile kod ayrışırsa bu testler kırılmalıdır.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.agent_status_contract import (  # noqa: E402
    LEGACY_AGENT_ID,
    SCHEMA_VERSION,
    SCHEMA_VERSION_V2,
    STATUS_AWAITING_DECISION,
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_RUNNING,
    SUPPORTED_SCHEMA_VERSIONS,
    V2_VALID_STATUSES,
    WAIT_REASON_DEPENDENCY,
    WAIT_REASON_HUMAN_DECISION,
    WAIT_REASONS_BY_STATUS,
    UnsupportedSchemaVersionError,
    load_agent_status_records,
    record_from_payload,
    resolve_status_payload,
    validate_agent_status_payload,
    validate_agent_status_payload_v2,
)
from lumos_board.agent_status import read_agent_status_projection  # noqa: E402

_V2_DOC = _REPO_ROOT / "docs" / "contracts" / "agent-status-v2.md"


def _v2_payload(**overrides: object) -> dict:
    payload = {
        "version": SCHEMA_VERSION_V2,
        "agent_id": "claude.code",
        "job_id": "abc123",
        "status": STATUS_RUNNING,
        "owner": "claude.code",
        "started_at": "2026-08-25T10:00:00+00:00",
        "updated_at": "2026-08-25T10:05:00+00:00",
        "evidence_ref": "outbox/agent_status_abc123.json",
        "progress": 40,
        "message": "tests",
    }
    payload.update(overrides)
    return payload


# --- v2 doğrulama ---


def test_v2_running_record_passes_without_wait_fields() -> None:
    payload = _v2_payload()
    assert validate_agent_status_payload_v2(payload) == []
    record = record_from_payload(payload)
    assert record.version == SCHEMA_VERSION_V2
    assert record.status == STATUS_RUNNING
    assert record.wait_reason is None
    assert record.decision_ref is None


def test_v2_blocked_accepts_each_nonhuman_reason() -> None:
    for reason in WAIT_REASONS_BY_STATUS[STATUS_BLOCKED]:
        payload = _v2_payload(status=STATUS_BLOCKED, wait_reason=reason)
        assert validate_agent_status_payload_v2(payload) == []
        assert record_from_payload(payload).wait_reason == reason


def test_v2_blocked_without_reason_is_invalid() -> None:
    errors = validate_agent_status_payload_v2(_v2_payload(status=STATUS_BLOCKED))
    assert "wait_reason_missing" in errors


def test_v2_blocked_with_human_decision_is_invalid() -> None:
    errors = validate_agent_status_payload_v2(
        _v2_payload(status=STATUS_BLOCKED, wait_reason=WAIT_REASON_HUMAN_DECISION)
    )
    assert "wait_reason_invalid" in errors


def test_v2_awaiting_decision_requires_human_decision_and_ref() -> None:
    payload = _v2_payload(
        status=STATUS_AWAITING_DECISION,
        wait_reason=WAIT_REASON_HUMAN_DECISION,
        decision_ref="  https://github.com/candasoz01-cmd/lumos-core/pull/803  ",
    )
    assert validate_agent_status_payload_v2(payload) == []
    record = record_from_payload(payload)
    assert record.decision_ref == "https://github.com/candasoz01-cmd/lumos-core/pull/803"


def test_v2_awaiting_decision_with_nonhuman_reason_is_invalid() -> None:
    errors = validate_agent_status_payload_v2(
        _v2_payload(
            status=STATUS_AWAITING_DECISION,
            wait_reason=WAIT_REASON_DEPENDENCY,
            decision_ref="PR #803",
        )
    )
    assert "wait_reason_invalid" in errors


def test_v2_awaiting_decision_without_ref_is_invalid() -> None:
    base = _v2_payload(status=STATUS_AWAITING_DECISION, wait_reason=WAIT_REASON_HUMAN_DECISION)
    assert "decision_ref_missing" in validate_agent_status_payload_v2(base)
    assert "decision_ref_missing" in validate_agent_status_payload_v2({**base, "decision_ref": "   "})


def test_v2_wait_fields_forbidden_outside_wait_statuses() -> None:
    assert "wait_reason_forbidden" in validate_agent_status_payload_v2(
        _v2_payload(wait_reason=WAIT_REASON_DEPENDENCY)
    )
    assert "decision_ref_forbidden" in validate_agent_status_payload_v2(
        _v2_payload(status=STATUS_COMPLETED, decision_ref="PR #803")
    )


def test_validators_reject_each_others_version() -> None:
    assert "version_invalid" in validate_agent_status_payload(_v2_payload())
    assert "version_invalid" in validate_agent_status_payload_v2(_v2_payload(version=SCHEMA_VERSION))


def test_v1_record_gets_no_wait_inference() -> None:
    record = record_from_payload(_v2_payload(version=SCHEMA_VERSION))
    assert record.version == SCHEMA_VERSION
    assert record.status == STATUS_RUNNING
    assert record.wait_reason is None
    assert record.decision_ref is None


# --- Sürüm kuralı ---


def test_versionless_payload_normalizes_as_v1(tmp_path: Path) -> None:
    source = tmp_path / "agent_status_f00d.json"
    resolved = resolve_status_payload(
        {"job_id": "f00d", "phase": "plan", "status": "running"}, source_path=source
    )
    assert resolved["version"] == SCHEMA_VERSION
    assert resolved["agent_id"] == LEGACY_AGENT_ID


def test_unknown_explicit_versions_fail_closed(tmp_path: Path) -> None:
    source = tmp_path / "agent_status_f00d.json"
    for version in (3, 0, "2", "legacy"):
        try:
            resolve_status_payload(_v2_payload(version=version), source_path=source)
        except UnsupportedSchemaVersionError as e:
            assert "version_unsupported" in str(e)
        else:
            raise AssertionError(f"fail closed bekleniyordu: version={version!r}")


def test_loader_mixed_directory_v1_v2_legacy_and_unknown(tmp_path: Path) -> None:
    (tmp_path / "agent_status_1e9a17.json").write_text(
        json.dumps({"job_id": "1e9a17", "phase": "plan", "status": "running"}),
        encoding="utf-8",
    )
    (tmp_path / "agent_status_abc123.json").write_text(
        json.dumps(_v2_payload(version=SCHEMA_VERSION)), encoding="utf-8"
    )
    (tmp_path / "agent_status_def456.json").write_text(
        json.dumps(
            _v2_payload(
                job_id="def456",
                agent_id="claude.session",
                owner="claude.session",
                status=STATUS_AWAITING_DECISION,
                wait_reason=WAIT_REASON_HUMAN_DECISION,
                decision_ref="OD-063",
            )
        ),
        encoding="utf-8",
    )
    (tmp_path / "agent_status_ffff99.json").write_text(
        json.dumps(_v2_payload(job_id="ffff99", version=3)), encoding="utf-8"
    )

    result = load_agent_status_records(tmp_path)

    by_job = {r.job_id: r for r in result.records}
    assert set(by_job) == {"1e9a17", "abc123", "def456"}
    assert by_job["1e9a17"].agent_id == LEGACY_AGENT_ID
    assert by_job["abc123"].version == SCHEMA_VERSION
    v2 = by_job["def456"]
    assert v2.version == SCHEMA_VERSION_V2
    assert v2.agent_id == "claude.session"  # LEGACY_AGENT_ID'ye ezilmedi
    assert v2.status == STATUS_AWAITING_DECISION
    assert v2.wait_reason == WAIT_REASON_HUMAN_DECISION
    assert v2.decision_ref == "OD-063"
    assert result.issues == ["agent_status_ffff99.json: version_unsupported: 3"]


def test_board_projection_accepts_v2_and_drops_unknown_version(tmp_path: Path) -> None:
    (tmp_path / "agent_status_def456.json").write_text(
        json.dumps(
            _v2_payload(
                job_id="def456",
                status=STATUS_BLOCKED,
                wait_reason=WAIT_REASON_DEPENDENCY,
            )
        ),
        encoding="utf-8",
    )
    (tmp_path / "agent_status_ffff99.json").write_text(
        json.dumps(_v2_payload(job_id="ffff99", agent_id="other", owner="other", version=7)),
        encoding="utf-8",
    )
    projection = read_agent_status_projection({"outbox": tmp_path})
    assert len(projection.records) == 1
    record = projection.records[0].record
    assert record.version == SCHEMA_VERSION_V2
    assert record.status == STATUS_BLOCKED
    assert record.agent_id == "claude.code"  # v2 kaydı legacy'ye ezilmedi
    assert projection.invalid_records == 1  # version=7 fail closed


# --- Doküman ↔ kod türetmesi (iki yönlü) ---


def _doc_section(text: str, heading: str) -> str:
    start = text.index(heading)
    match = re.search(r"\n#{2,3} ", text[start + len(heading):])
    end = start + len(heading) + match.start() if match else len(text)
    return text[start:end]


def test_doc_status_table_matches_code_both_ways() -> None:
    section = _doc_section(_V2_DOC.read_text(encoding="utf-8"), "## Durum kümesi")
    doc_statuses = re.findall(r"^\|\s*`([a-z_]+)`\s*\|", section, re.MULTILINE)
    assert doc_statuses, "doküman durum tablosu bulunamadı"
    assert set(doc_statuses) == set(V2_VALID_STATUSES)
    assert len(doc_statuses) == len(V2_VALID_STATUSES)


def test_doc_wait_reason_mapping_matches_code_both_ways() -> None:
    section = _doc_section(
        _V2_DOC.read_text(encoding="utf-8"), "### `wait_reason` eşleme kuralları"
    )
    doc_mapping: dict[str, tuple[str, ...]] = {}
    for line in section.splitlines():
        match = re.match(r"^\|\s*`([a-z_]+)`\s*\|(.+)\|\s*$", line)
        if not match or match.group(1) == "status":
            continue
        doc_mapping[match.group(1)] = tuple(re.findall(r"`([a-z_]+)`", match.group(2)))
    assert doc_mapping == WAIT_REASONS_BY_STATUS


def test_doc_version_rule_matches_supported_versions() -> None:
    section = _doc_section(_V2_DOC.read_text(encoding="utf-8"), "## v1 geriye uyumluluk")
    doc_versions = {int(v) for v in re.findall(r"`version: (\d+)`", section)}
    unsupported_examples = {int(v) for v in re.findall(r"örn\. `version: (\d+)`", section)}
    assert doc_versions - unsupported_examples == set(SUPPORTED_SCHEMA_VERSIONS)
