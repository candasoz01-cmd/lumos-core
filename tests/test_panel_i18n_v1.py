"""Panel i18n v1–v32 — LanguageSwitcher, nav, modules, Sohbet chat, Görevler."""

from __future__ import annotations

from pathlib import Path

from tests.test_panel_component_split import read_panel_source

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PANEL_ASTRO = _REPO_ROOT / "ui" / "src" / "pages" / "panel.astro"
_TR_MESSAGES = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "tr.ts"
_EN_MESSAGES = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "en.ts"
_PANEL_TR = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "tr.ts"
_PANEL_EN = _REPO_ROOT / "ui" / "src" / "i18n" / "messages" / "panel" / "en.ts"

PANEL_I18N_MARKERS = (
    'import LanguageSwitcher from "../components/LanguageSwitcher.astro";',
    'import I18nInit from "../components/I18nInit.astro";',
    "<LanguageSwitcher />",
    "<I18nInit />",
    'data-i18n="panel.header.title"',
    'data-i18n="panel.nav.sohbet"',
    'data-i18n="panel.nav.gorevler"',
    'data-i18n="panel.nav.dosyalar"',
    'data-i18n="panel.sections.gorevler"',
    'data-i18n="panel.sections.dosyalar"',
    'data-i18n-aria-label="panel.sections.sohbet"',
)

PANEL_I18N_V2_MARKERS = (
    'data-i18n="panel.sections.ses"',
    'data-i18n="panel.sections.medya"',
    'data-i18n="panel.sections.sosyal"',
    'data-i18n="panel.sections.posta"',
    'data-i18n="panel.modules.voice.intro"',
    'data-i18n="panel.modules.voice.c1Title"',
    'data-i18n="panel.modules.media.outboxTitle"',
    'data-i18n="panel.modules.media.outboxRefresh"',
    'data-i18n="panel.modules.social.sharePreviewIntro"',
    'data-i18n="panel.modules.mail.sharePreviewIntro"',
    'data-i18n="panel.common.badges.demoNotConnected"',
    'data-i18n="panel.common.form.showSummary"',
    'data-i18n="panel.common.form.sendDemoDisabled"',
    'data-i18n-placeholder="panel.common.placeholders.shareSummary"',
    'data-i18n-title="panel.common.demo.sendTitle"',
    'function panelT(key)',
)

PANEL_I18N_V2_TR_KEYS = (
    "common:",
    "demoNotConnected:",
    "sharePreviewIntro:",
    "dataType:",
    "ses:",
    "medya:",
    "sosyal:",
    "posta:",
)

PANEL_I18N_V3_MARKERS = (
    'data-i18n="panel.modules.chat.empty.default"',
    'data-i18n="panel.modules.chat.capability.title"',
    'data-i18n="panel.modules.chat.security.approval"',
    'data-i18n-placeholder="panel.modules.chat.compose.placeholder"',
    'data-i18n="panel.modules.chat.compose.send"',
    'data-i18n="panel.modules.chat.compose.attachFile"',
    'panelT("panel.modules.chat.empty.default")',
    'panelT("panel.modules.chat.modeHints.sendOffline")',
    'chatBubbleRoleLabel(kind)',
    'function refreshPanelChatI18n()',
    'refreshPanelChatI18n()',
)

PANEL_I18N_V3_TR_KEYS = (
    "chat:",
    "empty:",
    "modeHints:",
    "bubbles:",
    "capability:",
    "compose:",
)

PANEL_I18N_V4_MARKERS = (
    'data-i18n="panel.modules.tasks.intro"',
    'data-i18n="panel.modules.tasks.form.titleLabel"',
    'data-i18n-placeholder="panel.modules.tasks.form.titlePlaceholder"',
    # Create form no longer exposes status <option data-i18n>; labels via panelT.
    'panelT("panel.modules.tasks.status.bekliyor")',
    'id="gorevler-status"',
    'data-i18n="panel.modules.tasks.list.filterAll"',
    'data-i18n="panel.modules.tasks.detail.close"',
    'function gorevlerStatusLabel(',
    'panelT("panel.modules.tasks.empty.listDefault")',
    'gorevlerPriorityLabel(t.priority)',
)

PANEL_I18N_V4_TR_KEYS = (
    "form:",
    "priority:",
    "status:",
    "list:",
    "empty:",
    "detail:",
)

PANEL_I18N_V5_MARKERS = (
    'data-i18n="panel.sections.kuantum"',
    'data-i18n="panel.modules.quantum.intro"',
    'data-i18n="panel.modules.quantum.c1Title"',
    'data-i18n="panel.nav.lumosCore"',
    'data-i18n="panel.nav.yayincilik"',
    'data-i18n="panel.modules.publishing.c1Title"',
    'data-i18n="panel.modules.capabilities.intro"',
    'data-i18n="panel.modules.capabilities.testBtn"',
)

PANEL_I18N_V5_TR_KEYS = (
    "lumosCore:",
    "yayincilik:",
    "yapayzeka:",
    "entegrasyon:",
    "capabilities:",
)

PANEL_I18N_V6_MARKERS = (
    'data-i18n-aria-label="panel.shell.conn.ariaLabel"',
    'data-i18n-title="panel.shell.conn.title"',
    'data-i18n="panel.shell.userMode.menuOffline"',
    'data-i18n="panel.shell.userMode.segLegend"',
    'data-i18n-aria-label="panel.shell.userMode.badgeAria"',
    'function panelConnBadgeLabel(',
    'function refreshPanelShellI18n()',
    'refreshPanelShellI18n()',
    'panelT("panel.shell.userMode.badgeLimited")',
)

PANEL_I18N_V6_TR_KEYS = (
    "shell:",
    "conn:",
    "userMode:",
)

PANEL_I18N_V7_MARKERS = (
    'data-i18n="panel.modules.files.intro"',
    'data-i18n="panel.modules.files.form.pickLabel"',
    'data-i18n="panel.modules.files.form.uploadBtn"',
    'panelT("panel.modules.files.hints.pickFirst")',
    'panelT("panel.modules.files.result.metaTitle")',
    'function refreshPanelFilesI18n()',
    'refreshPanelFilesI18n()',
)

PANEL_I18N_V7_TR_KEYS = (
    "form:",
    "hints:",
    "result:",
    "history:",
    "messages:",
)

PANEL_I18N_V8_MARKERS = (
    'panelT("panel.modules.chat.errors." + k)',
    'const PANEL_CHAT_ERROR_KINDS = [',
    'PANEL_CHAT_ERROR_KINDS.includes(upstreamKind)',
)

PANEL_I18N_V8_TR_KEYS = (
    "errors:",
    "network_error:",
    "unknown_error:",
)

PANEL_I18N_V9_MARKERS = (
    'panelT("panel.modules.tasks.empty.evidence")',
    'panelT("panel.modules.tasks.detail.evidenceSummaryPrefix")',
    'function refreshPanelGorevlerI18n()',
    'refreshPanelGorevlerI18n()',
)

PANEL_I18N_V9_TR_KEYS = (
    "evidenceSummaryPrefix:",
)

PANEL_I18N_V10_MARKERS = (
    'panelT("panel.modules.chat.transcript.engineMsg")',
    'panelT("panel.modules.chat.transcript.offlineMsg")',
    'panelT("panel.modules.chat.transcript.addToChat")',
    'panelT("panel.modules.chat.transcript.previewAria")',
)

PANEL_I18N_V10_TR_KEYS = (
    "transcript:",
    "engineMsg:",
    "addToChat:",
)

PANEL_I18N_V11_MARKERS = (
    'panelT("panel.modules.chat.compose.hints.pickOneAttachment")',
    'panelT("panel.modules.chat.compose.hints.fullAudioHint")',
    'panelT("panel.modules.chat.errors.network_error")',
    'function panelComposePhotoHint(',
    'function panelComposeAudioReply(',
)

PANEL_I18N_V11_TR_KEYS = (
    "hints:",
    "pickOneAttachment:",
    "fullAudioHint:",
    "clipboardReadyWithSnippet:",
)

PANEL_I18N_V12_MARKERS = (
    'setCameraHintKey("panel.modules.chat.compose.cameraHints.unsupported")',
    'setCameraHintKey("panel.modules.chat.compose.cameraHints.permissionDenied")',
    'refreshPanelCameraHintsI18n = () => {',
    'if (typeof refreshPanelCameraHintsI18n === "function") refreshPanelCameraHintsI18n();',
)

PANEL_I18N_V12_TR_KEYS = (
    "cameraHints:",
    "unsupported:",
    "fileUploadPreparing:",
)

