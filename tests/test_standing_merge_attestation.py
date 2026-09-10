"""F9: standing attestation must be an append-only, later-verifiable record.

On origin/main (9691c8a4) ``--attest`` / ``--attest-by`` lived in process argv
only: CLI factual promotion exited 0, printed no actor, and wrote no JSONL.
CI still must not invent that judgement.
"""
from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path

import pytest

from standing_merge.attestation_log import (
    ALLOWED_KEYS,
    append_standing_attestation,
    read_standing_attestations,
    standing_attestation_log_path,
)
from standing_merge.classify import CLASS_ELIGIBLE, CLASS_SEMANTIC, main

ADR023 = "docs/decisions/ADR-023-lumos-representative-avatar.md"
HEAD = "89bc0651f0a1b2c3d4e5f60718293a4b5c6d7e8f"
ACTOR = "human-reviewer"


@pytest.fixture(autouse=True)
def _isolate_ledger(tmp_path, monkeypatch):
    base = tmp_path / ".lumos"
    monkeypatch.setenv("LUMOS_BASE_DIR", str(base))
    return base


def _block_log_dir(base: Path) -> None:
    logs = base / "logs"
    logs.parent.mkdir(parents=True, exist_ok=True)
    if logs.is_dir():
        for child in logs.iterdir():
            if child.is_file():
                child.unlink()
        logs.rmdir()
    logs.write_text("not-a-directory", encoding="utf-8")


def _run_main(argv: list[str]) -> tuple[int, dict]:
    stdout = StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout, StringIO()
    try:
        code = main(argv)
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return code, json.loads(stdout.getvalue())


def test_cli_factual_attestation_records_actor_head_and_paths(_isolate_ledger):
    code, verdict = _run_main(
        [
            ADR023,
            "--head-sha",
            HEAD,
            "--attest",
            "factual",
            "--attest-sha",
            HEAD,
            "--attest-by",
            ACTOR,
        ]
    )
    records = read_standing_attestations()
    assert code == 0
    assert verdict["class"] == CLASS_ELIGIBLE
    assert verdict["standing_merge"] is True
    assert verdict["attest_by"] == ACTOR
    assert len(records) == 1
    row = records[0]
    assert tuple(row) == ALLOWED_KEYS
    assert row["attest_by"] == ACTOR
    assert row["head_sha"] == HEAD
    assert row["attest_sha"] == HEAD
    assert row["verdict"] == "factual"
    assert row["class"] == "eligible"
    assert row["standing_merge"] is True
    assert ADR023 in row["paths"]
    raw = standing_attestation_log_path().read_text(encoding="utf-8")
    assert ACTOR in raw
    assert "secret" not in {key.lower() for key in row}
    assert "vault_ref" not in row


def test_anonymous_cli_attest_cannot_open_standing(_isolate_ledger):
    code, verdict = _run_main(
        [ADR023, "--head-sha", HEAD, "--attest", "factual", "--attest-sha", HEAD]
    )
    assert code == 3
    assert verdict["class"] == CLASS_SEMANTIC
    assert verdict["standing_merge"] is False
    assert verdict["attestation"] == "actor_missing"
    assert read_standing_attestations() == []


def test_factual_attestation_fail_closed_when_ledger_io_fails(_isolate_ledger):
    _block_log_dir(_isolate_ledger)
    code, verdict = _run_main(
        [
            ADR023,
            "--head-sha",
            HEAD,
            "--attest",
            "factual",
            "--attest-sha",
            HEAD,
            "--attest-by",
            ACTOR,
        ]
    )
    assert code == 3
    assert verdict["class"] == CLASS_SEMANTIC
    assert verdict["standing_merge"] is False
    assert verdict["attestation"] == "record_missing"
    assert "attestation_record_write_failed" in verdict["reasons"]
    assert read_standing_attestations() == []


def test_path_only_eligible_does_not_require_an_attestation_record(_isolate_ledger):
    """Machine-safe allowlist class is not a human judgement; CI still reports it."""
    code, verdict = _run_main(["docs/TECHNICAL_DEBT.md"])
    assert code == 0
    assert verdict["class"] == CLASS_ELIGIBLE
    assert verdict["attest_by"] == ""
    assert read_standing_attestations() == []


def test_ledger_is_append_only(_isolate_ledger):
    first = append_standing_attestation(
        attest_by="alice",
        head_sha=HEAD,
        attest_sha=HEAD,
        verdict="factual",
        standing_class="eligible",
        paths=[ADR023],
        reasons=["promoted:factual"],
        standing_merge=True,
    )
    second = append_standing_attestation(
        attest_by="bob",
        head_sha="aa" * 20,
        attest_sha="aa" * 20,
        verdict="normative",
        standing_class="excluded",
        paths=[ADR023],
        standing_merge=False,
    )
    records = read_standing_attestations()
    assert records == [first, second]
    assert records[0]["attest_by"] == "alice"
    assert records[1]["attest_by"] == "bob"


def test_append_rejects_secret_kwargs():
    with pytest.raises(TypeError):
        append_standing_attestation(
            attest_by=ACTOR,
            head_sha=HEAD,
            attest_sha=HEAD,
            verdict="factual",
            standing_class="eligible",
            paths=[ADR023],
            standing_merge=True,
            secret="must-not-be-accepted",
        )


def test_ci_classify_step_does_not_pass_attest():
    text = (
        Path(__file__).resolve().parents[1]
        / ".github/workflows/standing-class.yml"
    ).read_text(encoding="utf-8")
    classify_step = text.split("Classify with trusted classifier", 1)[1]
    command_lines = [
        line
        for line in classify_step.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    joined = "\n".join(command_lines)
    assert "--paths-nul" in classify_step
    assert "--attest" not in joined
    assert "--attest-by" not in joined
    assert "--attest-sha" not in joined
