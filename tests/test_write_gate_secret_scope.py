"""The production HMAC key may only be read inside a protected environment.

* ``lumos-write-gate``   — signer, required founder review.
* ``lumos-write-verify`` — PR verifier, deployment branches limited to main,
  no reviewers, so verification stays automatic on every PR.

These checks are static: they read the workflow files and fail if any job
references the key outside those environments, or if the verifier starts
checking out untrusted head code.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
SECRET_REF = re.compile(r"secrets\.LUMOS_WRITE_GATE_SECRET\b")
ALLOWED_ENVIRONMENTS = {"lumos-write-gate", "lumos-write-verify"}


def _workflows() -> list[Path]:
    return sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])


def _environment_name(job: dict) -> str | None:
    env = job.get("environment")
    if isinstance(env, str):
        return env
    if isinstance(env, dict):
        name = env.get("name")
        return name if isinstance(name, str) else None
    return None


def _jobs_reading_secret() -> list[tuple[str, str, dict]]:
    found = []
    for path in _workflows():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for job_id, job in (data.get("jobs") or {}).items():
            if SECRET_REF.search(yaml.safe_dump(job, allow_unicode=True)):
                found.append((path.name, job_id, job))
    return found


def test_secret_is_only_read_inside_a_protected_environment():
    jobs = _jobs_reading_secret()
    assert jobs, "expected the signer and the verifier to read the key"
    offenders = [
        f"{name}:{job_id} (environment={_environment_name(job)!r})"
        for name, job_id, job in jobs
        if _environment_name(job) not in ALLOWED_ENVIRONMENTS
    ]
    assert not offenders, "repository-level use of the HMAC key: " + ", ".join(offenders)


def test_secret_is_not_referenced_at_workflow_level():
    for path in _workflows():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        top = {k: v for k, v in data.items() if k != "jobs"}
        assert not SECRET_REF.search(yaml.safe_dump(top, allow_unicode=True)), path.name


def test_signer_keeps_the_approval_gated_environment():
    data = yaml.safe_load((WORKFLOWS / "write-sign-trusted.yml").read_text(encoding="utf-8"))
    assert _environment_name(data["jobs"]["sign"]) == "lumos-write-gate"


def test_verifier_uses_verify_environment_and_only_trusted_base_code():
    data = yaml.safe_load((WORKFLOWS / "write-attestation-trusted.yml").read_text(encoding="utf-8"))
    triggers = data.get("on", data.get(True))
    assert set(triggers) == {"pull_request_target"}
    job = data["jobs"]["write-attestation-trusted"]
    assert _environment_name(job) == "lumos-write-verify"
    checkout = next(s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.base.sha }}"
    assert checkout["with"]["persist-credentials"] is False
    # The key may appear only on the verify step, after the verifier has been
    # materialised from the base SHA.
    steps_with_key = [s.get("name") for s in job["steps"] if SECRET_REF.search(yaml.safe_dump(s))]
    assert steps_with_key == ["Verify HMAC write attestations"]


def test_untrusted_pr_ci_never_gets_the_production_key():
    text = (WORKFLOWS / "claim-guard.yml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    # Comments may name the secret; executable configuration must not.
    assert not SECRET_REF.search(yaml.safe_dump(data, allow_unicode=True))
    assert "lumos-ci-write-attestation-proof-not-prod-32" in text
