"""WebMCP dilimi (2026-08-25 sonrası) — panel tool kaydı ve onay kapısı sözleşmesi.

Bu testler kaynak sözleşmesini korur:
  * tool'lar gerçekten `document.modelContext.registerTool()` ile kaydedilir,
  * her dış etkili tool panelin insan onay kapısından geçer,
  * onay kapısını atlayan bir kısayol eklenmemiştir,
  * OKUMA da izne bağlıdır: izin yokken görev içeriği ajana dönmez,
  * onay ekranı, yazılacak HER alanı gerçek değerinden türeterek gösterir.

Çalışan uçtan uca doğrulama ayrıca: `npm run e2e:webmcp --prefix ui`.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_PAGE = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_PANEL_COMPONENTS = _REPO_ROOT / "ui" / "src" / "components" / "panel"
_WEBMCP_TOOLS = _PANEL_COMPONENTS / "WebMcpTools.astro"
_PANEL_RUNTIME = _PANEL_COMPONENTS / "PanelRuntime.astro"
_E2E = _REPO_ROOT / "ui" / "e2e" / "webmcp-panel-tools.mjs"
_E2E_NATIVE = _REPO_ROOT / "ui" / "e2e" / "webmcp-native-verify.mjs"

TOOL_NAMES = ("lumos-list-tasks", "lumos-propose-task", "lumos-complete-task")
WRITE_TOOL_BRIDGE_CALLS = ("b.proposeTask(", "b.completeTask(")


def _tools_src() -> str:
    return _WEBMCP_TOOLS.read_text(encoding="utf-8")


def _runtime_src() -> str:
    return _PANEL_RUNTIME.read_text(encoding="utf-8")


def test_webmcp_component_is_mounted_on_panel_page() -> None:
    page = _PANEL_PAGE.read_text(encoding="utf-8")
    assert 'import WebMcpTools from "../components/panel/WebMcpTools.astro";' in page
    assert "<WebMcpTools />" in page


def test_tools_are_registered_through_model_context() -> None:
    src = _tools_src()
    assert "modelContext" in src
    assert "registerTool" in src
    # Spec yüzeyi document.modelContext; navigator/window yalnızca yedek yoklama.
    assert "typeof document !== \"undefined\" ? document : null" in src
    for name in TOOL_NAMES:
        assert f'name: "{name}"' in src, name


def test_every_tool_declares_description_and_input_schema() -> None:
    src = _tools_src()
    assert src.count("description:") >= len(TOOL_NAMES)
    assert src.count("inputSchema:") >= len(TOOL_NAMES)
    assert src.count("execute(") >= len(TOOL_NAMES)


def test_write_tools_delegate_to_panel_bridge_only() -> None:
    """Tool'lar kendi başına yazmaz; panel köprüsünü çağırır."""
    src = _tools_src()
    for call in WRITE_TOOL_BRIDGE_CALLS:
        assert call in src, call
    # Tool bileşeni doğrudan görev REST'ine veya localStorage'a yazmamalı.
    assert "localStorage.setItem" not in src
    assert "fetch(" not in src


def test_bridge_write_paths_go_through_human_confirmation_gate() -> None:
    src = _runtime_src()
    assert "panelWebMcpHumanGate" in src
    # Her iki yazma yolu da kapıyı çağırır.
    assert src.count("await panelWebMcpHumanGate(") == 2
    # Kapı: sunucu onayı açıksa confirmation akışı, kapalıysa yerel modal.
    gate_start = src.index("async function panelWebMcpHumanGate(")
    # Sabit uzunluk yerine gerçek sınır: kapı büyüdükçe test kör kalmasın.
    gate_body = src[gate_start : src.index("async function panelWebMcpProposeTask(")]
    assert "isPanelConfirmationEnabled()" in gate_body
    assert "panelEnsureMutationConfirmation(" in gate_body
    assert "showPanelConfirmationModal(" in gate_body


def test_rejected_gate_never_writes() -> None:
    src = _runtime_src()
    # Onay alınmadan dönülür; mutasyon çağrısı kapının arkasında kalır.
    assert src.count('reason: gate.reason || "user_rejected",') == 2
    propose_start = src.index("async function panelWebMcpProposeTask(")
    propose_body = src[propose_start : src.index("async function panelWebMcpCompleteTask(")]
    assert propose_body.index("panelWebMcpHumanGate(") < propose_body.index(
        "persistPanelGorevCreateViaApi("
    )


