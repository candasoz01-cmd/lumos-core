"""CI's required `test` job runs the security-critical Meta callback tests."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"

REQUIRED = (
    "tests/test_meta_deletion_callbacks.test.mjs",
    "tests/test_meta_oauth.test.mjs",
    "tests/test_meta_webhook.test.mjs",
    "tests/test_credential_gateway.test.mjs",
)


def test_required_test_job_runs_meta_callback_node_tests():
    text = CI.read_text(encoding="utf-8")
    job = text[text.index("\n  test:\n") : text.index("\n  rust:\n")]
    assert "actions/setup-node@v4" in job
    assert "node --test" in job
    for path in REQUIRED:
        assert path in job, path
        assert (ROOT / path).is_file(), path