PANEL_I18N_V13_MARKERS = (
    'setAudioRecordHintKey("panel.modules.chat.compose.record.unsupported")',
    'panelT("panel.modules.chat.compose.attachRecordTitle")',
    'panelT("panel.modules.chat.compose.record.previewLabel")',
    'refreshPanelAudioRecordI18n = () => {',
    'if (typeof refreshPanelAudioRecordI18n === "function") refreshPanelAudioRecordI18n();',
)

PANEL_I18N_V13_TR_KEYS = (
    "record:",
    "previewLabel:",
    "recordingHint:",
    "attachRecordTitle:",
)

PANEL_I18N_V14_MARKERS = (
    'setVoiceHintKey("panel.modules.chat.compose.voiceHints.unsupported")',
    "navigator.mediaDevices.getUserMedia({ audio: true })",
    "requestLocalTranscription(",
    "function voiceTranscriptionFailureHintKey(",
    "fillPanelChatInputWithTranscript(result.text)",
    'refreshPanelVoiceHintsI18n = () => {',
    'if (typeof refreshPanelVoiceHintsI18n === "function") refreshPanelVoiceHintsI18n();',
)

PANEL_I18N_V14_TR_KEYS = (
    "voiceHints:",
    "recording:",
    "transcribing:",
    "added:",
    "startFailed:",
)

PANEL_I18N_V15_MARKERS = (
    'panelT("panel.modules.chat.compose.photoSelectedLabel")',
    'panelT("panel.modules.chat.compose.photoCapturedStatus")',
    'function syncCameraPhotoStatusText()',
    'syncCameraPhotoStatusText();',
)

PANEL_I18N_V15_TR_KEYS = (
    "photoSelectedLabel:",
    "photoCapturedStatus:",
)

PANEL_I18N_V16_MARKERS = (
    'panelT("panel.modules.chat.compose.sendLoading")',
    'panelT("panel.modules.chat.compose.audioFileAttached")',
    'panelT("panel.modules.chat.compose.audioRecordAttached")',
    'panelT("panel.modules.chat.compose.audioRecordAria")',
)

PANEL_I18N_V16_TR_KEYS = (
    "sendLoading:",
    "audioFileAttached:",
    "audioRecordAttached:",
    "audioRecordAria:",
)

PANEL_I18N_V17_MARKERS = (
    'panelT("panel.modules.chat.compose.send")',
    'panelT("panel.modules.chat.compose.photoAdded")',
    'panelT("panel.modules.chat.compose.clipboardConfirm")',
    'panelT("panel.modules.chat.compose.clipboardConfirmAria")',
    'panelT("panel.modules.chat.compose.clipboardConfirmTitle")',
)

PANEL_I18N_V17_TR_KEYS = (
    "photoAdded:",
    "clipboardConfirm:",
    "clipboardConfirmAria:",
    "clipboardConfirmTitle:",
)

PANEL_I18N_V18_MARKERS = (
    'panelT("panel.modules.chat.compose.hints.emptyReply")',
    'panelT("panel.modules.chat.compose.hints.responseUnusableBubble")',
    'panelT("panel.modules.chat.compose.hints.gorevServerReplyPrefix")',
    'panelT("panel.modules.chat.compose.hints.gorevNoExtraServerText")',
    'panelT("panel.modules.chat.compose.hints.photoNoVision")',
    'function panelChatDisplayReply(',
)

PANEL_I18N_V18_TR_KEYS = (
    "emptyReply:",
    "responseUnusableBubble:",
    "gorevServerReplyPrefix:",
    "gorevNoExtraServerText:",
    "photoNoVision:",
)

PANEL_I18N_V19_MARKERS = (
    'panelT("panel.modules.chat.gorev.deleteUnavailable")',
    'panelT("panel.modules.chat.gorev.restoreUnavailable")',
    'panelT("panel.modules.chat.gorev.confirmMini")',
    'panelT("panel.modules.chat.localReply.emptyMessage")',
    'panelT("panel.modules.chat.localReply.limitedDefault")',
    'panelT("panel.modules.chat.gorev.deleteRestoreHint")',
    'function panelGorevDeleteRestoreHint(',
    'function panelLocalWeekdayName(',
)

PANEL_I18N_V19_TR_KEYS = (
    "gorev:",
    "localReply:",
    "deleteUnavailable:",
    "restoreNothing:",
    "timeBase:",
)

PANEL_I18N_V20_MARKERS = (
    'panelT("panel.modules.tasks.hints.savedLocal")',
    'panelT("panel.modules.tasks.hints.titleEmpty")',
    'panelT("panel.modules.tasks.hints.bridgeFailed")',
    'panelT("panel.modules.tasks.hints.deleted")',
    'panelT("panel.modules.tasks.confirm.deleteOpen")',
    'panelT("panel.modules.tasks.confirm.clearLocal")',
    'panelT("panel.shell.infra.tokenMissing")',
    'panelT("panel.shell.infra.tokenPresent")',
    'panelT("panel.shell.infra.online")',
    'panelT("panel.shell.infra.offline")',
    'paintPanelInfraStatusSkeleton();',
)

PANEL_I18N_V20_TR_KEYS = (
    "hints:",
    "savedLocal:",
    "confirm:",
    "deleteOpen:",
    "infra:",
    "tokenMissing:",
)

PANEL_I18N_V21_MARKERS = (
    'data-i18n="panel.shell.infra.labelBridge"',
    'data-i18n="panel.shell.infra.labelToken"',
    'data-i18n="panel.shell.infra.labelHealth"',
    'data-i18n="panel.shell.infra.labelInternet"',
    'panelT("panel.shell.infra.unavailableMsg")',
    'panelT("panel.shell.infra.unavailableShort")',
    "function syncBridgeHealthLine()",
    "syncBridgeHealthLine();",
    'bridgeHealthPhase = "trying"',
    "if (photoTelemetry && PANEL_DEBUG) {",
)

PANEL_I18N_V21_TR_KEYS = (
    "labelBridge:",
    "labelToken:",
    "labelHealth:",
    "labelInternet:",
    "unavailableShort:",
    "unavailableMsg:",
    "healthPending:",
    "healthTrying:",
    "healthOk:",
    "healthUnreachable:",
)

PANEL_I18N_V22_MARKERS = (
    'data-i18n="panel.modules.settings.c6Title"',
    'data-i18n="panel.modules.settings.c6Body"',
    'data-i18n="panel.modules.settings.c7Title"',
    'data-i18n="panel.modules.settings.c7Body"',
)

PANEL_I18N_V22_TR_KEYS = (
    "c6Title:",
    "c6Body:",
    "c7Title:",
    "c7Body:",
)

PANEL_I18N_V23_MARKERS = (
    '"panel.modules.capabilities.status.active"',
    'panelT("panel.modules.capabilities.testRunning")',
    'panelT("panel.modules.files.hints.attachNavigate")',
    'panelT("panel.modules.chat.tts.speak")',
    'panelT("panel.modules.chat.tts.stopSpeaking")',
    "function capStatusLabel(",
    "function refreshPanelCapabilitiesI18n()",
    "function initCapLabels()",
    "refreshPanelCapabilitiesI18n();",
    "refreshPanelTtsI18n = () =>",
)

PANEL_I18N_V23_TR_KEYS = (
    "status:",
    "testRunning:",
    "attachNavigate:",
    "tts:",
    "stopSpeaking:",
    "unsupportedFeature:",
)

PANEL_I18N_V24_MARKERS = (
    'panelT("panel.modules.settings.corsMsg")',
    'id="panel-sistem-durumu-cors"',
    'data-i18n-aria-label="panel.modules.settings.infraSummaryAria"',
    'data-i18n="panel.modules.capabilities.row1"',
    'data-i18n="panel.modules.capabilities.row7"',
    'data-i18n-aria-label="panel.modules.chat.compose.galleryAria"',
    'data-i18n-aria-label="panel.modules.chat.compose.cameraAria"',
    'data-i18n-aria-label="panel.modules.chat.compose.voiceAriaSupported"',
    'data-i18n-aria-label="panel.modules.chat.compose.attachRecord"',
    "paintSistemDurumuPanel();",
)

PANEL_I18N_V24_TR_KEYS = (
    "corsMsg:",
    "infraSummaryAria:",
    "row1:",
    "row7:",
    "galleryAria:",
    "cameraAria:",
    "voiceAriaSupported:",
    "attachRecord:",
)

PANEL_I18N_V25_MARKERS = (
    'panelT("panel.modules.settings.connectionLine")',
    'panelT("panel.modules.settings.healthWithConnection")',
    'panelT("panel.modules.settings.visionConfiguredYes")',
    'panelT("panel.modules.settings.visionConfiguredNo")',
    'panelT("panel.modules.chat.bubbles.actionsAria")',
    'data-i18n="panel.modules.capabilities.bridgePending"',
    'data-i18n="panel.modules.capabilities.routeTerminal"',
    'data-i18n="panel.modules.capabilities.routeManualApproval"',
    'data-i18n="panel.modules.capabilities.routeNone"',
)