def test_confirmation_lock_taken_before_first_await() -> None:
    """Eşzamanlı onaylar: kilit ilk await'ten önce alınır; busy ilk diyaloğa dokunmaz."""
    src = _runtime_src()
    assert "let panelConfirmationInFlight = false;" in src
    assert "function isPanelConfirmationBusy()" in src
    gate_start = src.index("async function panelWebMcpHumanGate(")
    gate_body = src[gate_start : src.index("async function panelWebMcpProposeTask(")]
    assert 'reason: "confirmation_busy"' in gate_body
    # Kilit, panelEnsureMutationConfirmation / showPanelConfirmationModal await'inden önce.
    assert gate_body.index("panelConfirmationInFlight = true;") < gate_body.index(
        "await panelEnsureMutationConfirmation("
    )
    assert gate_body.index("panelConfirmationInFlight = true;") < gate_body.index(
        "await showPanelConfirmationModal("
    )
    assert "finally {" in gate_body
    assert "panelConfirmationInFlight = false;" in gate_body


def test_gate_distinguishes_user_reject_from_server_failure() -> None:
    """user_rejected yalnız Vazgeç; sunucu/altyapı ayrı reason."""
    src = _runtime_src()
    req_start = src.index("async function requestPanelConfirmation(")
    req_body = src[req_start : src.index("async function panelEnsureMutationConfirmation(")]
    assert 'reason: "confirmation_unavailable"' in req_body
    assert 'reason: "confirmation_failed"' in req_body
    assert "catch {" in req_body
    modal_start = src.index("function showPanelConfirmationModal(")
    modal_body = src[modal_start : src.index("async function requestPanelConfirmation(")]
    assert 'reason: "user_rejected"' in modal_body
    assert "onCancel" in modal_body
    assert 'finish({ approved: false, reason: "confirmation_failed" })' in modal_body
    gate_start = src.index("async function panelWebMcpHumanGate(")
    gate_body = src[gate_start : src.index("async function panelWebMcpProposeTask(")]
    assert "confirmation.reason" in gate_body
    assert "decision.reason" in gate_body


def test_read_tool_is_not_a_mutation_path() -> None:
    """Okuma izin ister ama mutasyon kapısını kullanmaz; hiçbir şey yazmaz."""
    src = _runtime_src()
    list_start = src.index("async function panelWebMcpListTasks(")
    list_body = src[list_start : src.index("function panelWebMcpEnsureTasksModuleVisible(")]
    assert "panelWebMcpHumanGate" not in list_body
    assert "tasksApiPost" not in list_body
    assert "persistPanelGorevlerTasks" not in list_body


# ── Mahremiyet: okuma izni kapısı ────────────────────────────────────────────


def test_read_tool_withholds_content_without_consent() -> None:
    """İzin yoksa görev içeriği DÖNMEZ; ret, içerik toplamadan önce olur."""
    src = _runtime_src()
    list_start = src.index("async function panelWebMcpListTasks(")
    list_body = src[list_start : src.index("function panelWebMcpEnsureTasksModuleVisible(")]
    # Ret, listeyi kurmadan önce gelir.
    assert list_body.index("panelWebMcpReadRefusal(") < list_body.index("panelGorevlerTasks[i]")
    assert "if (!panelWebMcpReadConsentGranted) {" in list_body


def test_refusal_payload_is_explicit_and_carries_no_task_data() -> None:
    """Sessiz boş liste değil: ajana neden reddedildiği açıkça söylenir."""
    src = _runtime_src()
    start = src.index("function panelWebMcpReadRefusal(")
    body = src[start : src.index("async function panelWebMcpRequestReadConsent(")]
    assert 'reason: "read_consent_required"' in body
    assert "ok: false" in body
    assert "approved: false" in body
    assert "hint:" in body
    # Ret gövdesi görev verisi taşımamalı.
    assert "tasks" not in body
    assert "count" not in body
    assert "panelGorevlerTasks" not in body


