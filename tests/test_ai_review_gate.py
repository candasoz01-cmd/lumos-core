"""ai_review_gate: SHA-bound AI review evidence gate (ADR-036 draft)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from lumos_board.ai_review_gate import (
    AI_NOT_HUMAN,
    GateError,
    evaluate_ai_gate,
    is_critical,
    load_policy,
    main,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "ai-review" / "policy.json"
WORKFLOW = ROOT / ".github" / "workflows" / "ai-review-gate.yml"
HEAD = "a" * 40
OTHER = "b" * 40
CODEX = "chatgpt-codex-connector[bot]"


@pytest.fixture()
def policy() -> dict:
    p = load_policy(POLICY_PATH)
    p = copy.deepcopy(p)
    # Tests use a stand-in success value; the shipped policy keeps it empty.
    p["providers"]["codex"]["pass_status"] = ["ok-test-only"]
    return p


def cursor_run(sha=HEAD, conclusion="success", slug="cursor", status="completed"):
    return {
        "id": 1,
        "name": "Cursor Security Agent: Security Reviewer",
        "app": {"slug": slug},
        "head_sha": sha,
        "status": status,
        "conclusion": conclusion,
        "completed_at": "2026-11-09T07:00:00Z",
    }


def codex_comment(sha=HEAD, status="ok-test-only", unresolved=False, any_f=False,
                  login=CODEX, user_type="Bot", slug="chatgpt-codex-connector"):
    state = {"code_review": {"commit_sha": sha, "has_any_findings": any_f,
                             "has_unresolved_findings": unresolved, "status": status}}
    return {
        "id": 9,
        "user": {"login": login, "type": user_type},
        "performed_via_github_app": {"slug": slug},
        "updated_at": "2026-11-09T07:01:00Z",
        "body": f"<!-- codex-review-state:v1 {json.dumps(state)} -->\n## Codex Review Summary",
    }


def cursor_review(sha=HEAD):
    return {"id": 5, "user": {"login": "cursor[bot]", "type": "Bot"}, "commit_id": sha,
            "state": "COMMENTED"}


def run_ai(policy, paths=("docs/x.md",), runs=None, reviews=(), rc=(), comments=None):
    return evaluate_ai_gate(
        pr=1, head_sha=HEAD, paths=list(paths),
        check_runs=[cursor_run()] if runs is None else list(runs),
        reviews=list(reviews), review_comments=list(rc),
        issue_comments=[codex_comment()] if comments is None else list(comments),
        policy=policy,
    )


# ------------------------------------------------------------ policy


def test_shipped_policy_requires_two_providers_and_codex_fails_closed():
    p = load_policy(POLICY_PATH)
    assert p["min_distinct_providers"] >= 2
    assert p["providers"]["codex"]["pass_status"] == []
    v = evaluate_ai_gate(pr=1, head_sha=HEAD, paths=["docs/x.md"], check_runs=[cursor_run()],
                         reviews=[], review_comments=[], issue_comments=[codex_comment()],
                         policy=p)
    assert v["pass"] is False
    assert "not yet verified" in v["providers"]["codex"]["reason"]


def test_policy_below_two_providers_rejected(tmp_path):
    bad = json.loads(POLICY_PATH.read_text())
    bad["min_distinct_providers"] = 1
    f = tmp_path / "p.json"
    f.write_text(json.dumps(bad))
    with pytest.raises(GateError):
        load_policy(f)


# ------------------------------------------------------------ AI gate


def test_two_providers_on_head_pass_and_never_human(policy):
    v = run_ai(policy)
    assert v["pass"] is True
    assert v["providers_passed"] == ["codex", "cursor"]
    assert v["human_approval"] is False and v["note"] == AI_NOT_HUMAN


def test_one_provider_is_not_enough(policy):
    assert run_ai(policy, comments=[])["pass"] is False
    assert run_ai(policy, runs=[])["pass"] is False


@pytest.mark.parametrize("kw", [{"sha": OTHER}, {"slug": "evil-app"},
                                {"conclusion": "neutral"}, {"status": "in_progress"}])
def test_cursor_rejects_wrong_sha_app_or_result(policy, kw):
    assert run_ai(policy, runs=[cursor_run(**kw)])["providers"]["cursor"]["pass"] is False


@pytest.mark.parametrize("kw", [{"sha": OTHER}, {"status": "failed"}, {"unresolved": True},
                                {"login": "candasoz01-cmd", "user_type": "User"},
                                {"login": "chatgpt-codex-connector", "user_type": "User"},
                                {"slug": "other"}])
def test_codex_rejects_wrong_sha_identity_or_status(policy, kw):
    assert run_ai(policy, comments=[codex_comment(**kw)])["providers"]["codex"]["pass"] is False


def test_codex_uses_latest_state(policy):
    old = codex_comment(sha=OTHER)
    old["updated_at"] = "2026-11-09T08:00:00Z"  # newer state on another SHA wins
    assert run_ai(policy, comments=[codex_comment(), old])["pass"] is False


def test_critical_paths_are_stricter(policy):
    paths = [".github/workflows/ci.yml"]
    assert run_ai(policy, paths=paths)["pass"] is False  # no cursor review on head
    assert run_ai(policy, paths=paths, reviews=[cursor_review()])["pass"] is True
    assert run_ai(policy, paths=paths, reviews=[cursor_review()],
                  comments=[codex_comment(any_f=True)])["pass"] is False
    inline = {"id": 3, "user": {"login": "cursor[bot]", "type": "Bot"}, "commit_id": HEAD}
    assert run_ai(policy, paths=paths, reviews=[cursor_review()], rc=[inline])["pass"] is False


def test_unknown_or_hostile_paths_are_critical(policy):
    assert is_critical(["-rf"], policy) and is_critical(["a/../b"], policy)
    assert is_critical(["src/lumos_board/trusted_sign.py"], policy)
    assert not is_critical(["docs/x.md"], policy)
    assert run_ai(policy, paths=[])["critical"] is True


def test_short_sha_rejected(policy):
    with pytest.raises(GateError):
        evaluate_ai_gate(pr=1, head_sha="abc", paths=[], check_runs=[], reviews=[],
                         review_comments=[], issue_comments=[], policy=policy)


# ------------------------------------------------------- workflow shape


def test_workflow_runs_from_base_and_never_skips():
    text = WORKFLOW.read_text()
    assert "pull_request_target:" in text and "\n  pull_request:" not in text
    assert text.count("ref: ${{ github.event.pull_request.base.sha }}") == 1
    assert "pull_request.head.ref" not in text and "refs/pull/" not in text
    assert "\n    if:" not in text and "pull_request.draft" not in text  # never SKIPPED
    assert "environment:" not in text  # founder authority is ADR-035, not this job
    assert "write" not in text.split("permissions:")[1].split("concurrency:")[0]


def test_cli_fails_closed_on_bad_policy(tmp_path, capsys):
    rc = main(["ai-gate", "--repo", "o/r", "--pr", "1", "--head", HEAD,
               "--policy", str(tmp_path / "missing.json")])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1 and out["pass"] is False and out["human_approval"] is False


def test_policy_has_no_founder_or_merge_authority():
    p = load_policy(POLICY_PATH)
    assert "founder_gate" not in p and "not founder merge authority" in p["note"]