PANEL_I18N_V25_TR_KEYS = (
    "connectionLine:",
    "healthWithConnection:",
    "visionConfiguredYes:",
    "visionConfiguredNo:",
    "actionsAria:",
    "routeTerminal:",
    "routeManualApproval:",
    "routeNone:",
)

PANEL_I18N_V26_MARKERS = (
    'panelT("panel.modules.settings.chatPingReady")',
    'panelT("panel.modules.settings.chatPingNoResponse")',
    'panelT("panel.modules.settings.chatPingUnreadable")',
    'panelT("panel.modules.settings.chatWithPing")',
)

PANEL_I18N_V26_TR_KEYS = (
    "chatPingReady:",
    "chatPingNoResponse:",
    "chatPingUnreadable:",
    "chatWithPing:",
)

PANEL_I18N_V27_MARKERS = (
    'panelT("panel.modules.media.outboxResultNotFound")',
    'panelT("panel.modules.media.outboxFetchFailed")',
    'panelT("panel.modules.capabilities.testBridgeUnavailable")',
    'panelT("panel.modules.capabilities.testDone")',
    'panelT("panel.modules.capabilities.testPartialFailed")',
)

PANEL_I18N_V27_TR_KEYS = (
    "outboxResultFailedWithSnippet:",
    "outboxResultNotFound:",
    "outboxFetchFailed:",
    "testBridgeUnavailable:",
    "testDone:",
    "testPartialFailed:",
)

PANEL_I18N_V28_MARKERS = (
    'panelT("panel.shell.infra.bridgeTokenMsg")',
    'panelT("panel.modules.tasks.hints.createFailed")',
    'panelT("panel.modules.tasks.hints.leakCompleteFailed")',
    'panelT("panel.modules.tasks.hints.leakDeleteFailed")',
    'panelT("panel.modules.tasks.hints.leakRestoreFailed")',
)

PANEL_I18N_V28_TR_KEYS = (
    "bridgeTokenMsg:",
    "createFailed:",
    "leakCompleteFailed:",
    "leakDeleteFailed:",
    "leakRestoreFailed:",
)

PANEL_I18N_V29_MARKERS = (
    'panelT("panel.shell.infra.leakConnectionKey")',
    'panelT("panel.shell.infra.leakLocalServer")',
    'panelT("panel.shell.infra.leakRequestError")',
)

PANEL_I18N_V29_TR_KEYS = (
    "leakConnectionKey:",
    "leakLocalServer:",
    "leakRequestError:",
)

PANEL_I18N_V30_MARKERS = (
    'panelT("panel.shell.infra.leakConnectionInfo")',
    'panelT("panel.shell.infra.leakRoute")',
    'panelT("panel.shell.infra.leakTransmission")',
    'panelT("panel.shell.infra.leakLastResult")',
    'panelT("panel.shell.infra.leakTaskRecord")',
    'panelT("panel.shell.infra.leakBrowserRestriction")',
)

PANEL_I18N_V30_TR_KEYS = (
    "leakConnectionInfo:",
    "leakRoute:",
    "leakTransmission:",
    "leakLastResult:",
    "leakTaskRecord:",
    "leakBrowserRestriction:",
)

PANEL_I18N_V31_MARKERS = (
    'panelT("panel.shell.infra.leakDevice")',
    'panelT("panel.shell.infra.leakConnection")',
    'panelT("panel.shell.infra.leakTask")',
    'panelT("panel.shell.infra.leakControlledFile")',
    'panelT("panel.shell.infra.leakStatus")',
    'panelT("panel.shell.infra.leakHealth")',
    'panelT("panel.shell.infra.leakChat")',
    'panelT("panel.shell.infra.leakTaskService")',
    'panelT("panel.shell.infra.leakConnectionStart")',
)

PANEL_I18N_V31_TR_KEYS = (
    "leakDevice:",
    "leakConnection:",
    "leakTask:",
    "leakControlledFile:",
    "leakStatus:",
    "leakHealth:",
    "leakChat:",
    "leakTaskService:",
    "leakConnectionStart:",
)

PANEL_I18N_V32_MARKERS = (
    'panelT("panel.shell.infra.leakConnectionMasked")',
)

PANEL_I18N_V32_TR_KEYS = (
    "leakConnectionMasked:",
)

PANEL_I18N_V33_MARKERS = (
    '"panel.modules.tasks.plan.teshis.ozet"',
    'panelT("panel.modules.tasks.plan.notPending")',
    'panelT("panel.modules.tasks.plan.alanGorevler")',
    'panelT("panel.modules.tasks.plan.approvalSaved")',
    'panelT("panel.modules.tasks.detail.dlStatus")',
    'panelT("panel.modules.tasks.detail.dlPriority")',
    'panelT("panel.modules.tasks.detail.yes")',
    'panelT("panel.modules.tasks.detail.bridgeNotYet")',
    'function gorevlerTeshisLabels()',
    'let panelGorevlerRefreshI18n = null',
    'panelGorevlerRefreshI18n = () =>',
)

PANEL_I18N_V33_TR_KEYS = (
    "teshis:",
    "notPending:",
    "alanGorevler:",
    "approvalSaved:",
    "dlStatus:",
    "dlPriority:",
    "bridgeNotYet:",
    "lowRiskStatus:",
)

PANEL_I18N_V34_MARKERS = (
    'panelT("panel.modules.tasks.evidence.sourceBridge")',
    'panelT("panel.modules.tasks.evidence.bridgePrefix")',
    'panelT("panel.modules.tasks.evidence.taskPrefix")',
    'panelT("panel.modules.tasks.evidence.guardPrefix")',
    'panelT("panel.modules.tasks.evidence.enginePrefix")',
    'panelT("panel.modules.tasks.evidence.mutationDefault")',
    'panelT("panel.modules.tasks.evidence.guardDefault")',
)

PANEL_I18N_V34_TR_KEYS = (
    "sourceBridge:",
    "bridgePrefix:",
    "taskPrefix:",
    "guardPrefix:",
    "enginePrefix:",
    "mutationDefault:",
    "guardDefault:",
)

PANEL_I18N_V35_MARKERS = (
    "function panelLocaleTag()",
    'panelT("panel.modules.tasks.when.tomorrow")',
    'panelT("panel.modules.tasks.when.today")',
    "panelLocaleTag()",
)

PANEL_I18N_V35_TR_KEYS = (
    "when:",
    "tomorrow:",
    "today:",
)

PANEL_I18N_V36_MARKERS = (
    'data-i18n-title="panel.nav.statusTitle.kuantum"',
    'panelT("panel.modules.tasks.plan.listPrefix")',
    "function gorevlerPlanTurDisplay(",
    "function gorevlerPlanRiskDisplay(",
    "function gorevlerPlanSonrakiAdimDisplay(",
    'tur: tur || "genelGorev"',
    'risk: risk || "dusuk"',
    'let tur = "genelGorev"',
    'let risk = "dusuk"',
)

PANEL_I18N_V36_TR_KEYS = (
    "kuantumResearchTitle:",
    "listPrefix:",
    "genelGorev:",
    "dosyaIslemi:",
    "sonrakiAdim:",
    "alanPanel:",
)

PANEL_I18N_V37_MARKERS = (
    "wirePanelConnBadgeSetupLink",
    'panelT("panel.shell.conn.setupHint")',
    'badge.setAttribute("data-setup-link"',
)

PANEL_I18N_V37_TR_KEYS = (
    "setupHint:",
)

PANEL_I18N_V38_MARKERS = (
    'panelT("panel.modules.tasks.empty.evidenceUnreachable")',
    "const fetched = await fetchEvidenceRecent()",
    "if (!fetched.ok)",
    "return { ok: true, events: data.events }",
)

PANEL_I18N_V38_TR_KEYS = (
    "evidenceUnreachable:",
)

PANEL_I18N_V39_MARKERS = (
    'panelT("panel.modules.chat.empty.heroPrefillBanner")',
    "showPanelHeroPrefillBanner",
    'navigatePanelModule("sohbet")',
    "scrollIntoView({ behavior: \"smooth\", block: \"center\" })",
)

PANEL_I18N_V39_TR_KEYS = (
    "heroPrefillBanner:",
)

PANEL_I18N_V40_MARKERS = (
    "function classifyPanelProdError(",
    "function panelProdErrorUserMessage(",
    "function userMessageForPanelProdErrorKind(",
    'panelT("panel.shell.infra.prodErrors.write_failed")',
    'panelT("panel.shell.infra.prodErrors.path_outside_sandbox")',
    "panelProdErrorUserMessage({",
)