def test_read_consent_is_session_scoped_and_fails_closed() -> None:
    src = _runtime_src()
    assert 'PANEL_WEBMCP_READ_CONSENT_SCOPE = "session"' in src
    assert "let panelWebMcpReadConsentGranted = false;" in src
    # Kalıcılık oturum düzeyinde: localStorage değil sessionStorage.
    load_start = src.index("function panelWebMcpReadConsentLoad(")
    load_body = src[load_start : src.index("function panelWebMcpReadConsentPersist(")]
    assert "window.sessionStorage.getItem" in load_body
    assert "localStorage" not in load_body


def test_read_consent_is_visible_and_revocable_in_the_panel() -> None:
    page = _PANEL_PAGE.read_text(encoding="utf-8")
    assert 'id="gorevler-webmcp-consent"' in page
    assert 'id="gorevler-webmcp-consent-revoke"' in page
    src = _runtime_src()
    assert "function panelWebMcpRevokeReadConsent(" in src
    assert "function panelWebMcpRenderConsentState(" in src
    # Geri alma düğmesi gerçekten bağlanır.
    assert 'getElementById("gorevler-webmcp-consent-revoke")' in src
    # Görünür durum sayfa açılışında yüklenir.
    assert "panelWebMcpReadConsentLoad();" in src
    assert "panelWebMcpRenderConsentState();" in src


def test_consent_prompt_is_shown_to_the_user_before_sharing() -> None:
    """İzin sessizce verilemez: kullanıcının gördüğü diyalogdan geçer."""
    src = _runtime_src()
    start = src.index("async function panelWebMcpRequestReadConsent(")
    body = src[start : src.index("async function panelWebMcpListTasks(")]
    assert "showPanelConfirmationModal(" in body
    assert "panelWebMcpEnsureTasksModuleVisible();" in body
    # Onay alınmadan izin yazılmaz.
    assert body.index("if (approved !== true) return false;") < body.index(
        "panelWebMcpReadConsentGranted = true;"
    )


def test_already_completed_shortcut_does_not_leak_task_content() -> None:
    """Onay ekranı açılmayan tek yazma yolu da izinsiz içerik döndürmemeli."""
    src = _runtime_src()
    start = src.index("async function panelWebMcpCompleteTask(")
    body = src[start : start + 1400]
    assert 'reason: "already_completed"' in body
    # İçerik doğrudan değil, izin kapısı olan yardımcıdan geçerek eklenir.
    assert "panelWebMcpAttachTask(" in body
    assert "task: panelWebMcpTaskView(" not in body


def test_task_echo_helper_is_gated_on_read_consent() -> None:
    """`task` alanını zarfa ekleyen tek yer, okuma iznini kontrol eder."""
    src = _runtime_src()
    start = src.index("function panelWebMcpAttachTask(")
    body = src[start : src.index("async function panelWebMcpRequestReadConsent(")]
    assert "panelWebMcpReadConsentGranted === true" in body
    assert "out.task = view;" in body
    # İzin kontrolü, görünümün zarfa yazılmasından ÖNCE gelir.
    assert body.index("panelWebMcpReadConsentGranted === true") < body.index("out.task =")


def test_no_bridge_path_attaches_task_data_outside_the_consent_helper() -> None:
    """Mutasyon onayı okuma izni değildir: hiçbir yol `task`ı elle eklemez.

    Ajan bir başlığı tahmin edip yalnızca "tamamla" onayı alarak okuma
    kapısını atlayamamalı; başarı zarfı da içerik taşımamalı.
    """
    src = _runtime_src()
    bridge_start = src.index("const PANEL_WEBMCP_BRIDGE_VERSION")
    bridge_end = src.index("window.__lumosPanelWebMcp = Object.freeze(")
    bridge = src[bridge_start:bridge_end]
    # Zarfa `task` yazan elle kurulmuş bir yol kalmamalı.
    assert "task: panelWebMcpTaskView(" not in bridge
    assert "out.task = panelWebMcpTaskView(" not in bridge
    # `panelWebMcpTaskView` yalnızca üç yerde geçer: tanımı, izin kapısı olan
    # yardımcı, ve zaten izinli olduğu kanıtlanmış listTasks gövdesi.
    # Yeni bir çağrı eklenirse bu sayı değişir ve test kırmızıya döner.
    assert bridge.count("panelWebMcpTaskView(") == 3
    list_body = bridge[
        bridge.index("async function panelWebMcpListTasks(") : bridge.index(
            "function panelWebMcpEnsureTasksModuleVisible("
        )
    ]
    assert list_body.count("panelWebMcpTaskView(") == 1


