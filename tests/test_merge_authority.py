"""Merge-authority verifier (ADR-035, TD-20): fail-closed, exact-scope signatures."""

import json
import subprocess
from pathlib import Path

import pytest

from merge_authority import verify as ma

REPO = "candasoz01-cmd/lumos-core"
SHA = "496a20c38ba7256e6b45ad4dc880b2c1a782747f"
OTHER_SHA = "4357f6df59e62fc9e6091eccac4cb63c7d3bbe89"


def keypair(directory: Path, name: str = "founder_key") -> tuple[Path, str]:
    key = directory / name
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    key_type, blob = (directory / f"{name}.pub").read_text().split()[:2]
    return key, f"{key_type} {blob}"


@pytest.fixture
def founder(tmp_path):
    key, pub = keypair(tmp_path)
    signers = tmp_path / "allowed_signers"
    signers.write_text(f'# comment\nfounder namespaces="{ma.NAMESPACE}" {pub}\n')
    return {"key": key, "signers": signers, "dir": tmp_path}


def sign(key: Path, payload: bytes, namespace: str = ma.NAMESPACE) -> str:
    data = key.parent / "payload.bin"
    data.write_bytes(payload)
    sig = data.with_name("payload.bin.sig")
    sig.unlink(missing_ok=True)
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", namespace, str(data)],
                   check=True, capture_output=True)
    return sig.read_text()


def envelope(signature: str, principal: str = "founder", **fields) -> str:
    values = {"repo": REPO, "pr": "889", "head_sha": SHA, "action": "merge", **fields}
    body = "\n".join(f"{k}: {v}" for k, v in values.items())
    return f"Onay.\n```\n{ma.ENVELOPE_MARKER}\nprincipal: {principal}\n{body}\n{signature}```\n"


def scope(**overrides) -> ma.Scope:
    return ma.Scope(**{"repo": REPO, "pr": 889, "head_sha": SHA, **overrides})


def test_exact_scope_signature_is_authorized(founder):
    text = envelope(sign(founder["key"], scope().payload()))
    verdict = ma.decide(scope(), [text], founder["signers"])
    assert verdict["authorized"] is True
    assert (verdict["reason"], verdict["principal"]) == ("SIGNED", "founder")


def test_new_head_sha_invalidates_approval(founder):
    text = envelope(sign(founder["key"], scope().payload()))
    verdict = ma.decide(scope(head_sha=OTHER_SHA), [text], founder["signers"])
    assert verdict["authorized"] is False
    assert verdict["rejected"] == ["SCOPE_MISMATCH: head_sha"]


@pytest.mark.parametrize("field,value", [("repo", "someone/fork"), ("pr", "890"),
                                         ("head_sha", OTHER_SHA), ("action", "deploy")])
def test_envelope_claiming_other_scope_is_rejected(founder, field, value):
    # Even a correct signature for the other scope cannot pass here.
    other = {"repo": REPO, "pr": 889, "head_sha": SHA, "action": "merge"}
    signed_for = dict(other, **{field: int(value) if field == "pr" else value})
    payload = (f"{ma.SCHEMA}\nrepo={signed_for['repo']}\npr={signed_for['pr']}\n"
               f"head_sha={signed_for['head_sha']}\naction={signed_for['action']}\n").encode()
    text = envelope(sign(founder["key"], payload), **{field: value})
    verdict = ma.decide(scope(), [text], founder["signers"])
    assert verdict["authorized"] is False
    assert verdict["rejected"] == [f"SCOPE_MISMATCH: {field}"]


def test_signature_for_other_sha_under_matching_fields_is_rejected(founder):
    # Fields claim this SHA, but the signature covers another one.
    text = envelope(sign(founder["key"], scope(head_sha=OTHER_SHA).payload()))
    verdict = ma.decide(scope(), [text], founder["signers"])
    assert verdict["rejected"] == ["SIGNATURE_INVALID"]


def test_publication_namespace_signature_is_not_merge_authority(founder):
    text = envelope(sign(founder["key"], scope().payload(), namespace="lumos-publication"))
    assert ma.decide(scope(), [text], founder["signers"])["rejected"] == ["SIGNATURE_INVALID"]


def test_unenrolled_key_cannot_approve(founder):
    rogue, _ = keypair(founder["dir"], "rogue_key")
    text = envelope(sign(rogue, scope().payload()))
    assert ma.decide(scope(), [text], founder["signers"])["rejected"] == ["SIGNATURE_INVALID"]


def test_principal_must_match_enrolled_identity(founder):
    text = envelope(sign(founder["key"], scope().payload()), principal="someone-else")
    assert ma.decide(scope(), [text], founder["signers"])["rejected"] == ["SIGNATURE_INVALID"]


def test_tampered_signature_is_rejected(founder):
    signature = sign(founder["key"], scope().payload())
    lines = signature.splitlines()
    lines[2] = lines[2][:-4] + ("AAAA" if not lines[2].endswith("AAAA") else "BBBB")
    text = envelope("\n".join(lines) + "\n")
    assert ma.decide(scope(), [text], founder["signers"])["authorized"] is False