PANEL_I18N_V40_TR_KEYS = (
    "prodErrors:",
    "write_failed:",
    "path_outside_sandbox:",
    "create_failed:",
    "complete_failed:",
)

PANEL_I18N_V41_MARKERS = (
    "function panelOutboxFailureUserMessage(",
    "setMedyaOutboxHint(() => panelOutboxFailureUserMessage(outboxErrCtx))",
    'panelT("panel.modules.media.outboxResultUnauthorized")',
)

PANEL_I18N_V41_TR_KEYS = (
    "outboxResultUnauthorized:",
)

PANEL_I18N_V42_MARKERS = (
    "let gorevlerHintRefresh = null",
    "function refreshGorevlerVisibleHintI18n(",
    "function setGorevlerHint(",
    "let dosyalarHintRefresh = null",
    "function refreshDosyalarVisibleHintI18n(",
    "function setDosyalarHint(",
    "window.refreshMedyaOutboxHintI18n",
    "function setMedyaOutboxHint(",
    "refreshGorevlerVisibleHintI18n();",
    "refreshDosyalarVisibleHintI18n();",
    "window.refreshMedyaOutboxHintI18n()",
)

PANEL_I18N_V43_MARKERS = (
    "function panelChatFailureUserMessage(",
    "panelChatFailureUserMessage(",
    "httpFailKind,",
)

PANEL_I18N_V43_TR_KEYS = (
    "errors:",
    "network_error:",
)

PANEL_I18N_V44_MARKERS = (
    "let sendHintRefresh = null",
    "function paintSendHintFromResolver(",
    "refreshSendHintI18n = () =>",
    "refreshPanelSendButtonI18n = () =>",
    "function refreshPanelHeroPrefillBannerI18n(",
    "function panelSendLabel(",
    "function panelSendLoadingLabel(",
    "refreshPanelHeroPrefillBannerI18n();",
    "refreshSendHintI18n();",
)

PANEL_I18N_V44_TR_KEYS = (
    "heroPrefillBanner:",
    "sendLoading:",
)

PANEL_I18N_V45_MARKERS = (
    "function transcriptBlockedUserMessage(",
    "function transcriptEngineUserMessage(",
    "showStatus(() => transcriptBlockedUserMessage(result))",
    "showStatus(() => transcriptEngineUserMessage(result))",
)

PANEL_I18N_V45_TR_KEYS = (
    "engineMsg:",
    "limitedMsg:",
    "limitedUserMsg:",
)

PANEL_I18N_V46_MARKERS = (
    "let transcriptStatusRefresh = null",
    "function paintTranscriptStatusFromResolver(",
    "function refreshTranscriptVisibleI18n(",
    "transcriptVisibleI18nRefreshers.add(refreshTranscriptWidgetVisibleI18n)",
    "refreshTranscriptVisibleI18n();",
    "showStatus(() => panelT(\"panel.modules.chat.transcript.busyMsg\")",
    "showStatus(() => transcriptBlockedUserMessage(result))",
)

PANEL_I18N_V46_TR_KEYS = (
    "busyMsg:",
    "transcribing:",
)

PANEL_I18N_V47_MARKERS = (
    'panelT("panel.modules.chat.log.unknownError")',
    'panelT("panel.modules.chat.log.charsRemaining")',
    "PANEL_CHAT_LOG_MAX",
)

PANEL_I18N_V47_TR_KEYS = (
    "log:",
    "unknownError:",
    "charsRemaining:",
)

PANEL_I18N_V48_MARKERS = (
    "function scrollActivePanelNavChipIntoView(",
    'scrollIntoView({ behavior: "smooth", inline: "nearest", block: "nearest" })',
    "scrollActivePanelNavChipIntoView(btn)",
    "scrollActivePanelNavChipIntoView(",
)

PANEL_I18N_V49_MARKERS = (
    "function parsePanelChatErrorPayload(",
    "parsePanelChatErrorPayload(parsedPayload)",
    "errorPayload.kind",
    "HTTP 200 · error alanı",
)

PANEL_I18N_V50_MARKERS = (
    "let refreshChatBubbleBodies = null",
    "refreshChatBubbleBodies = function refreshChatBubbleBodiesImpl(",
    "function panelChatBubbleTextFromI18nMeta(",
    "data-panel-chat-error-kind",
    "data-panel-bubble-i18n",
    "if (typeof refreshChatBubbleBodies === \"function\") refreshChatBubbleBodies();",
)

PANEL_I18N_V51_MARKERS = (
    "function isPanelChatPhotoFallbackReply(",
    "skip200ErrorBubble",
    "isPanelChatPhotoFallbackReply(replyFor200)",
)

PANEL_I18N_V52_MARKERS = (
    "function focusableAttachMenuItems(",
    "function focusFirstAttachMenuItem(",
    "closePanelAttachMenu({ returnFocus: false })",
    "attachMenu?.addEventListener(\"keydown\"",
    "if (e.key === \"Tab\") {",
)

PANEL_I18N_V53_MARKERS = (
    'id="panel-kuantum-readiness-mock-banner"',
    'class="panel-quantum-readiness-banner"',
    'data-i18n="panel.modules.quantum.banner.demo"',
    'data-i18n="panel.modules.quantum.banner.localScan"',
    'data-i18n="panel.modules.quantum.banner.docsExample"',
    'data-i18n="panel.modules.quantum.banner.noLiveScan"',
    'data-i18n="panel.modules.quantum.banner.mvpPlanning"',
    'data-quantum-readiness-mock="true"',
    'data-i18n="panel.modules.quantum.readinessIntro"',
    'data-i18n="panel.modules.quantum.entropyLab.title"',
    'fetchQuantumReadiness',
    'refreshQuantumReadinessPanel',
)

PANEL_I18N_V53_TR_KEYS = (
    "banner:",
    "localScan:",
    "readinessIntro:",
    "readinessIntroLive:",
    "mock:",
    "titleLive:",
    "live:",
    "entropyLab:",
    "Kuantum Güvenlik Hazırlığı",
)

PANEL_I18N_V54_MARKERS = (
    'id="panel-quantum-generated-at-label"',
    'id="panel-quantum-findings-block"',
    'id="panel-quantum-entropy-dl"',
    'data-i18n="panel.modules.quantum.live.generatedAtLabel"',
    'data-i18n="panel.modules.quantum.live.findingsTitle"',
    'data-i18n="panel.modules.quantum.entropyLab.configuredLabel"',
    "formatQuantumGeneratedAt",
    "renderQuantumFindings",
    "applyQuantumEntropyLabSection",
    "hideQuantumLiveOnlyFields",
)

PANEL_I18N_V54_TR_KEYS = (
    "generatedAtLabel:",
    "findingsTitle:",
    "bodyLive:",
    "configuredLabel:",
    "fallbackYes:",
    "severity:",
)

PANEL_I18N_V55_MARKERS = (
    'id="panel-quantum-long-lived-block"',
    'id="panel-quantum-deps-block"',
    'id="panel-quantum-plan-block"',
    'data-i18n="panel.modules.quantum.live.longLivedTitle"',
    'data-i18n="panel.modules.quantum.live.hardDepsTitle"',
    'data-i18n="panel.modules.quantum.live.migrationPlanTitle"',
    "renderQuantumLongLivedData",
    "renderQuantumHardDeps",
    "renderQuantumMigrationPlan",
    "formatQuantumChangeCost",
    "formatQuantumPlanStatus",
)

PANEL_I18N_V55_TR_KEYS = (
    "longLivedTitle:",
    "hardDepsTitle:",
    "migrationPlanTitle:",
    "migrationPlanNote:",
    "changeCost:",
    "planStatus:",
)

PANEL_I18N_V56_MARKERS = (
    'id="panel-quantum-readiness-report-badge"',
    "panel-quantum-readiness-report-badge--mock",
    'data-i18n="panel.modules.quantum.readinessReport.label"',
    'data-i18n="panel.modules.quantum.readinessReport.mock"',
    "deriveQuantumReadinessReportBadge",
    "applyQuantumReadinessReportBadge",
)

PANEL_I18N_V56_TR_KEYS = (
    "readinessReport:",
    "label:",
    "tamamlandi:",
    "kismi:",
    "dogrulanamadi:",
)


PANEL_I18N_V57_MARKERS = (
    'id="panel-resource-mode-advisor-layer"',
    'id="panel-resource-mode-advisor-status"',
    'id="panel-resource-mode-advisor-hint"',
    'class="panel-resource-mode-advisor__layer-dot',
    'data-i18n="panel.modules.resourceModeAdvisor.statusLabel"',
    'data-i18n="panel.modules.resourceModeAdvisor.reasonLabel"',
    'data-i18n="panel.modules.resourceModeAdvisor.hintLabel"',
    'data-i18n="panel.modules.resourceModeAdvisor.disclaimer"',
    'panel-resource-mode-advisor__btn--secondary',
    "resourceModeAdvisorLayerLabel",
    "resourceModeAdvisorModeHint",
    "applyResourceModeAdvisorLayerDot",
)