def test_success_envelopes_go_through_the_consent_helper() -> None:
    """propose/complete başarı yolları da aynı kapıdan geçer."""
    src = _runtime_src()
    propose = src[
        src.index("async function panelWebMcpProposeTask(") : src.index(
            "async function panelWebMcpCompleteTask("
        )
    ]
    complete = src[
        src.index("async function panelWebMcpCompleteTask(") : src.index(
            "window.__lumosPanelWebMcp = Object.freeze("
        )
    ]
    assert propose.count("panelWebMcpAttachTask(") == 1
    # already_completed + yerel tamamlama + API sonrası tamamlama.
    assert complete.count("panelWebMcpAttachTask(") == 3


def test_complete_tool_description_states_the_no_echo_rule() -> None:
    """Ajan, `task` yokluğunu 'yazılmadı' sanmamalı."""
    src = _tools_src()
    start = src.index('name: "lumos-complete-task"')
    body = src[start : start + 1200]
    assert "NOT permission to read the board" in body
    assert "already_completed" in body


def test_list_tool_tells_the_agent_consent_is_required() -> None:
    src = _tools_src()
    assert "read_consent_required" in src
    assert "await b.listTasks()" in src


# ── Onay ekranı: yazılacak alanların tamamı ──────────────────────────────────


def test_confirmation_dialog_has_a_field_list_section() -> None:
    page = _PANEL_PAGE.read_text(encoding="utf-8")
    assert 'id="lumos-confirm-preview-fields-wrap"' in page
    assert 'id="lumos-confirm-preview-fields"' in page
    src = _runtime_src()
    assert "function renderPanelConfirmationFields(" in src
    assert "renderPanelConfirmationFields(p.fields);" in src


def test_field_values_are_rendered_as_text_not_markup() -> None:
    """Alan değerleri ajandan gelir; HTML olarak yorumlanmamalı."""
    src = _runtime_src()
    start = src.index("function renderPanelConfirmationFields(")
    body = src[start : src.index("function showPanelConfirmationModal(")]
    assert "dd.textContent" in body
    assert "innerHTML" not in body


def test_propose_dialog_shows_every_written_field_from_real_values() -> None:
    """priority ve when dahil, yazılacak her alan onay ekranında görünür."""
    src = _runtime_src()
    start = src.index("async function panelWebMcpProposeTask(")
    body = src[start : src.index("async function panelWebMcpCompleteTask(")]
    for key in ('key: "title"', 'key: "priority"', 'key: "when"', 'key: "status"', 'key: "source"'):
        assert key in body, key
    # Değerler sabit metin değil, çağrının gerçek değişkenlerinden gelir.
    assert "value: title," in body
    assert "panelWebMcpPriorityLabel(priority)" in body
    assert "? whenSummary" in body
    # Alanlar kapıya taşınır — yoksa ekranda görünmez.
    assert "fields: previewFields," in body
    # Ekranda gösterilen durum, yazılan durumla aynı değişkendir.
    assert "status: proposeStatus," in body


def test_propose_dialog_marks_unset_fields_explicitly() -> None:
    """Boş/varsayılan alan gizlenmez: kullanıcı neyi onayladığını bilir."""
    src = _runtime_src()
    start = src.index("async function panelWebMcpProposeTask(")
    body = src[start : src.index("async function panelWebMcpCompleteTask(")]
    assert 'panelWebMcpT("valueUnsetPrefix"' in body
    assert 'panelWebMcpT("valueDefaultPrefix"' in body
    assert "unset: !priorityGiven," in body
    assert "unset: !whenSummary," in body


def test_complete_dialog_shows_the_status_transition() -> None:
    """Tamamlama: durum değişikliği neyi neye çeviriyor, ekranda yazar."""
    src = _runtime_src()
    start = src.index("async function panelWebMcpCompleteTask(")
    body = src[start : src.index("window.__lumosPanelWebMcp = Object.freeze(")]
    assert 'const statusFrom = String(row.status || "bekliyor");' in body
    assert 'const statusTo = "tamamlandi";' in body
    assert 'key: "status_change"' in body
    assert "panelWebMcpStatusLabel(statusFrom)" in body
    assert "panelWebMcpStatusLabel(statusTo)" in body
    assert "fields: completeFields," in body


