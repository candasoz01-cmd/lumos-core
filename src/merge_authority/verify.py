"""Deterministic merge-authority verifier (ADR-035, TD-20).

Answers one question: did a human-gated merge-authority key sign exactly this
``repo + PR + head SHA + action``? It decides nothing else, holds no key and
grants nothing. The GitHub account that delivers an envelope is never the
trust root; only an SSH signature that verifies against the trusted
``allowed_signers`` counts.

The verifier is carrier-agnostic. An envelope is plain text; how it reaches
the verifier (PR comment, GitHub App, device upload) is a carrier decision
outside this module. The signed payload is always rebuilt from the trusted
scope, never taken from the envelope, so a signature for another PR, SHA or
action cannot be replayed here.

Fail-closed: a missing or invalid trust root, an empty root, a missing
``ssh-keygen``, a malformed envelope or any verification error means
``authorized: false``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "lumos.merge_authority.v1"
VERDICT_SCHEMA = "lumos.merge_authority.verdict.v1"
ENVELOPE_MARKER = "lumos-merge-authority-v1"
# Distinct from the publication namespace: a publication signature can never
# stand in for merge authority, and vice versa.
NAMESPACE = "lumos-merge-authority"
ACTIONS = ("merge",)
DEFAULT_SIGNERS = (Path(__file__).resolve().parents[2]
                   / "config" / "merge_authority" / "allowed_signers")

# An agent-reachable key proves no human authority. Carried over from the
# publication gate's revocation (2026-09-18); removal is a founder decision.
REVOKED_SIGNER_FINGERPRINTS = {
    "SHA256:fCmMHAEP2k865znMPpzZdBZEdEVSLQVST9WT/hHhNHc",
}

SSH_KEY_TYPE_PREFIXES = ("ssh-", "ecdsa-", "sk-")
SIG_BEGIN = "-----BEGIN SSH SIGNATURE-----"
SIG_END = "-----END SSH SIGNATURE-----"
# Bounds the work an unauthenticated flood of envelopes can cause.
MAX_ENVELOPES = 100

_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_PRINCIPAL_RE = re.compile(r"^[A-Za-z0-9._@+-]{1,128}$")
_FIELDS = ("repo", "pr", "head_sha", "action")


@dataclass(frozen=True)
class Scope:
    repo: str
    pr: int
    head_sha: str
    action: str = "merge"

    def __post_init__(self):
        if not _REPO_RE.match(self.repo):
            raise ValueError("SCOPE_INVALID: repo")
        if isinstance(self.pr, bool) or not isinstance(self.pr, int) or self.pr <= 0:
            raise ValueError("SCOPE_INVALID: pr")
        if not _SHA_RE.match(self.head_sha):
            raise ValueError("SCOPE_INVALID: head_sha")
        if self.action not in ACTIONS:
            raise ValueError("SCOPE_INVALID: action")

    def payload(self) -> bytes:
        return (f"{SCHEMA}\nrepo={self.repo}\npr={self.pr}\n"
                f"head_sha={self.head_sha}\naction={self.action}\n").encode()


@dataclass(frozen=True)
class Envelope:
    principal: str
    fields: dict
    signature: str


def parse_envelopes(text: str) -> list[Envelope]:
    """Extract every well-formed envelope from ``text``; malformed ones are dropped."""
    lines = [line.strip() for line in text.splitlines()]
    found: list[Envelope] = []
    i = 0
    while i < len(lines):
        if lines[i] != ENVELOPE_MARKER:
            i += 1
            continue
        i += 1
        fields: dict = {}
        principal = ""
        while i < len(lines) and lines[i] != SIG_BEGIN and lines[i] != ENVELOPE_MARKER:
            key, sep, value = lines[i].partition(":")
            key, value = key.strip(), value.strip()
            if sep and key == "principal":
                principal = value
            elif sep and key in _FIELDS and key not in fields:
                fields[key] = value
            i += 1
        if i >= len(lines) or lines[i] != SIG_BEGIN:
            continue
        start = i
        while i < len(lines) and lines[i] != SIG_END:
            i += 1
        if i >= len(lines):
            break
        signature = "\n".join(lines[start:i + 1]) + "\n"
        i += 1
        if principal and set(fields) == set(_FIELDS):
            found.append(Envelope(principal, fields, signature))
    return found


def enrolled_signer_lines(signers: Path) -> list[str]:
    if not signers.is_file():
        return []
    return [line.strip() for line in signers.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")]


def _fingerprint(key_type: str, blob: str) -> str | None:
    try:
        result = subprocess.run(["ssh-keygen", "-lf", "-"],
                                input=f"{key_type} {blob}\n".encode(),
                                capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    parts = result.stdout.decode(errors="replace").split()
    if result.returncode == 0 and len(parts) >= 2 and parts[1].startswith("SHA256:"):
        return parts[1]
    return None


def trust_root_problems(signers: Path) -> list[str]:
    """Every enrolled line must resolve to a key that is not revoked."""
    if not signers.is_file():
        return ["TRUST_ROOT_MISSING"]
    problems = []
    for lineno, line in enumerate(signers.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        prints = [_fingerprint(parts[k], parts[k + 1]) for k in range(1, len(parts) - 1)
                  if parts[k].startswith(SSH_KEY_TYPE_PREFIXES)]
        prints = [p for p in prints if p]
        if not prints:
            problems.append(f"TRUST_ROOT_UNPARSABLE: line {lineno}")
        problems.extend(f"TRUST_ROOT_REVOKED: {p} line {lineno}"
                        for p in prints if p in REVOKED_SIGNER_FINGERPRINTS)
    return problems


def verify_envelope(envelope: Envelope, scope: Scope, signers: Path) -> str | None:
    """Return None when the envelope authorizes ``scope``, else the rejection reason."""
    expected = {"repo": scope.repo, "pr": str(scope.pr),
                "head_sha": scope.head_sha, "action": scope.action}
    for key in _FIELDS:
        if envelope.fields.get(key) != expected[key]:
            return f"SCOPE_MISMATCH: {key}"
    if not _PRINCIPAL_RE.match(envelope.principal):
        return "PRINCIPAL_INVALID"
    with tempfile.TemporaryDirectory() as tmp:
        sig = Path(tmp) / "envelope.sig"
        sig.write_text(envelope.signature, encoding="utf-8")
        try:
            result = subprocess.run(
                ["ssh-keygen", "-Y", "verify", "-f", str(signers), "-I", envelope.principal,
                 "-n", NAMESPACE, "-s", str(sig)],
                input=scope.payload(), capture_output=True, timeout=30, check=False)
        except (OSError, subprocess.SubprocessError):
            return "SIGNATURE_UNVERIFIABLE"
    return None if result.returncode == 0 else "SIGNATURE_INVALID"


def decide(scope: Scope, texts: list[str], signers: Path = DEFAULT_SIGNERS) -> dict:
    verdict = {"schema": VERDICT_SCHEMA, "repo": scope.repo, "pr": scope.pr,
               "head_sha": scope.head_sha, "action": scope.action,
               "authorized": False, "reason": "", "principal": "", "rejected": []}
    if shutil.which("ssh-keygen") is None:
        verdict["reason"] = "VERIFIER_UNAVAILABLE"
        return verdict
    problems = trust_root_problems(signers)
    if problems:
        verdict.update(reason="TRUST_ROOT_INVALID", rejected=problems)
        return verdict
    if not enrolled_signer_lines(signers):
        verdict["reason"] = "NO_ENROLLED_SIGNER"
        return verdict
    envelopes = [env for text in texts for env in parse_envelopes(text)][-MAX_ENVELOPES:]
    for envelope in envelopes:
        reason = verify_envelope(envelope, scope, signers)
        if reason is None:
            verdict.update(authorized=True, reason="SIGNED", principal=envelope.principal)
            return verdict
        verdict["rejected"].append(reason)
    verdict["reason"] = "NO_VALID_APPROVAL"
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--action", default="merge")
    parser.add_argument("--signers", type=Path, default=DEFAULT_SIGNERS)
    parser.add_argument("--envelopes", type=Path, action="append", default=[],
                        help="text file holding zero or more envelopes (repeatable)")
    args = parser.parse_args(argv)
    try:
        scope = Scope(args.repo, args.pr, args.head_sha, args.action)
        texts = [path.read_text(encoding="utf-8") for path in args.envelopes]
    except (ValueError, OSError) as exc:
        print(json.dumps({"schema": VERDICT_SCHEMA, "authorized": False,
                          "reason": str(exc)}), file=sys.stderr)
        return 2
    verdict = decide(scope, texts, args.signers)
    print(json.dumps(verdict, ensure_ascii=False))
    return 0 if verdict["authorized"] else 2


if __name__ == "__main__":
    sys.exit(main())