def test_one_valid_among_invalid_envelopes_authorizes(founder):
    bad = envelope(sign(founder["key"], scope(head_sha=OTHER_SHA).payload()))
    good = envelope(sign(founder["key"], scope().payload()))
    verdict = ma.decide(scope(), ["no envelope here", bad, good], founder["signers"])
    assert verdict["authorized"] is True
    assert verdict["rejected"] == ["SIGNATURE_INVALID"]


def test_no_envelope_is_not_authorized(founder):
    verdict = ma.decide(scope(), ["LGTM", ""], founder["signers"])
    assert (verdict["authorized"], verdict["reason"]) == (False, "NO_VALID_APPROVAL")


def test_empty_trust_root_rejects_even_a_valid_signature(founder, tmp_path):
    text = envelope(sign(founder["key"], scope().payload()))
    empty = tmp_path / "empty_signers"
    empty.write_text("# nothing enrolled\n")
    verdict = ma.decide(scope(), [text], empty)
    assert (verdict["authorized"], verdict["reason"]) == (False, "NO_ENROLLED_SIGNER")


def test_missing_trust_root_is_fail_closed(founder, tmp_path):
    text = envelope(sign(founder["key"], scope().payload()))
    verdict = ma.decide(scope(), [text], tmp_path / "absent")
    assert (verdict["authorized"], verdict["reason"]) == (False, "TRUST_ROOT_INVALID")


def test_unparsable_root_line_is_fail_closed(founder):
    text = envelope(sign(founder["key"], scope().payload()))
    founder["signers"].write_text(founder["signers"].read_text() + "garbage-line\n")
    verdict = ma.decide(scope(), [text], founder["signers"])
    assert verdict["reason"] == "TRUST_ROOT_INVALID"
    assert verdict["rejected"] == ["TRUST_ROOT_UNPARSABLE: line 3"]


def test_revoked_key_in_root_is_fail_closed(founder, monkeypatch):
    fingerprint = subprocess.run(["ssh-keygen", "-lf", str(founder["key"]) + ".pub"],
                                 capture_output=True, text=True, check=True).stdout.split()[1]
    monkeypatch.setattr(ma, "REVOKED_SIGNER_FINGERPRINTS", {fingerprint})
    text = envelope(sign(founder["key"], scope().payload()))
    verdict = ma.decide(scope(), [text], founder["signers"])
    assert verdict["reason"] == "TRUST_ROOT_INVALID"
    assert verdict["rejected"][0].startswith(f"TRUST_ROOT_REVOKED: {fingerprint}")


def test_missing_ssh_keygen_is_fail_closed(founder, monkeypatch):
    text = envelope(sign(founder["key"], scope().payload()))
    monkeypatch.setattr(ma.shutil, "which", lambda _name: None)
    verdict = ma.decide(scope(), [text], founder["signers"])
    assert (verdict["authorized"], verdict["reason"]) == (False, "VERIFIER_UNAVAILABLE")


@pytest.mark.parametrize("overrides", [{"repo": "no-slash"}, {"pr": 0}, {"pr": True},
                                       {"head_sha": SHA[:12]}, {"head_sha": SHA.upper()},
                                       {"action": "deploy"}])
def test_invalid_scope_is_refused(overrides):
    with pytest.raises(ValueError, match="SCOPE_INVALID"):
        scope(**overrides)


def test_malformed_envelopes_are_ignored():
    assert ma.parse_envelopes(f"{ma.ENVELOPE_MARKER}\nprincipal: founder\nrepo: {REPO}\n") == []
    missing_field = f"{ma.ENVELOPE_MARKER}\nprincipal: x\nrepo: {REPO}\n{ma.SIG_BEGIN}\nAA\n{ma.SIG_END}\n"
    assert ma.parse_envelopes(missing_field) == []


def test_committed_trust_root_is_closed_by_default():
    assert ma.DEFAULT_SIGNERS.is_file()
    assert ma.enrolled_signer_lines(ma.DEFAULT_SIGNERS) == []
    assert ma.trust_root_problems(ma.DEFAULT_SIGNERS) == []
    assert ma.DEFAULT_SIGNERS.resolve() != (Path(ma.__file__).resolve().parents[2]
                                            / "config/publication/allowed_signers").resolve()


def test_cli_exit_codes(founder, tmp_path, capsys):
    good = tmp_path / "good.txt"
    good.write_text(envelope(sign(founder["key"], scope().payload())))
    base = ["--repo", REPO, "--pr", "889", "--signers", str(founder["signers"])]
    assert ma.main([*base, "--head-sha", SHA, "--envelopes", str(good)]) == 0
    assert json.loads(capsys.readouterr().out)["authorized"] is True
    assert ma.main([*base, "--head-sha", OTHER_SHA, "--envelopes", str(good)]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "NO_VALID_APPROVAL"
    assert ma.main([*base, "--head-sha", "not-a-sha"]) == 2
    assert "SCOPE_INVALID" in capsys.readouterr().err