PANEL_I18N_V57_TR_KEYS = (
    "statusLabel:",
    "reasonLabel:",
    "hintLabel:",
    "disclaimer:",
    "hints:",
    "layers:",
    "Beklemeli Mod",
    "Son karar kullanıcıya aittir.",
)

PANEL_I18N_V57_EN_KEYS = (
    "statusLabel:",
    "reasonLabel:",
    "hintLabel:",
    "disclaimer:",
    "hints:",
    "layers:",
    "Passive Mode",
    "The final decision is yours.",
)


PANEL_I18N_V58_MARKERS = (
    'data-i18n="panel.health.bridgeLlm.unknown"',
    'data-i18n-aria-label="panel.health.bridgeLlm.neverChecked"',
    'data-i18n="panel.nav.statusSub.sohbet"',
    'data-i18n-title="panel.nav.statusTitle.sohbet"',
    'class="panel-nav-status-pill lumos-status-pill lumos-status-pill--ready"',
    'class="panel-root-status"',
    'data-i18n="panel.rootStatus.title"',
    'data-i18n="panel.rootStatus.hydroponic"',
    'data-i18n="panel.rootStatus.katmanAFootnote"',
    'data-i18n="panel.rootStatus.katmanALink"',
    'data-i18n="panel.modules.quantum.disclaimer"',
    'lumos-status-pill--developing',
    'lumos-status-pill--active',
    'lumos-status-pill--layers',
)

PANEL_I18N_V58_TR_KEYS = (
    "status:",
    "statusSub:",
    "statusTitle:",
    "rootStatus:",
    "hydroponic:",
    "disclaimer:",
    "Sınırlı yerel mod",
    "katmanAFootnote:",
    "Katman A",
    "neverChecked:",
    "hiç kontrol edilmedi",
    "Kurulmadı",
)

PANEL_I18N_V58_EN_KEYS = (
    "status:",
    "statusSub:",
    "statusTitle:",
    "rootStatus:",
    "hydroponic:",
    "disclaimer:",
    "Limited local mode",
    "katmanAFootnote:",
    "Katman A",
    "neverChecked:",
    "never checked",
    "Not configured",
)


def test_panel_astro_i18n_wiring_present() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_MARKERS:
        assert token in text, f"missing panel i18n token: {token}"


def test_panel_messages_imported_into_catalogs() -> None:
    tr_text = _TR_MESSAGES.read_text(encoding="utf-8")
    en_text = _EN_MESSAGES.read_text(encoding="utf-8")
    assert 'import panel from "./panel/tr";' in tr_text
    assert "panel," in tr_text
    assert 'import panel from "./panel/en";' in en_text
    assert "panel," in en_text


def test_panel_dynamic_i18n_refreshes_after_initial_load() -> None:
    text = read_panel_source()
    assert 'window.addEventListener("lumos:localechange", refreshPanelI18n);' in text
    assert 'window.addEventListener("load", refreshPanelI18n, { once: true });' in text


def test_quantum_readiness_report_key_is_not_duplicated() -> None:
    assert _PANEL_TR.read_text(encoding="utf-8").count("readinessReport:") == 1
    assert _PANEL_EN.read_text(encoding="utf-8").count("readinessReport:") == 1


def test_panel_nav_keys_exist_in_panel_tr() -> None:
    text = _PANEL_TR.read_text(encoding="utf-8")
    for key in ("sohbet:", "gorevler:", "dosyalar:", "sections:", "ses:", "medya:", "sosyal:", "posta:"):
        assert key in text


def test_panel_astro_i18n_v2_module_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V2_MARKERS:
        assert token in text, f"missing panel i18n v2 token: {token}"


def test_panel_i18n_v2_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V2_TR_KEYS:
        assert key in tr_text, f"missing panel tr key fragment: {key}"
        assert key in en_text, f"missing panel en key fragment: {key}"


def test_panel_astro_i18n_v3_chat_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V3_MARKERS:
        assert token in text, f"missing panel i18n v3 token: {token}"


def test_panel_i18n_v3_chat_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V3_TR_KEYS:
        assert key in tr_text, f"missing panel tr v3 key fragment: {key}"
        assert key in en_text, f"missing panel en v3 key fragment: {key}"


def test_panel_astro_i18n_v4_gorevler_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V4_MARKERS:
        assert token in text, f"missing panel i18n v4 token: {token}"


def test_panel_i18n_v4_gorevler_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V4_TR_KEYS:
        assert key in tr_text, f"missing panel tr v4 key fragment: {key}"
        assert key in en_text, f"missing panel en v4 key fragment: {key}"


def test_panel_astro_i18n_v5_lumos_core_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V5_MARKERS:
        assert token in text, f"missing panel i18n v5 token: {token}"


def test_panel_i18n_v5_lumos_core_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V5_TR_KEYS:
        assert key in tr_text, f"missing panel tr v5 key fragment: {key}"
        assert key in en_text, f"missing panel en v5 key fragment: {key}"


def test_panel_astro_i18n_v6_shell_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V6_MARKERS:
        assert token in text, f"missing panel i18n v6 token: {token}"


def test_panel_i18n_v6_shell_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V6_TR_KEYS:
        assert key in tr_text, f"missing panel tr v6 key fragment: {key}"
        assert key in en_text, f"missing panel en v6 key fragment: {key}"


def test_panel_astro_i18n_v7_files_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V7_MARKERS:
        assert token in text, f"missing panel i18n v7 token: {token}"


def test_panel_i18n_v7_files_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V7_TR_KEYS:
        assert key in tr_text, f"missing panel tr v7 key fragment: {key}"
        assert key in en_text, f"missing panel en v7 key fragment: {key}"


def test_panel_astro_i18n_v8_chat_errors_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V8_MARKERS:
        assert token in text, f"missing panel i18n v8 token: {token}"


def test_panel_i18n_v8_chat_errors_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V8_TR_KEYS:
        assert key in tr_text, f"missing panel tr v8 key fragment: {key}"
        assert key in en_text, f"missing panel en v8 key fragment: {key}"


def test_panel_astro_i18n_v9_gorevler_evidence_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V9_MARKERS:
        assert token in text, f"missing panel i18n v9 token: {token}"


def test_panel_i18n_v9_gorevler_evidence_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V9_TR_KEYS:
        assert key in tr_text, f"missing panel tr v9 key fragment: {key}"
        assert key in en_text, f"missing panel en v9 key fragment: {key}"


def test_panel_astro_i18n_v10_transcript_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V10_MARKERS:
        assert token in text, f"missing panel i18n v10 token: {token}"
    assert "AUDIO_TRANSCRIPT_ENGINE_MSG" not in text


def test_panel_i18n_v10_transcript_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V10_TR_KEYS:
        assert key in tr_text, f"missing panel tr v10 key fragment: {key}"
        assert key in en_text, f"missing panel en v10 key fragment: {key}"


def test_panel_astro_i18n_v11_compose_hints_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V11_MARKERS:
        assert token in text, f"missing panel i18n v11 token: {token}"
    assert "PANEL_FULL_AUDIO_HINT" not in text
    assert 'setSendHint("Önce tek ek seçin")' not in text


def test_panel_i18n_v11_compose_hints_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V11_TR_KEYS:
        assert key in tr_text, f"missing panel tr v11 key fragment: {key}"
        assert key in en_text, f"missing panel en v11 key fragment: {key}"


def test_panel_astro_i18n_v12_camera_hints_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V12_MARKERS:
        assert token in text, f"missing panel i18n v12 token: {token}"
    assert 'setCameraHint("Bu tarayıcıda kamera' not in text
    assert "function setCameraHint(" not in text


def test_panel_i18n_v12_camera_hints_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V12_TR_KEYS:
        assert key in tr_text, f"missing panel tr v12 key fragment: {key}"
        assert key in en_text, f"missing panel en v12 key fragment: {key}"


def test_panel_astro_i18n_v13_record_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V13_MARKERS:
        assert token in text, f"missing panel i18n v13 token: {token}"
    assert "AUDIO_RECORD_UNSUPPORTED_HINT" not in text
    assert "function setAudioRecordHint(" not in text


def test_panel_i18n_v13_record_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V13_TR_KEYS:
        assert key in tr_text, f"missing panel tr v13 key fragment: {key}"
        assert key in en_text, f"missing panel en v13 key fragment: {key}"


def test_panel_astro_i18n_v14_voice_hints_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V14_MARKERS:
        assert token in text, f"missing panel i18n v14 token: {token}"
    assert "window.SpeechRecognition" not in text
    assert "window.webkitSpeechRecognition" not in text
    assert "VOICE_UNSUPPORTED_HINT" not in text
    assert "function setVoiceHint(" not in text


