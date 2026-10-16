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
REASON_IDENTITY_GAP = "WRITE_IDENTITY_EVIDENCE_DENIED"
REQUIRED_APP_SLUGS = ("claude", "chatgpt-codex-connector")
FOUNDER_LOGIN = "candasoz01-cmd"
# Inventory only. Listing a grant here does not open Stage A or B.
STAGE_A_OPENS = (
    "founder_merge_of_signer_workflow_onto_main",
    "workflow_file_present_on_origin_main",
    "write_sign_trusted_listed_active",
)
STAGE_B_OPENS = (
    "founder_workflow_dispatch_from_refs_heads_main",
    "founder_lumos_write_gate_environment_approval",
    "service_production_secret_in_sign_job_only",
    "copy_range_to_trusted_sign_branch",
    "open_draft_pr_of_signed_copy",
)
STAGE_NEITHER_OPENS = (
    "agent_merge",
    "agent_dispatch",
    "agent_environment_approval",
    "grants_merge",
    "proof_hmac_as_production",
    "relax_trusted_verifier",
    "branch_protection_settings_write",
    "unlock_pr_945",
    "unlock_pr_946",
    "later_pr_merge",
    "publication_signers_root",
)


def stage_authority_map() -> dict[str, Any]:
    """What A and B would unlock if the founder later opens them. This call does not open them."""
    return {
        "schema": SCHEMA,
        "stage_0_accepted": True,
        "grants_stage_a": False,
        "grants_stage_b": False,
        "stage_a_opens": list(STAGE_A_OPENS),
        "stage_b_opens": list(STAGE_B_OPENS),
        "neither_opens": list(STAGE_NEITHER_OPENS),
        "agent_inherits_founder": False,
        "dispatch": False,
        "merge": False,
        "settings_mutated": False,
    }

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


def evaluate_identity_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Salt-okunur kimlik kaydını doğrular. Settings yazmaz, Aşama A/B açmaz.

    Claude ve Codex kendi GitHub App kayıtlarıyla ajan öznesidir. Kurucu
    ``User`` allowlist'tedir; ajan sürecinde üretim sırrı ve SSH beklenmez.
    """
    if not isinstance(payload, Mapping):
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    founder = payload.get("founder")
    apps = payload.get("apps")
    process = payload.get("agent_process")
    environment = payload.get("write_gate_environment")
    identities = payload.get("operating_identities")
    if not isinstance(founder, Mapping) or not isinstance(apps, list):
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    if not isinstance(process, Mapping) or not isinstance(environment, Mapping):
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    if not isinstance(identities, list):
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    founder_login = str(founder.get("login") or "")
    founder_type = str(founder.get("type") or "")
    founder_id = founder.get("id")
    if founder_login != FOUNDER_LOGIN or founder_type != "User" or not isinstance(founder_id, int):
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    if classify_subject(owner=founder_login, founder_ids=(FOUNDER_LOGIN,)) != SUBJECT_FOUNDER:
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    if classify_subject(
        owner=founder_login,
        lumos_agent="cursor-cloud",
        founder_ids=(FOUNDER_LOGIN,),
    ) != SUBJECT_AGENT:
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    by_slug = {}
    for item in apps:
        if not isinstance(item, Mapping):
            raise AuthoritySplitError(REASON_IDENTITY_GAP)
        slug = str(item.get("slug") or "")
        bot_login = str(item.get("bot_login") or "")
        bot_type = str(item.get("bot_type") or "")
        app_id = item.get("id")
        bot_id = item.get("bot_id")
        if not slug or bot_type != "Bot" or not bot_login or not isinstance(app_id, int):
            raise AuthoritySplitError(REASON_IDENTITY_GAP)
        if not isinstance(bot_id, int) or bot_id == founder_id or app_id == founder_id:
            raise AuthoritySplitError(REASON_IDENTITY_GAP)
        if classify_subject(owner=bot_login, github_actor=bot_login, founder_ids=(FOUNDER_LOGIN,)) != SUBJECT_AGENT:
            raise AuthoritySplitError(REASON_IDENTITY_GAP)
        by_slug[slug] = item
    for slug in REQUIRED_APP_SLUGS:
        if slug not in by_slug:
            raise AuthoritySplitError(REASON_IDENTITY_GAP)
    for item in identities:
        if not isinstance(item, Mapping):
            raise AuthoritySplitError(REASON_IDENTITY_GAP)
        login = str(item.get("login") or "")
        kind = str(item.get("type") or "")
        if not login:
            raise AuthoritySplitError(REASON_IDENTITY_GAP)
        subject = classify_subject(
            owner=login,
            github_actor=login if kind == "Bot" else "",
            founder_ids=(FOUNDER_LOGIN,),
        )
        if subject != SUBJECT_AGENT:
            raise AuthoritySplitError(REASON_IDENTITY_GAP)
    reviewers = list(environment.get("required_reviewers") or [])
    branches = list(environment.get("deployment_branches") or [])
    if reviewers != [FOUNDER_LOGIN] or branches != ["main"]:
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    if process.get("lumos_write_gate_secret_present") or process.get("github_token_env_present"):
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    if process.get("ssh_dir_present"):
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    gh_account = str(process.get("gh_account") or "")
    if not gh_account or gh_account == FOUNDER_LOGIN:
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    return {
        "schema": SCHEMA,
        "ok": True,
        "settings_mutated": False,
        "dispatch": False,
        "merge": False,
        "grants_stage_a": False,
        "grants_stage_b": False,
        "founder": founder_login,
        "required_apps": list(REQUIRED_APP_SLUGS),
        "agent_logins": [str(item.get("login")) for item in identities if isinstance(item, Mapping)],
        "write_gate_reviewer": FOUNDER_LOGIN,
        "production_secret_in_agent_env": False,
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


def _identities_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m lumos_board.write_authority_split identities")
    parser.add_argument("--file", required=True)
    args = parser.parse_args(argv)
    payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise AuthoritySplitError(REASON_IDENTITY_GAP)
    report = evaluate_identity_evidence(payload)
    sys.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
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
            sys.stderr.write("usage: classify | secret-use | required-impact | identities | stages\n")
            return 2
        command, rest = argv[0], argv[1:]
        if command == "classify":
            return _classify_main(rest)
        if command == "secret-use":
            return _secret_main(rest)
        if command == "required-impact":
            return _impact_main(rest)
        if command == "identities":
            return _identities_main(rest)
        if command == "stages":
            sys.stdout.write(json.dumps(stage_authority_map(), ensure_ascii=False, sort_keys=True) + "\n")
            return 0
        raise AuthoritySplitError("bilinmeyen komut")
    except (ClaimError, OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(json.dumps({"error": str(exc)}, ensure_ascii=False) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
