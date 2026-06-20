"""Phase 1 + EC2-01 v1: panel görev sil/geri al — parse + UX wiring (panel.astro ile hizalı)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"

PANEL_GOREV_DELETE_RESTORE_HINT = (
    ' Geri almak için «görev geri al» yazabilir veya Görevler\'de «Son silineni geri al» kullan.'
)
PANEL_GOREV_DELETE_RESTORE_HINT_ASTRO_SNIPPET = "Görevler\\'de «Son silineni geri al»"
PANEL_GOREV_NOT_FOUND_PREFIX = "Görev bulunamadı: «"
PANEL_GOREV_RESTORE_VERIFY_FAIL = "Görev listesine eklenemedi; geri alma doğrulanamadı."


def _canonicalize_task_input(raw: str) -> str:
    s = str(raw or "").strip()
    s = re.sub(r"\bgorev\b", "görev", s, flags=re.I)
    s = re.sub(r"\bolustur\b", "oluştur", s, flags=re.I)
    return s.lower().strip()


def parse_panel_gorev_sil(raw: str) -> dict[str, str] | None:
    """panel.astro parsePanelGorevKomutu sil dalının Python aynası."""
    s0 = str(raw or "").strip()
    if not s0:
        return None
    s = _canonicalize_task_input(s0)
    m = re.match(r"^(?:görev|gorev)\s+sil(?=\s|:|$)", s, re.I)
    if not m:
        return None
    ref = re.sub(r"^\s*:+\s*", "", s[m.end() :]).strip()
    return {"verb": "sil", "ref": ref}


def parse_panel_gorev_geri_al(raw: str) -> dict[str, str] | None:
    """panel.astro parsePanelGorevKomutu geri_al dalının Python aynası."""
    s0 = str(raw or "").strip()
    if not s0:
        return None
    s = _canonicalize_task_input(s0)
    m = re.match(r"^(?:görev|gorev)\s+geri\s+al(?=\s|:|$)", s, re.I)
    if not m:
        return None
    ref = re.sub(r"^\s*:+\s*", "", s[m.end() :]).strip()
    return {"verb": "geri_al", "ref": ref}


def build_gorevler_not_found_message(ref: str) -> str:
    r = str(ref or "").strip()
    return f"{PANEL_GOREV_NOT_FOUND_PREFIX}{r}». Başlık veya görev kimliği (tsk_…) kontrol edin."


def build_gorev_delete_success_message(title_or_ref: str) -> str:
    t = str(title_or_ref or "").strip()
    return f'Görev silindi: "{t}".{PANEL_GOREV_DELETE_RESTORE_HINT}'


def test_parse_panel_gorev_sil_basic() -> None:
    assert parse_panel_gorev_sil("görev sil alışveriş") == {"verb": "sil", "ref": "alışveriş"}
    assert parse_panel_gorev_sil("gorev sil: tsk_abc") == {"verb": "sil", "ref": "tsk_abc"}
    assert parse_panel_gorev_sil("görev sil") == {"verb": "sil", "ref": ""}


def test_parse_panel_gorev_sil_not_create() -> None:
    assert parse_panel_gorev_sil("görev oluştur alışveriş") is None
    assert parse_panel_gorev_sil("mini görev ekle test") is None


def test_parse_panel_gorev_geri_al_basic() -> None:
    assert parse_panel_gorev_geri_al("görev geri al") == {"verb": "geri_al", "ref": ""}
    assert parse_panel_gorev_geri_al("gorev geri al: tsk_abc") == {"verb": "geri_al", "ref": "tsk_abc"}
    assert parse_panel_gorev_geri_al("görev geri al alışveriş") == {
        "verb": "geri_al",
        "ref": "alışveriş",
    }


def test_parse_panel_gorev_geri_al_not_sil() -> None:
    assert parse_panel_gorev_geri_al("görev sil alışveriş") is None
    assert parse_panel_gorev_sil("görev geri al") is None


def test_delete_success_message_includes_restore_hint() -> None:
    msg = build_gorev_delete_success_message("Alışveriş listesi")
    assert "Görev silindi:" in msg
    assert PANEL_GOREV_DELETE_RESTORE_HINT in msg
    assert "görev geri al" in msg


def test_not_found_message_includes_ref_not_raw_error_code() -> None:
    msg = build_gorevler_not_found_message("yok-ref")
    assert msg == (
        "Görev bulunamadı: «yok-ref». Başlık veya görev kimliği (tsk_…) kontrol edin."
    )
    assert "not_found" not in msg


def test_panel_astro_ec2_01_silme_ux_wiring() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    required = [
        'verb: "geri_al"',
        "panelGorevlerRestoreFromChat",
        "restoreGorevlerTaskFromChat",
        "function panelGorevDeleteRestoreHint(",
        'panelT("panel.modules.chat.gorev.deleteRestoreHint")',
        "buildGorevlerNotFoundMessage",
        "refreshPanelEvidenceStripIfReady",
        "panelGorevlerRestoreFromChat = restoreGorevlerTaskFromChat",
    ]
    for token in required:
        assert token in text, f"missing panel.astro token: {token}"
    assert text.count("refreshPanelEvidenceStripIfReady()") >= 4


def test_panel_astro_restore_chat_verifies_list_presence() -> None:
    """Chat restore başarısı yalnızca görev listesinde doğrulama sonrası."""
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    restore_fn = text.split("async function restoreGorevlerTaskFromChat", 1)[1].split(
        "panelGorevlerTasksRender = render", 1
    )[0]
    assert "gorevlerRestoreVerifyRef" in restore_fn
    assert "gorevlerTaskPresentInList" in restore_fn
    assert "findGorevlerTaskIndexByRef" in text.split("function gorevlerTaskPresentInList", 1)[1].split(
        "function finishDeleteGorevlerTaskLocal", 1
    )[0]
    assert "await restoreLastGorevlerTask();" in restore_fn
    assert 'panelT("panel.modules.chat.gorev.restored")' in restore_fn
    assert 'panelT("panel.modules.chat.gorev.restoreVerifyFailed")' in restore_fn
    assert "lastGorevlerDeletedId = savedDeletedId" in restore_fn
    assert "hadDeleted && lastGorevlerDeletedId" not in restore_fn


def test_panel_astro_chat_delete_server_path_closes_detail() -> None:
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    delete_fn = text.split("async function deleteGorevlerTaskFromChat", 1)[1].split(
        "async function deleteOpenGorevlerTask", 1
    )[0]
    assert "detailIdxToClose" in delete_fn
    assert "closeGorevlerDetail(true)" in delete_fn
    assert "refreshPanelEvidenceStripIfReady()" in delete_fn


def test_panel_astro_online_delete_success_does_not_enqueue_evidence() -> None:
    """Online sunucu başarı yolunda delete enqueue yok (EC2-02 semantiği korunur)."""
    text = _PANEL_ASTRO.read_text(encoding="utf-8")
    delete_fn = text.split("async function deleteGorevlerTaskFromChat", 1)[1].split(
        "async function deleteOpenGorevlerTask", 1
    )[0]
    server_block = delete_fn.split("const refreshed = await refreshPanelGorevlerFromTasksApi();", 1)[0]
    assert "enqueueEvidencePendingOp" not in server_block


def test_panel_tasks_server_find_by_ref_title() -> None:
    panel_scripts = _REPO_ROOT / "panel" / "scripts"
    if str(panel_scripts) not in sys.path:
        sys.path.insert(0, str(panel_scripts))
    import panel_tasks_server as pts  # noqa: E402

    doc = {
        "tasks": [
            {"id": "tsk_1", "title": "Alışveriş listesi", "status": "active"},
            {"id": "tsk_2", "title": "Rapor yaz", "status": "done"},
        ]
    }
    assert pts._find_task_by_ref(doc, "tsk_1") is not None
    assert pts._find_task_by_ref(doc, "alışveriş listesi") is not None
    assert pts._find_task_by_ref(doc, "alışveriş-listesi") is not None
    assert pts._find_task_by_ref(doc, "yok") is None