def test_panel_i18n_v14_voice_hints_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V14_TR_KEYS:
        assert key in tr_text, f"missing panel tr v14 key fragment: {key}"
        assert key in en_text, f"missing panel en v14 key fragment: {key}"


def test_panel_astro_i18n_v15_camera_photo_status_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V15_MARKERS:
        assert token in text, f"missing panel i18n v15 token: {token}"
    assert '"Seçilen görsel"' not in text
    assert '"Fotoğraf alındı"' not in text


def test_panel_i18n_v15_camera_photo_status_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V15_TR_KEYS:
        assert key in tr_text, f"missing panel tr v15 key fragment: {key}"
        assert key in en_text, f"missing panel en v15 key fragment: {key}"


def test_panel_astro_i18n_v16_compose_loading_audio_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V16_MARKERS:
        assert token in text, f"missing panel i18n v16 token: {token}"
    assert 'const loadingLabel = "Gönderiliyor…"' not in text
    assert '"Ses dosyası eklendi"' not in text
    assert '"Ses kaydı eklendi"' not in text
    assert 'audio.setAttribute("aria-label", "Ses kaydı")' not in text


def test_panel_i18n_v16_compose_loading_audio_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V16_TR_KEYS:
        assert key in tr_text, f"missing panel tr v16 key fragment: {key}"
        assert key in en_text, f"missing panel en v16 key fragment: {key}"


def test_panel_astro_i18n_v17_compose_send_clipboard_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V17_MARKERS:
        assert token in text, f"missing panel i18n v17 token: {token}"
    assert 'const sendLabel = "Gönder"' not in text
    assert 'cap.textContent = "Fotoğraf eklendi"' not in text
    assert 'const clipboardLabel = "Panodaki metni ilet"' not in text
    assert 'const clipboardConfirmLabel = "Onayla ve gönder"' not in text
    assert 'const clipboardLoadingLabel = "Gönderiliyor…"' not in text
    assert 'clipboardBtn.setAttribute("aria-label", "Panodaki metni ilet")' not in text
    assert 'clipboardBtn.setAttribute("aria-label", "Panodaki metni onayla ve gönder")' not in text


def test_panel_i18n_v17_compose_send_clipboard_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V17_TR_KEYS:
        assert key in tr_text, f"missing panel tr v17 key fragment: {key}"
        assert key in en_text, f"missing panel en v17 key fragment: {key}"


def test_panel_astro_i18n_v18_compose_replies_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V18_MARKERS:
        assert token in text, f"missing panel i18n v18 token: {token}"
    assert '"Bu turda net bir yanıt üretemedim' not in text
    assert '"Sunucudan gelen yanıtı işleyemedik' not in text
    assert 'appendBubble("lumos", "Sunucu yanıtı' not in text
    assert "Sunucu bu istek için ek metin dönmedi" not in text


def test_panel_i18n_v18_compose_replies_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V18_TR_KEYS:
        assert key in tr_text, f"missing panel tr v18 key fragment: {key}"
        assert key in en_text, f"missing panel en v18 key fragment: {key}"


def test_panel_astro_i18n_v19_gorev_chat_fallback_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V19_MARKERS:
        assert token in text, f"missing panel i18n v19 token: {token}"
    assert "Görev silme şu an kullanılamıyor (liste bağlanmadı)." not in text
    assert "Görev geri alma şu an kullanılamıyor (liste bağlanmadı)." not in text
    assert 'return "Bir mesaj yazın."' not in text
    assert "PANEL_GOREV_DELETE_RESTORE_HINT" not in text
    assert 'let reply = "Saat " + hh' not in text


def test_panel_i18n_v19_gorev_chat_fallback_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V19_TR_KEYS:
        assert key in tr_text, f"missing panel tr v19 key fragment: {key}"
        assert key in en_text, f"missing panel en v19 key fragment: {key}"


def test_panel_astro_i18n_v20_gorev_hints_infra_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V20_MARKERS:
        assert token in text, f"missing panel i18n v20 token: {token}"
    assert 'showHint("Görev yerel olarak kaydedildi.")' not in text
    assert 'confirm("Görev silinsin mi?")' not in text
    assert 'bridgeTokenMissing ? "Yapılandırılmamış"' not in text
    assert 'navigator.onLine ? "Çevrimiçi"' not in text


def test_panel_i18n_v20_gorev_hints_infra_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V20_TR_KEYS:
        assert key in tr_text, f"missing panel tr v20 key fragment: {key}"
        assert key in en_text, f"missing panel en v20 key fragment: {key}"


def test_panel_astro_i18n_v21_infra_health_labels_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V21_MARKERS:
        assert token in text, f"missing panel i18n v21 token: {token}"
    assert 'const PANEL_INFRA_UNAVAILABLE_MSG = "' not in text
    assert 'bridgeHealthLine = "deneniyor…"' not in text
    assert 'bridgeHealthLine = "bekleniyor…"' not in text
    assert 'userLine != null ? String(userLine) : "Köprü erişilemiyor (altyapı)"' not in text
    assert "if (photoTelemetry) {\n                let reason" not in text


def test_panel_i18n_v21_infra_health_labels_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V21_TR_KEYS:
        assert key in tr_text, f"missing panel tr v21 key fragment: {key}"
        assert key in en_text, f"missing panel en v21 key fragment: {key}"


def test_panel_astro_i18n_v22_settings_c6_c7_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V22_MARKERS:
        assert token in text, f"missing panel i18n v22 token: {token}"
    assert "<h3>Görünürlük ve Güvenlik Tercihleri</h3>" not in text
    assert "<h3>Varsayılanlar ve Kontrol</h3>" not in text


def test_panel_i18n_v22_settings_c6_c7_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V22_TR_KEYS:
        assert key in tr_text, f"missing panel tr v22 key fragment: {key}"
        assert key in en_text, f"missing panel en v22 key fragment: {key}"


def test_panel_astro_i18n_v23_cap_tts_files_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V23_MARKERS:
        assert token in text, f"missing panel i18n v23 token: {token}"
    assert 'aktif: { label: "AKTİF"' not in text
    assert 'dosyaHint.textContent = "Dosyayı seçin' not in text
    assert 'hint.textContent = panelUserVisibleText("Test çalışıyor' not in text
    assert 'btn.setAttribute("aria-label", "Sesli oku")' not in text
    assert 'panelActionFlash(btn, "Durduruldu"' not in text


def test_panel_i18n_v23_cap_tts_files_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V23_TR_KEYS:
        assert key in tr_text, f"missing panel tr v23 key fragment: {key}"
        assert key in en_text, f"missing panel en v23 key fragment: {key}"


def test_panel_astro_i18n_v24_settings_cors_cap_compose_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V24_MARKERS:
        assert token in text, f"missing panel i18n v24 token: {token}"
    assert 'corsEl.textContent = "Bu bilgi panelden okunamıyor (CORS)."' not in text
    assert '<span class="lumos-capability-name">1. Dosya okuma</span>' not in text
    assert '<span class="lumos-capability-name">7. Canlı deploy</span>' not in text


def test_panel_i18n_v24_settings_cors_cap_compose_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V24_TR_KEYS:
        assert key in tr_text, f"missing panel tr v24 key fragment: {key}"
        assert key in en_text, f"missing panel en v24 key fragment: {key}"


def test_panel_astro_i18n_v25_sistem_cap_actions_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V25_MARKERS:
        assert token in text, f"missing panel i18n v25 token: {token}"
    assert 'setSistemDurumuDd("panel-sistem-durumu-baglanti", "Bağlantı: "' not in text
    assert 'health + " · bağlantı: " + bridgeHealthLine' not in text
    assert 'visionCfg ? "Evet (görsel analiz için anahtar tanımlı)" : "Hayır"' not in text
    assert 'actions.setAttribute("aria-label", "Yanıt işlemleri")' not in text
    assert '<span class="lumos-capability-route">Yerel cihaz köprüsü bekleniyor.</span>' not in text
    assert '<span class="lumos-capability-route">manuel onay sonrası</span>' not in text
    assert 'data-cap-note-for="cap-file-read" hidden>' not in text


def test_panel_i18n_v25_sistem_cap_actions_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V25_TR_KEYS:
        assert key in tr_text, f"missing panel tr v25 key fragment: {key}"
        assert key in en_text, f"missing panel en v25 key fragment: {key}"


