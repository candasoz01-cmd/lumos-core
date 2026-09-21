"""Lumos Duvar v1 sözleşmesi kilit testleri.

Yeni claim mekanizması yok: kapı `claim_cli` / `task_claim.ClaimStatus`.
Anayasa maddeleri sözleşmede kopyalanmaz, referans verilir.
"""

from __future__ import annotations

from pathlib import Path

from lumos_board.task_claim import ClaimStatus

_REPO = Path(__file__).resolve().parents[1]
_CONTRACT = _REPO / "docs" / "contracts" / "lumos-wall-v1.md"
_ADR = _REPO / "docs" / "decisions" / "ADR-032-lumos-wall-v1.md"
_CLAIM_CLI = _REPO / "src" / "lumos_board" / "claim_cli.py"


def test_wall_v1_eight_articles_and_law_are_locked() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "Duvar'da kaydı olmayan iş, Lumos açısından yürütülen iş sayılmaz." in text
    for heading in (
        "### 1. Tek aktif sahip",
        "### 2. Claim zorunluluğu",
        "### 3. Çalışma alanı beyanı",
        "### 4. Durum makinesi",
        "### 5. Kanıt zorunluluğu",
        "### 6. Çakışma koruması",
        "### 7. Kurucu kapısı",
        "### 8. Gürültü ayıklama",
    ):
        assert heading in text, heading
    assert (
        "INBOX → CLAIMED → WORKING → TEST → FOUNDER_REVIEW → READY → CLOSED" in text
    )
    assert "Yan durumlar: `BLOCKED`, `PARKED`." in text
    assert "karar" in text and "risk" in text and "blokaj" in text and "tamamlanma" in text


def test_wall_v1_status_in_force_and_mapping_is_founder_locked() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    # 2026-09-19 kurucu onayı: sözleşme yürürlükte.
    assert "Yürürlükte — 2026-09-19 kurucu onayı" in text
    assert "TASLAK" not in text
    # 2026-09-18 kurucu alt kararları:
    assert "| `READY` | `ACTIVE` |" in text
    assert "| `PARKED` | `RELEASED` |" in text
    assert "| `BLOCKED` | `ACTIVE` |" in text
    assert "Duvar = Lumos Board'un iç operasyon yüzü" in text
    # #863'ten taşınan analizler kanonik metinde:
    assert "## Mevcut semantikle çelişki kontrolü" in text
    assert "## Mevcut altyapıyla eşleme" in text
    assert "**KISMİ**" in text and "**VAR**" in text


def test_wall_v1_reuses_claim_cli_not_a_second_lease() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert (
        "`claim_cli` tek yetkili yazma/claim kapısıdır; Duvar, claim durumunu tüketir ve gösterir, ayrı claim üretmez."
        in text
    )
    assert (
        "görev durumu, sahiplik, kanıt, çakışma ve kurucu"
        in text
    )
    assert "iş mantığı UI'ya dağılmaz" in text
    assert "İkinci `TaskClaimStore` veya `claim_cli` çatalı" in text
    assert _CLAIM_CLI.is_file()
    cli = _CLAIM_CLI.read_text(encoding="utf-8")
    assert "from lumos_board.task_claim import" in cli
    assert {s.value for s in ClaimStatus} == {
        "ACTIVE",
        "QUEUED",
        "RELEASED",
        "EXPIRED",
        "OVERRIDDEN",
    }


def test_wall_v1_references_constitution_without_copying_articles() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "[CONSTITUTION.md](../CONSTITUTION.md)" in text
    assert "§3" in text and "§9" in text and "§10" in text and "§11" in text
    # Anayasa maddelerinin gövdesi kopyalanmaz.
    assert "Tek merkez, dört belge" not in text
    assert "Tek kontrollü çekirdek yazıcısı" not in text
    assert "Kullanıcı yalnız dört şey görür" not in text


def test_adr_032_exists_and_forbids_parallel_stack() -> None:
    text = _ADR.read_text(encoding="utf-8")
    assert "Accepted (2026-09-19)" in text
    assert "Proposed" not in text
    assert "lumos-wall-v1.md" in text
    assert "ayrı claim üretmez" in text
    assert "Görsel yüz" in text
    assert "görev durumu, sahiplik, kanıt, çakışma ve kurucu kapısını" in text
    assert "iş mantığı UI'ya dağılmaz" in text
    assert "sözleşme gereksinimidir" in text
    assert "minimal kayıt deposu" in text


def test_wall_v1_approval_schema_fields_and_limits_are_locked() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "## Onay şeması v1 (sözleşme gereksinimi)" in text
    for field in (
        "`approval_id`",
        "`task`",
        "`gate`",
        "`action`",
        "`head_sha`",
        "`approved_by`",
    ):
        assert field in text, field
    assert "Aynı geçerli onay tekrar sorulmaz" in text
    assert "Ajan, bot veya App bu alanı insan onayı olarak dolduramaz" in text
    assert "ikinci insan şartı yoktur" in text
    assert "anayasa farkı ayrı açık karardır" in text
    assert "Yayın güvenliği" in text and "bu eke izin bağlanmaz" in text
    # 2026-09-20 dilimi: minimal depo/CLI uygulandı; imza kökü hâlâ kapalı.
    assert "`lumos_board.founder_approval`" in text
    assert "fail-closed" in text
    assert "yayın güvenlik kökü **hâlâ açılmaz.**" in text
    # Override HMAC lease kapısı ayrı kalır; şema onu genişletmez.
    assert "Override, aşağıdaki onay" in text or "claim override HMAC" in text
    adr = _ADR.read_text(encoding="utf-8")
    assert "onay-şeması imza kökü/CheckRun" in adr
    assert "anayasa yazımı" in adr


def test_wall_v1_approval_schema_implementation_exists() -> None:
    module = _REPO / "src" / "lumos_board" / "founder_approval.py"
    assert module.is_file()
    source = module.read_text(encoding="utf-8")
    for field in ('"approval_id"', '"task"', '"gate"', '"action"', '"head_sha"', '"approved_by"'):
        assert field in source, field
    cli = _CLAIM_CLI.read_text(encoding="utf-8")
    assert 'subparsers.add_parser("approval")' in cli
    assert "LUMOS_FOUNDER_APPROVER_REGISTRY" in cli
