"""Aşama 0: kurucu / ajan / imza hizmeti ayrımı.

Aşama A ve B yetkisi üretmez. Üretim sırrını loglamaz, Settings API
yazmaz, merge / dispatch / ortam onayı çağırmaz. #945 ve #946 kilitli
kalır; bu modül onları açmaz.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from lumos_board.task_claim import ClaimError, _clean_text

SCHEMA = "lumos.write_authority_split.v1"
SUBJECT_FOUNDER = "human.founder"
SUBJECT_AGENT = "agent"
SUBJECT_SERVICE = "service.write-gate"
SUBJECT_UNKNOWN = "unknown"
SERVICE_OWNER = "lumos-write-gate"
PROOF_KEY_CHECK = "write-attestation"
PRODUCTION_CHECK = "write-attestation-trusted"
REASON_AGENT_SECRET = "WRITE_SECRET_AGENT_DENIED"
REASON_PROOF_AS_PRODUCTION = "WRITE_SECRET_PROOF_IS_NOT_PRODUCTION"
REASON_SUBJECT_DENIED = "WRITE_SECRET_SUBJECT_DENIED"
REASON_SERVICE_CONTEXT = "WRITE_SECRET_SERVICE_CONTEXT_DENIED"
REASON_ALLOWED = "WRITE_SECRET_SERVICE_ONLY"

_NON_HUMAN_MARKERS = ("[bot]",)
_NON_HUMAN_PREFIXES = ("app/",)
_AGENT_OWNER_TOKENS = (
    "cursor",
    "claude",
    "codex",
    "agent",
    "bot",
)


class AuthoritySplitError(ClaimError):
    """Kurucu/ajan/sır ayrımı reddi."""


def public_proof_key(*, workflow: Path | None = None) -> str:
    path = workflow or Path(__file__).resolve().parents[2] / ".github" / "workflows" / "claim-guard.yml"
    marker = "LUMOS_WRITE_GATE_SECRET:"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AuthoritySplitError("genel prova anahtarı okunamadı") from exc
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(marker) and "secrets." not in stripped:
            value = stripped.split(":", 1)[1].strip()
            if len(value.encode("utf-8")) >= 32:
                return value
    raise AuthoritySplitError("genel prova anahtarı okunamadı")


def classify_subject(
    *,
    owner: str,
    lumos_agent: str | None = None,
    github_actor: str | None = None,
    event_name: str | None = None,
    ref: str | None = None,
    founder_ids: Sequence[str] = (),
) -> str:
    """Özne sınıfı. Kurucu kimliği ajan trailer'ından veya LUMOS_AGENT'tan türemez."""
    owner = _clean_text(owner, "owner")
    agent = (lumos_agent or "").strip()
    actor = (github_actor or "").strip()
    if agent or _looks_agent(owner) or _looks_agent(actor):
        if owner == SERVICE_OWNER:
            return SUBJECT_UNKNOWN
        return SUBJECT_AGENT
    if owner == SERVICE_OWNER:
        if ref == "refs/heads/main" and event_name == "workflow_dispatch":
            return SUBJECT_SERVICE
        return SUBJECT_UNKNOWN
    allowed = {_clean_text(item, "founder_id") for item in founder_ids}
    if owner in allowed and not agent:
        return SUBJECT_FOUNDER
    return SUBJECT_UNKNOWN


def _looks_agent(value: str) -> bool:
    lowered = value.lower()
    if any(marker in lowered for marker in _NON_HUMAN_MARKERS):
        return True
    if any(lowered.startswith(prefix) for prefix in _NON_HUMAN_PREFIXES):
        return True
    tokens = set(lowered.replace("_", "-").replace("/", "-").split("-"))
    return bool(tokens.intersection(_AGENT_OWNER_TOKENS))


def assert_production_secret_use(
    *,
    subject: str,
    secret: str | None,
    proof_key: str | None = None,
    event_name: str | None = None,
    ref: str | None = None,
) -> str:
    """Üretim sırrı yalnız yetkili hizmet öznesine açıktır. Ajan ve prova anahtarı red."""
    if secret is None or len(secret.encode("utf-8")) < 32:
        raise AuthoritySplitError("CLAIM_GUARD_UNCONFIGURED")
    proof = proof_key if proof_key is not None else public_proof_key()
    if secret == proof:
        raise AuthoritySplitError(REASON_PROOF_AS_PRODUCTION)
    if subject == SUBJECT_AGENT:
        raise AuthoritySplitError(REASON_AGENT_SECRET)
    if subject != SUBJECT_SERVICE:
        raise AuthoritySplitError(REASON_SUBJECT_DENIED)
    if ref != "refs/heads/main" or event_name != "workflow_dispatch":
        raise AuthoritySplitError(REASON_SERVICE_CONTEXT)
    return REASON_ALLOWED


def simulate_required_check_impact(
    *,
    current_required: Sequence[str],
    add: Sequence[str],
    pr_checks: Mapping[str, str],
    pr_number: int | None = None,
    head_sha: str | None = None,
) -> dict[str, Any]:
    """Zorunlu kontrol eklemenin etkisini hesaplar. Settings yazmaz."""
    blockers: list[dict[str, str]] = []
    for name in add:
        conclusion = str(pr_checks.get(name) or "missing").upper()
        if conclusion != "SUCCESS":
            blockers.append({"check": name, "conclusion": conclusion})
    proposed = list(current_required)
    for name in add:
        if name not in proposed:
            proposed.append(name)
    return {
        "schema": SCHEMA,
        "settings_mutated": False,
        "dispatch": False,
        "merge": False,
        "pr_number": pr_number,
        "head_sha": head_sha,
        "current_required": list(current_required),
        "proposed_required": proposed,
        "would_block_merge": bool(blockers),
        "blockers": blockers,
        "proof_key_check": pr_checks.get(PROOF_KEY_CHECK),
        "production_check": pr_checks.get(PRODUCTION_CHECK),
        "grants_stage_a": False,
        "grants_stage_b": False,
    }


def _classify_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m lumos_board.write_authority_split classify")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--lumos-agent", default="")
    parser.add_argument("--github-actor", default="")
    parser.add_argument("--event-name", default="")
    parser.add_argument("--ref", default="")
    parser.add_argument("--founder-id", action="append", default=[])
    args = parser.parse_args(argv)
    subject = classify_subject(
        owner=args.owner,
        lumos_agent=args.lumos_agent or os.environ.get("LUMOS_AGENT"),
        github_actor=args.github_actor or os.environ.get("GITHUB_ACTOR"),
        event_name=args.event_name or os.environ.get("GITHUB_EVENT_NAME"),
        ref=args.ref or os.environ.get("GITHUB_REF"),
        founder_ids=args.founder_id,
    )
    sys.stdout.write(json.dumps({"schema": SCHEMA, "subject": subject, "owner": args.owner}, sort_keys=True) + "\n")
    return 0


def _secret_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m lumos_board.write_authority_split secret-use")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--lumos-agent", default="")
    parser.add_argument("--event-name", default="")
    parser.add_argument("--ref", default="")
    parser.add_argument("--founder-id", action="append", default=[])
    args = parser.parse_args(argv)
    subject = classify_subject(
        owner=args.owner,
        lumos_agent=args.lumos_agent or os.environ.get("LUMOS_AGENT"),
        event_name=args.event_name or os.environ.get("GITHUB_EVENT_NAME"),
        ref=args.ref or os.environ.get("GITHUB_REF"),
        founder_ids=args.founder_id,
    )
    reason = assert_production_secret_use(
        subject=subject,
        secret=os.environ.get("LUMOS_WRITE_GATE_SECRET"),
        event_name=args.event_name or os.environ.get("GITHUB_EVENT_NAME"),
        ref=args.ref or os.environ.get("GITHUB_REF"),
    )
    sys.stdout.write(json.dumps({"schema": SCHEMA, "reason": reason, "subject": subject}, sort_keys=True) + "\n")
    return 0


def _impact_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m lumos_board.write_authority_split required-impact")
    parser.add_argument("--file", required=True)
    args = parser.parse_args(argv)
    payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise AuthoritySplitError("etki kaydı geçersiz")
    report = simulate_required_check_impact(
        current_required=list(payload.get("current_required") or []),
        add=list(payload.get("add") or []),
        pr_checks=dict(payload.get("pr_checks") or {}),
        pr_number=payload.get("pr_number") if isinstance(payload.get("pr_number"), int) else None,
        head_sha=payload.get("head_sha") if isinstance(payload.get("head_sha"), str) else None,
    )
    sys.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if not argv or argv[0] in {"-h", "--help"}:
            sys.stderr.write("usage: classify | secret-use | required-impact\n")
            return 2
        command, rest = argv[0], argv[1:]
        if command == "classify":
            return _classify_main(rest)
        if command == "secret-use":
            return _secret_main(rest)
        if command == "required-impact":
            return _impact_main(rest)
        raise AuthoritySplitError("bilinmeyen komut")
    except (ClaimError, OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(json.dumps({"error": str(exc)}, ensure_ascii=False) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