def test_panel_astro_i18n_v26_chat_status_ping_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V26_MARKERS:
        assert token in text, f"missing panel i18n v26 token: {token}"
    assert 'panelDebugText("OPTIONS OK (" + r.status + ")", "Sohbet bağlantısı hazır")' not in text
    assert 'panelDebugText("OPTIONS HTTP " + r.status, "Sohbet bağlantısı yanıt vermedi")' not in text
    assert 'panelDebugText("OPTIONS hata (ağ/CORS)", "Sohbet bağlantısı okunamadı")' not in text
    assert 'chatS + " · " + lastChatOptionsPingLine' not in text


def test_panel_i18n_v26_chat_status_ping_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V26_TR_KEYS:
        assert key in tr_text, f"missing panel tr v26 key fragment: {key}"
        assert key in en_text, f"missing panel en v26 key fragment: {key}"


def test_panel_astro_i18n_v27_outbox_bridge_debug_user_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V27_MARKERS:
        assert token in text, f"missing panel i18n v27 token: {token}"
    assert 'snippet ? "Sonuç alınamadı: " + snippet' not in text
    assert '"Sonuç kaydı bulunamadı veya bağlantı doğrulanamadı."' not in text
    assert '"Sonuç alınamadı. Bağlantıyı kontrol edin."' not in text
    assert '"Köprü şu an kullanılamıyor."' not in text
    assert '"Bağlantı testi tamamlandı."' not in text
    assert '"Bağlantı testi kısmen başarısız. Cihaz ayarlarını kontrol edin."' not in text


def test_panel_i18n_v27_outbox_bridge_debug_user_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V27_TR_KEYS:
        assert key in tr_text, f"missing panel tr v27 key fragment: {key}"
        assert key in en_text, f"missing panel en v27 key fragment: {key}"


def test_panel_astro_i18n_v28_bridge_token_tasks_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V28_MARKERS:
        assert token in text, f"missing panel i18n v28 token: {token}"
    assert "const BRIDGE_TOKEN_MSG" not in text
    assert '"kayıt başarısız"' not in text
    assert 'return shouldSuppressBridgeHint() ? "" : BRIDGE_TOKEN_MSG' not in text


def test_panel_i18n_v28_bridge_token_tasks_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V28_TR_KEYS:
        assert key in tr_text, f"missing panel tr v28 key fragment: {key}"
        assert key in en_text, f"missing panel en v28 key fragment: {key}"


def test_panel_astro_i18n_v29_strip_leak_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V29_MARKERS:
        assert token in text, f"missing panel i18n v29 token: {token}"
    assert '"bağlantı anahtarı"' not in text
    assert '"yerel sunucu"' not in text
    assert '"istek hatası"' not in text


def test_panel_i18n_v29_strip_leak_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V29_TR_KEYS:
        assert key in tr_text, f"missing panel tr v29 key fragment: {key}"
        assert key in en_text, f"missing panel en v29 key fragment: {key}"


def test_panel_astro_i18n_v30_strip_leak_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V30_MARKERS:
        assert token in text, f"missing panel i18n v30 token: {token}"
    assert '"bağlantı bilgisi"' not in text
    assert '"yol"' not in text
    assert '"iletim"' not in text
    assert '"son sonuç"' not in text
    assert '"görev kaydı"' not in text
    assert '"tarayıcı kısıtı"' not in text


def test_panel_i18n_v30_strip_leak_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V30_TR_KEYS:
        assert key in tr_text, f"missing panel tr v30 key fragment: {key}"
        assert key in en_text, f"missing panel en v30 key fragment: {key}"


def test_panel_astro_i18n_v31_strip_leak_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V31_MARKERS:
        assert token in text, f"missing panel i18n v31 token: {token}"
    assert 's.replace(/\bajan\b/gi, "cihaz")' not in text
    assert 's.replace(/\bendpoint\b/gi, "bağlantı")' not in text
    assert r's.replace(/\/tasks\b/gi, "görev")' not in text
    assert r's.replace(/\/controlled\b/gi, "kontrollü dosya")' not in text
    assert r's.replace(/\/status\b/gi, "durum")' not in text
    assert r's.replace(/\/health\b/gi, "sağlık")' not in text
    assert r's.replace(/\/chat\b/gi, "sohbet")' not in text
    assert 's.replace(/panel_tasks_server/gi, "görev servisi")' not in text
    assert r's.replace(/bridge_start\.sh/gi, "bağlantı başlatma")' not in text


def test_panel_i18n_v31_strip_leak_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V31_TR_KEYS:
        assert key in tr_text, f"missing panel tr v31 key fragment: {key}"
        assert key in en_text, f"missing panel en v31 key fragment: {key}"


def test_panel_astro_i18n_v32_mask_bridge_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V32_MARKERS:
        assert token in text, f"missing panel i18n v32 token: {token}"
    assert '"Bağlantı: ***"' not in text


def test_panel_i18n_v32_mask_bridge_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V32_TR_KEYS:
        assert key in tr_text, f"missing panel tr v32 key fragment: {key}"
        assert key in en_text, f"missing panel en v32 key fragment: {key}"


def test_panel_astro_i18n_v33_gorevler_plan_detail_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V33_MARKERS:
        assert token in text, f"missing panel i18n v33 token: {token}"
    assert 'appendDetailRow(dl, "Durum"' not in text
    assert 'appendDetailRow(detailTaskDl, "Durum"' not in text
    assert 'p.onayDurumu = "Onay kaydedildi"' not in text
    assert 'return "Henüz iletilmedi"' not in text


def test_panel_i18n_v33_gorevler_plan_detail_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V33_TR_KEYS:
        assert key in tr_text, f"missing panel tr v33 key fragment: {key}"
        assert key in en_text, f"missing panel en v33 key fragment: {key}"


def test_panel_astro_i18n_v34_gorevler_evidence_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V34_MARKERS:
        assert token in text, f"missing panel i18n v34 token: {token}"
    assert '"Köprü: "' not in text
    assert '"Görev: "' not in text
    assert '"Koruma: "' not in text
    assert '"Motor · "' not in text
    assert 'return "Köprü"' not in text


def test_panel_i18n_v34_gorevler_evidence_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V34_TR_KEYS:
        assert key in tr_text, f"missing panel tr v34 key fragment: {key}"
        assert key in en_text, f"missing panel en v34 key fragment: {key}"


def test_panel_astro_i18n_v35_datetime_when_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V35_MARKERS:
        assert token in text, f"missing panel i18n v35 token: {token}"
    assert 'parts.push("Yarın")' not in text
    assert 'parts.push("Bugün")' not in text
    assert 'toLocaleString("tr-TR"' not in text


def test_panel_i18n_v35_datetime_when_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V35_TR_KEYS:
        assert key in tr_text, f"missing panel tr v35 key fragment: {key}"
        assert key in en_text, f"missing panel en v35 key fragment: {key}"


def test_panel_astro_i18n_v36_gorevler_plan_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V36_MARKERS:
        assert token in text, f"missing panel i18n v36 token: {token}"
    assert 'title="Kuantum — araştırma alanı' not in text
    assert 'return "Plan: "' not in text
    assert 'tur = "Genel görev"' not in text
    assert 'risk = "Düşük"' not in text


def test_panel_i18n_v36_gorevler_plan_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V36_TR_KEYS:
        assert key in tr_text, f"missing panel tr v36 key fragment: {key}"
        assert key in en_text, f"missing panel en v36 key fragment: {key}"


def test_panel_astro_i18n_v37_conn_setup_link_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V37_MARKERS:
        assert token in text, f"missing panel i18n v37 token: {token}"


def test_panel_i18n_v37_conn_setup_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V37_TR_KEYS:
        assert key in tr_text, f"missing panel tr v37 key fragment: {key}"
        assert key in en_text, f"missing panel en v37 key fragment: {key}"


def test_panel_astro_i18n_v38_evidence_unreachable_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V38_MARKERS:
        assert token in text, f"missing panel i18n v38 token: {token}"


def test_panel_i18n_v38_evidence_unreachable_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V38_TR_KEYS:
        assert key in tr_text, f"missing panel tr v38 key fragment: {key}"
        assert key in en_text, f"missing panel en v38 key fragment: {key}"


def test_panel_astro_i18n_v39_hero_prefill_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V39_MARKERS:
        assert token in text, f"missing panel i18n v39 token: {token}"


def test_panel_i18n_v39_hero_prefill_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V39_TR_KEYS:
        assert key in tr_text, f"missing panel tr v39 key fragment: {key}"
        assert key in en_text, f"missing panel en v39 key fragment: {key}"


def test_panel_astro_i18n_v40_prod_error_classify_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V40_MARKERS:
        assert token in text, f"missing panel i18n v40 token: {token}"
    assert 'panelT("panel.modules.tasks.hints.saveFailed").replace("{error}"' not in text
    assert 'panelT("panel.modules.tasks.hints.completeFailed").replace("{error}"' not in text
    assert 'panelT("panel.modules.files.hints.writeFailed") + ": " + err' not in text


