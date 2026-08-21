"""ADR-028 standing-class classifier — fail-closed; #777 is the fixture."""

from __future__ import annotations

from standing_merge.classify import (
    CLASS_ELIGIBLE,
    CLASS_EXCLUDED,
    CLASS_SEMANTIC,
    SemanticAttestation,
    PR777_PATHS,
    classify_paths,
    main,
)


def test_pr777_fixture_is_excluded() -> None:
    verdict = classify_paths(PR777_PATHS)
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["standing_merge"] is False
    assert verdict["human_merge_required"] is True
    assert any(hit["reason"].startswith("prefix:docs/contracts/") for hit in verdict["hits"])


def test_debt_register_only_is_eligible() -> None:
    verdict = classify_paths(["docs/TECHNICAL_DEBT.md"])
    assert verdict["class"] == CLASS_ELIGIBLE
    assert verdict["standing_merge"] is True
    assert verdict["human_merge_required"] is False
    assert verdict["unknown"] == []


def test_generic_docs_file_is_semantic_review_not_eligible() -> None:
    """Genel docs/ allowlist'i kaldırıldı: isim listesinden kaçan belge
    otomatik standing kazanamaz, semantik incelemeye düşer."""
    verdict = classify_paths(["docs/getting-started.md"])
    assert verdict["class"] == CLASS_SEMANTIC
    assert verdict["standing_merge"] is False


def test_empty_diff_is_excluded() -> None:
    verdict = classify_paths([])
    assert verdict["class"] == CLASS_EXCLUDED
    assert "empty_diff" in verdict["reasons"]


def test_adr028_itself_is_excluded() -> None:
    verdict = classify_paths(
        ["docs/decisions/ADR-028-standing-low-risk-merge-approval.md"]
    )
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["standing_merge"] is False


def test_constitution_is_excluded() -> None:
    verdict = classify_paths(["docs/CONSTITUTION.md"])
    assert verdict["class"] == CLASS_EXCLUDED


def test_security_code_is_hard_excluded() -> None:
    verdict = classify_paths(["src/security/permissions.py"])
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["standing_merge"] is False
    assert any("src/security/" in hit["reason"] for hit in verdict["hits"])


def test_unlisted_code_is_fail_closed() -> None:
    verdict = classify_paths(["src/dashboard_health/watch.py"])
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["unknown"] == ["src/dashboard_health/watch.py"]
    assert any(hit["reason"] == "unlisted:src/dashboard_health/watch.py" for hit in verdict["hits"])


def test_hard_exclude_wins_over_docs_allowlist() -> None:
    verdict = classify_paths(
        ["docs/TECHNICAL_DEBT.md", "docs/contracts/dashboard-health-v1.md"]
    )
    assert verdict["class"] == CLASS_EXCLUDED
    assert any("docs/contracts/" in hit["reason"] for hit in verdict["hits"])


def test_cli_exits_two_when_excluded() -> None:
    assert main(["src/security/identity.py"]) == 2


def test_cli_exits_zero_when_eligible() -> None:
    assert main(["docs/TECHNICAL_DEBT.md"]) == 0


def test_policy_code_is_hard_excluded() -> None:
    verdict = classify_paths(["src/policy/action_policy.py"])
    assert verdict["class"] == CLASS_EXCLUDED
    assert any("src/policy/" in hit["reason"] for hit in verdict["hits"])


def test_security_named_doc_under_docs_is_hard_excluded() -> None:
    verdict = classify_paths(["docs/lumos-persona-security-checkpoint.md"])
    assert verdict["class"] == CLASS_EXCLUDED
    assert any(hit["reason"] == "token:security" for hit in verdict["hits"])


def test_privacy_named_doc_is_hard_excluded() -> None:
    verdict = classify_paths(["docs/analysis/lumos-privacy-manifesto-draft.md"])
    assert verdict["class"] == CLASS_EXCLUDED
    assert any(hit["reason"] == "token:privacy" for hit in verdict["hits"])