def test_server_confirmation_path_also_receives_the_fields() -> None:
    """Sunucu onay akışında da alanlar ekrana taşınır — iki yol ayrışamaz."""
    src = _runtime_src()
    assert (
        "async function panelEnsureMutationConfirmation(mutationPath, mutationBody, previewFields)"
        in src
    )
    gate_start = src.index("async function panelWebMcpHumanGate(")
    gate_body = src[gate_start : src.index("async function panelWebMcpProposeTask(")]
    assert "previewFields," in gate_body
    assert "fallbackPreview.fields" in gate_body


def test_confirmation_modal_ignores_stale_close_event() -> None:
    """Ardışık onaylarda önceki `close` olayı yeni diyaloğu iptal etmemeli."""
    src = _runtime_src()
    close_start = src.index("function onClose() {")
    close_body = src[close_start : close_start + 700]
    assert "if (dlg.open) return;" in close_body


def test_e2e_scenario_exists_and_covers_rejection() -> None:
    assert _E2E.is_file()
    e2e = _E2E.read_text(encoding="utf-8")
    assert "lumos-confirm-cancel" in e2e
    assert "lumos-confirm-approve" in e2e
    assert "onay kapısı atlanmış" in e2e
    assert "WEBMCP_PANEL_E2E_RESULT" in e2e


def test_e2e_scenario_covers_concurrent_busy_and_server_errors() -> None:
    e2e = _E2E.read_text(encoding="utf-8")
    assert "confirmation_busy" in e2e
    assert "confirmation_failed" in e2e
    assert "confirmation_unavailable" in e2e
    assert "eşzamanlı" in e2e.lower() or "concurrent" in e2e.lower()
    assert "HTTP 500" in e2e or "status: 500" in e2e
    assert "bozuk JSON" in e2e or "invalid json" in e2e.lower() or "broken json" in e2e.lower()
    for marker in ("lumos-confirm/request", "network"):
        assert marker in e2e, marker


def test_e2e_scenario_covers_read_consent_and_dialog_fields() -> None:
    e2e = _E2E.read_text(encoding="utf-8")
    # İzin yokken içerik dönmüyor.
    assert "read_consent_required" in e2e
    assert "İzinsiz okumada görev içeriği sızmış" in e2e
    # İzin görünür ve geri alınabilir.
    assert "gorevler-webmcp-consent-revoke" in e2e
    assert "Geri alma sonrası okuma engellenmedi" in e2e
    # Diyalog priority/when'i gerçek değerlerle gösteriyor.
    assert "lumos-confirm-preview-fields" in e2e
    assert "Zaman alanı gerçek değeri göstermiyor" in e2e
    assert "Verilmeyen 'when' alanı belirtilmedi olarak işaretlenmemiş" in e2e
    assert "Verilmeyen öncelik 'belirtilmedi' işaretlenmemiş" in e2e


def test_native_e2e_proves_no_leak_without_read_consent() -> None:
    """Bayraklı gerçek Chrome kanıtı: izinsiz hiçbir yol veri döndürmez."""
    assert _E2E_NATIVE.is_file()
    e2e = _E2E_NATIVE.read_text(encoding="utf-8")
    # Sayfaya enjeksiyon yok — kanıtın temeli (yorumda geçebilir, ÇAĞRI olamaz).
    assert "addInitScript(" not in e2e
    assert "document.modelContext.executeTool(" in e2e
    # İzin panelin kendi düğmesiyle geri alınır, sonra üç durum sınanır.
    assert "gorevler-webmcp-consent-revoke" in e2e
    assert "function assertNoTaskData(" in e2e
    for label in (
        "native already_completed (izinsiz)",
        "native propose onaylı (izinsiz)",
        "native complete onaylı (izinsiz)",
        "native task_not_found",
        "native ref_required",
    ):
        assert label in e2e, label
    # Zarf anahtar bazında da taranır, değer bazında da.
    assert '"task", "title", "priority", "when", "id", "status"' in e2e
    # Yazmanın gerçekten olduğu ajan yüzeyinden değil panelden doğrulanır.
    assert "lumos_panel_gorevler_list_v1" in e2e
    # Regresyon: izin geri verilince içerik yeniden döner.
    assert "izin varken içerik dönmedi (regresyon)" in e2e
    # Chrome 152'de test yüzeyinin yokluğu kayda geçer.
    assert "modelContextTestingType" in e2e
