"""ADR-028 kanıt kimliği: CheckRun adı authority değildir.

Canlı vaka: #793 aynı commit üzerinde `standing-class` adlı İKİ run üretti —
biri trusted `pull_request_target` bağlamından kırmızı, biri PR'ın kendi
yazdığı `on: pull_request` workflow'undan yeşil.
"""

from __future__ import annotations

from standing_merge.trusted_run import (
    CANONICAL_WORKFLOW_PATH,
    CheckRunRecord,
    standing_evidence,
)

PR = 793
HEAD = "4abeefa1111111111111111111111111111111111"
BASE = "1f0fae0222222222222222222222222222222222"
CTX = {"pull_request_number": PR, "head_sha": HEAD, "base_sha": BASE}


def _run(**kw) -> CheckRunRecord:
    defaults = dict(
        name="standing-class",
        event="pull_request_target",
        workflow_path=CANONICAL_WORKFLOW_PATH,
        conclusion="success",
        head_sha=HEAD,
        base_sha=BASE,
        pull_request_number=PR,
        workflow_ref=f"candasoz01-cmd/lumos-core/{CANONICAL_WORKFLOW_PATH}@refs/heads/main",
    )
    defaults.update(kw)
    return CheckRunRecord(**defaults)


# --- #793'ün gerçek senaryosu ---


def test_forged_green_does_not_authorize_when_trusted_run_failed() -> None:
    """Aynı SHA'da: sahte pull_request+SUCCESS, trusted target+FAILURE.

    Sonuç kesinlikle standing eligible OLMAMALI."""
    forged = _run(event="pull_request", conclusion="success")
    trusted = _run(conclusion="failure")
    verdict = standing_evidence([forged, trusted], **CTX)
    assert verdict["standing_authorized"] is False
    assert verdict["reason"] == "trusted_run_not_success"


def test_trusted_success_authorizes() -> None:
    verdict = standing_evidence([_run()], **CTX)
    assert verdict["standing_authorized"] is True
    assert verdict["reason"] == "trusted_success"


def test_forged_green_alone_is_not_authority() -> None:
    verdict = standing_evidence(
        [_run(event="pull_request", conclusion="success")], **CTX
    )
    assert verdict["standing_authorized"] is False
    assert verdict["reason"] == "no_trusted_run"


def test_renaming_the_forged_run_does_not_help_the_attacker() -> None:
    """İsim benzersizleştirme güvenlik sınırı değildir: saldırgan da o adı verir."""
    verdict = standing_evidence(
        [
            _run(
                name="standing-class-trusted",
                event="pull_request",
                conclusion="success",
            )
        ],
        **CTX,
    )
    assert verdict["standing_authorized"] is False


# --- Beş özelliğin her biri tek başına bağlayıcı ---


def test_non_canonical_workflow_is_rejected() -> None:
    verdict = standing_evidence(
        [_run(workflow_path=".github/workflows/evil.yml")], **CTX
    )
    assert verdict["standing_authorized"] is False


def test_workflow_ref_outside_base_branch_is_rejected() -> None:
    verdict = standing_evidence(
        [_run(workflow_ref="o/r/x.yml@refs/heads/attacker-branch")], **CTX
    )
    assert verdict["standing_authorized"] is False


def test_missing_workflow_ref_is_fail_closed() -> None:
    """Kanıt yokluğu kanıt değildir."""
    verdict = standing_evidence([_run(workflow_ref="")], **CTX)
    assert verdict["standing_authorized"] is False


def test_head_sha_mismatch_is_rejected() -> None:
    verdict = standing_evidence([_run(head_sha="deadbeef")], **CTX)
    assert verdict["standing_authorized"] is False


def test_base_sha_mismatch_is_rejected() -> None:
    verdict = standing_evidence([_run(base_sha="deadbeef")], **CTX)
    assert verdict["standing_authorized"] is False


def test_other_pull_request_run_is_rejected() -> None:
    verdict = standing_evidence([_run(pull_request_number=1)], **CTX)
    assert verdict["standing_authorized"] is False


def test_empty_run_list_is_fail_closed() -> None:
    verdict = standing_evidence([], **CTX)
    assert verdict["standing_authorized"] is False
    assert verdict["reason"] == "no_trusted_run"


def test_forged_green_cannot_mask_trusted_red_even_if_listed_first() -> None:
    """Sıra önemli değil: trusted run ada veya lehte sonuca göre seçilmez."""
    forged = _run(event="pull_request", conclusion="success")
    trusted = _run(conclusion="failure")
    assert standing_evidence([forged, trusted], **CTX)["standing_authorized"] is False
    assert standing_evidence([trusted, forged], **CTX)["standing_authorized"] is False