def test_permission_memory_doc_is_hard_excluded() -> None:
    verdict = classify_paths(["docs/memory/external-integrations-permissions.md"])
    assert verdict["class"] == CLASS_EXCLUDED


def test_adr023_is_semantic_review_not_auto_eligible() -> None:
    """Aynı dosyada hem olgu düzeltmesi (#788) hem yetki normu (#784) olabilir.
    Yol bunu ayıramaz: makine eligible demez, insan semantik olarak karar verir."""
    verdict = classify_paths(
        ["docs/decisions/ADR-023-lumos-representative-avatar.md"]
    )
    assert verdict["class"] == CLASS_SEMANTIC
    assert verdict["standing_merge"] is False
    assert verdict["semantic_review_required"] is True


def test_adr009_stays_open_to_factual_standing_via_semantic_review() -> None:
    """#786 ilkesi korunuyor: ADR'de salt olgu düzeltmesi standing'e girebilir.
    docs/decisions/ komple excluded YAPILMADI; semantic_review kapısından geçer."""
    verdict = classify_paths(
        ["docs/decisions/ADR-009-mail-address-and-domain-boundary.md"]
    )
    assert verdict["class"] == CLASS_SEMANTIC


def test_tests_prefix_is_allowed_unless_hard_excluded() -> None:
    verdict = classify_paths(["tests/test_representative_ingress.py"])
    assert verdict["class"] == CLASS_ELIGIBLE


def test_merge_named_test_file_is_hard_excluded() -> None:
    """Jeton savunması tests/ allowlist'inin de önünde: merge kuralına dokunan
    dosya adı standing'e giremez."""
    verdict = classify_paths(["tests/test_standing_merge_classify.py"])
    assert verdict["class"] == CLASS_EXCLUDED
    assert any(hit["reason"] == "token:merge" for hit in verdict["hits"])


def test_security_named_test_is_hard_excluded() -> None:
    verdict = classify_paths(["tests/test_security_never_auto_engine.py"])
    assert verdict["class"] == CLASS_EXCLUDED
    assert any(hit["reason"] == "token:security" for hit in verdict["hits"])


# --- Üç durumlu model: kurucu fixture'ları (2026-08-21) ---


def test_adr029_is_hard_excluded() -> None:
    """TD-20 / #777 olayının ADR'si. Governance-sorumluluk niteliği nedeniyle
    semantic_review'a bile düşmez; doğrudan excluded."""
    verdict = classify_paths(
        ["docs/decisions/ADR-029-dashboard-health-earned-responsibility.md"]
    )
    assert verdict["class"] == CLASS_EXCLUDED
    assert any("ADR-029" in hit["reason"] for hit in verdict["hits"])


def test_new_merge_rules_doc_cannot_become_eligible() -> None:
    """docs/merge-rules.md isim listesinde yok; yine de eligible olamaz."""
    verdict = classify_paths(["docs/merge-rules.md"])
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["standing_merge"] is False


def test_new_data_boundary_doc_cannot_become_eligible() -> None:
    """Veri sınırı belgesi isim listesinden kaçsa bile eligible olamaz."""
    verdict = classify_paths(["docs/data-boundary-policy-notes.md"])
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["standing_merge"] is False


def test_unknown_governance_doc_falls_to_semantic_not_eligible() -> None:
    """Hiçbir jetona çarpmayan yeni docs/ belgesi bile eligible olmaz."""
    verdict = classify_paths(["docs/yeni-calisma-duzeni.md"])
    assert verdict["class"] == CLASS_SEMANTIC
    assert verdict["standing_merge"] is False


def test_excluded_wins_over_semantic() -> None:
    verdict = classify_paths(
        [
            "docs/decisions/ADR-009-mail-address-and-domain-boundary.md",
            "src/security/identity.py",
        ]
    )
    assert verdict["class"] == CLASS_EXCLUDED