def test_panel_i18n_v40_prod_error_classify_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V40_TR_KEYS:
        assert key in tr_text, f"missing panel tr v40 key fragment: {key}"
        assert key in en_text, f"missing panel en v40 key fragment: {key}"


def test_panel_astro_i18n_v41_outbox_classified_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V41_MARKERS:
        assert token in text, f"missing panel i18n v41 token: {token}"
    assert 'panelT("panel.modules.media.outboxResultFailedWithSnippet").replace' not in text
    assert "String(text).trim().slice(0, 280)" not in text


def test_panel_i18n_v41_outbox_classified_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V41_TR_KEYS:
        assert key in tr_text, f"missing panel tr v41 key fragment: {key}"
        assert key in en_text, f"missing panel en v41 key fragment: {key}"


def test_panel_astro_i18n_v42_locale_hint_refresh_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V42_MARKERS:
        assert token in text, f"missing panel i18n v42 token: {token}"
    assert "function showHint(msg)" not in text


def test_panel_i18n_v42_locale_hint_refresh_has_no_new_catalog_keys() -> None:
    assert PANEL_I18N_V42_MARKERS


def test_panel_astro_i18n_v43_chat_http_classified_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V43_MARKERS:
        assert token in text, f"missing panel i18n v43 token: {token}"
    assert "upstreamErr && !PANEL_CHAT_TECH_LEAK_RE.test(upstreamErr)" not in text
    assert "panelUserVisibleText(upstreamErr)" not in text


def test_panel_i18n_v43_chat_http_classified_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V43_TR_KEYS:
        assert key in tr_text, f"missing panel tr v43 key fragment: {key}"
        assert key in en_text, f"missing panel en v43 key fragment: {key}"


def test_panel_astro_i18n_v44_locale_send_hint_refresh_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V44_MARKERS:
        assert token in text, f"missing panel i18n v44 token: {token}"
    assert "function setSendHint(msg)" not in text
    assert "const sendLabel = panelT(" not in text
    assert "const loadingLabel = panelT(" not in text


def test_panel_i18n_v44_locale_send_hint_refresh_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V44_TR_KEYS:
        assert key in tr_text, f"missing panel tr v44 key fragment: {key}"
        assert key in en_text, f"missing panel en v44 key fragment: {key}"


def test_panel_astro_i18n_v45_transcript_classified_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V45_MARKERS:
        assert token in text, f"missing panel i18n v45 token: {token}"
    assert 'showStatus(result.message || panelT("panel.modules.chat.transcript.limitedMsg"))' not in text
    assert 'showStatus(result.message || panelT("panel.modules.chat.transcript.engineMsg"))' not in text


def test_panel_i18n_v45_transcript_classified_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V45_TR_KEYS:
        assert key in tr_text, f"missing panel tr v45 key fragment: {key}"
        assert key in en_text, f"missing panel en v45 key fragment: {key}"


def test_panel_astro_i18n_v46_transcript_locale_refresh_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V46_MARKERS:
        assert token in text, f"missing panel i18n v46 token: {token}"
    assert 'showStatus(panelT("panel.modules.chat.transcript.busyMsg")' not in text
    assert "showStatus(transcribeUserBlock.message)" not in text


def test_panel_i18n_v46_transcript_locale_refresh_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V46_TR_KEYS:
        assert key in tr_text, f"missing panel tr v46 key fragment: {key}"
        assert key in en_text, f"missing panel en v46 key fragment: {key}"


def test_panel_astro_i18n_v47_chat_log_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V47_MARKERS:
        assert token in text, f"missing panel i18n v47 token: {token}"
    assert '"Bilinmeyen hata"' not in text
    assert "karakter daha" not in text


def test_panel_i18n_v47_chat_log_keys_in_catalogs() -> None:
    tr_text = _PANEL_TR.read_text(encoding="utf-8")
    en_text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V47_TR_KEYS:
        assert key in tr_text, f"missing panel tr v47 key fragment: {key}"
        assert key in en_text, f"missing panel en v47 key fragment: {key}"


def test_panel_astro_i18n_v48_mobile_nav_scroll_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V48_MARKERS:
        assert token in text, f"missing panel i18n v48 token: {token}"


def test_panel_astro_i18n_v49_chat_200_error_bubble_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V49_MARKERS:
        assert token in text, f"missing panel i18n v49 token: {token}"


def test_panel_astro_i18n_v50_locale_bubble_body_refresh_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V50_MARKERS:
        assert token in text, f"missing panel i18n v50 token: {token}"


def test_panel_astro_i18n_v52_attach_menu_focus_trap_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V52_MARKERS:
        assert token in text, f"missing panel i18n v52 token: {token}"


def test_panel_astro_i18n_v51_chat_200_photo_fallback_reply_priority_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V51_MARKERS:
        assert token in text, f"missing panel i18n v51 token: {token}"


def test_panel_astro_i18n_v53_quantum_readiness_mock_banner_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V53_MARKERS:
        assert token in text, f"missing panel i18n v53 token: {token}"


def test_panel_quantum_readiness_mock_banner_keys_in_panel_tr() -> None:
    text = _PANEL_TR.read_text(encoding="utf-8")
    for key in PANEL_I18N_V53_TR_KEYS:
        assert key in text, f"missing panel tr v53 key: {key}"


def test_panel_astro_i18n_v54_quantum_readiness_live_fields_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V54_MARKERS:
        assert token in text, f"missing panel i18n v54 token: {token}"


def test_panel_quantum_readiness_live_fields_keys_in_panel_tr() -> None:
    text = _PANEL_TR.read_text(encoding="utf-8")
    for key in PANEL_I18N_V54_TR_KEYS:
        assert key in text, f"missing panel tr v54 key: {key}"


def test_panel_astro_i18n_v55_quantum_readiness_migration_fields_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V55_MARKERS:
        assert token in text, f"missing panel i18n v55 token: {token}"


def test_panel_quantum_readiness_migration_fields_keys_in_panel_tr() -> None:
    text = _PANEL_TR.read_text(encoding="utf-8")
    for key in PANEL_I18N_V55_TR_KEYS:
        assert key in text, f"missing panel tr v55 key: {key}"


def test_panel_astro_i18n_v56_quantum_readiness_report_badge_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V56_MARKERS:
        assert token in text, f"missing panel i18n v56 token: {token}"


def test_panel_quantum_readiness_report_badge_keys_in_panel_tr() -> None:
    text = _PANEL_TR.read_text(encoding="utf-8")
    for key in PANEL_I18N_V56_TR_KEYS:
        assert key in text, f"missing panel tr v56 key: {key}"


def test_panel_quantum_readiness_report_badge_keys_in_panel_en() -> None:
    text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V56_TR_KEYS:
        assert key in text, f"missing panel en v56 key: {key}"


def test_panel_demo_share_i18n_is_resolved_when_rendered() -> None:
    text = read_panel_source()
    for token in (
        "function demoIdleHint()",
        "function demoReviewHint()",
        "function demoMessage()",
        "function dataTypeLabel()",
        "hintEl.textContent = demoIdleHint();",
        "hintEl.textContent = demoMessage();",
    ):
        assert token in text, f"missing render-time demo i18n token: {token}"

    assert 'const demoIdleHint = cfg.demoIdleHint || panelT(' not in text


def test_panel_astro_i18n_v57_resource_mode_advisor_card_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V57_MARKERS:
        assert token in text, f"missing panel i18n v57 token: {token}"


def test_panel_resource_mode_advisor_card_keys_in_panel_tr() -> None:
    text = _PANEL_TR.read_text(encoding="utf-8")
    for key in PANEL_I18N_V57_TR_KEYS:
        assert key in text, f"missing panel tr v57 key: {key}"


def test_panel_resource_mode_advisor_card_keys_in_panel_en() -> None:
    text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V57_EN_KEYS:
        assert key in text, f"missing panel en v57 key: {key}"


def test_panel_astro_i18n_v58_honest_module_status_wiring() -> None:
    text = read_panel_source()
    for token in PANEL_I18N_V58_MARKERS:
        assert token in text, f"missing panel i18n v58 token: {token}"
    assert 'data-i18n="panel.nav.inactiveBadge">Önizleme</span>' not in text


def test_panel_honest_module_status_keys_in_panel_tr() -> None:
    text = _PANEL_TR.read_text(encoding="utf-8")
    for key in PANEL_I18N_V58_TR_KEYS:
        assert key in text, f"missing panel tr v58 key: {key}"


def test_panel_honest_module_status_keys_in_panel_en() -> None:
    text = _PANEL_EN.read_text(encoding="utf-8")
    for key in PANEL_I18N_V58_EN_KEYS:
        assert key in text, f"missing panel en v58 key: {key}"