def test_semantic_wins_over_eligible() -> None:
    verdict = classify_paths(
        [
            "tests/test_representative_ingress.py",
            "docs/decisions/ADR-009-mail-address-and-domain-boundary.md",
        ]
    )
    assert verdict["class"] == CLASS_SEMANTIC


def test_cli_exits_three_when_semantic_review() -> None:
    assert main(["docs/decisions/ADR-023-lumos-representative-avatar.md"]) == 3


# --- semantic_review → standing geçişi (attestation, head SHA'ya bağlı) ---

ADR023 = "docs/decisions/ADR-023-lumos-representative-avatar.md"
ADR029 = "docs/decisions/ADR-029-dashboard-health-earned-responsibility.md"
HEAD = "89bc0651f0a1b2c3d4e5f60718293a4b5c6d7e8f"


def _attest(verdict: str, sha: str = HEAD) -> SemanticAttestation:
    return SemanticAttestation(verdict=verdict, head_sha=sha, evaluated_by="test")


def test_factual_attestation_promotes_adr023_to_standing_candidate() -> None:
    """#786 ilkesi yürütmede de çalışıyor: salt olgu düzeltmesi standing'e girer.
    semantic_review kalıcı bir yasak değil, karar verilmemiş durumdur."""
    verdict = classify_paths(
        [ADR023], attestation=_attest("factual"), head_sha=HEAD
    )
    assert verdict["class"] == CLASS_ELIGIBLE
    assert verdict["standing_merge"] is True
    assert verdict["attestation"] == "factual"


def test_normative_attestation_demotes_adr023_to_excluded() -> None:
    """#784 türü yetki normu: semantik değerlendirme norm derse standing kapanır."""
    verdict = classify_paths(
        [ADR023], attestation=_attest("normative"), head_sha=HEAD
    )
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["human_merge_required"] is True


def test_attestation_bound_to_another_sha_does_not_carry_over() -> None:
    verdict = classify_paths(
        [ADR023], attestation=_attest("factual", "deadbeef"), head_sha=HEAD
    )
    assert verdict["class"] == CLASS_SEMANTIC
    assert verdict["attestation"] == "stale"
    assert "attestation_sha_mismatch" in verdict["reasons"]


def test_attestation_without_head_sha_is_fail_closed() -> None:
    verdict = classify_paths([ADR023], attestation=_attest("factual"), head_sha=None)
    assert verdict["class"] == CLASS_SEMANTIC


def test_unknown_verdict_string_is_not_a_decision() -> None:
    verdict = classify_paths([ADR023], attestation=_attest("maybe"), head_sha=HEAD)
    assert verdict["class"] == CLASS_SEMANTIC
    assert verdict["attestation"] == "unknown"


def test_attestation_cannot_promote_hard_exclusion_adr029() -> None:
    """ADR-029 governance: hiçbir semantik değerlendirme onu standing'e sokamaz."""
    verdict = classify_paths(
        [ADR029], attestation=_attest("factual"), head_sha=HEAD
    )
    assert verdict["class"] == CLASS_EXCLUDED
    assert verdict["attestation"] == "ignored_hard_exclusion"


def test_attestation_cannot_promote_unlisted_path() -> None:
    verdict = classify_paths(
        ["some/unknown/path.py"], attestation=_attest("factual"), head_sha=HEAD
    )
    assert verdict["class"] == CLASS_EXCLUDED


def test_cli_attestation_promotes_and_exits_zero() -> None:
    assert (
        main([ADR023, "--head-sha", HEAD, "--attest", "factual", "--attest-sha", HEAD])
        == 0
    )


def test_cli_attestation_on_adr029_still_exits_two() -> None:
    assert (
        main([ADR029, "--head-sha", HEAD, "--attest", "factual", "--attest-sha", HEAD])
        == 2
    )
