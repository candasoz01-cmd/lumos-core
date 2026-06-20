/** Panel shell + module copy — English */
import type panelTr from "./tr";

const panelCommon: typeof panelTr.common = {
  badges: {
    externalService: "[External service]",
    demoNotConnected: "[Demo — not connected]",
    local: "[Local]",
    unknown: "[Unknown]",
  },
  form: {
    target: "Target",
    targetPlatform: "Target platform",
    recipient: "Recipient",
    contentSummary: "Content summary",
    postDraft: "Post draft",
    messageDraft: "Message draft",
    attachmentCount: "Attachment count",
    showSummary: "Show summary",
    sendDemoDisabled: "Send (demo off)",
    shareDemoDisabled: "Share (demo off)",
  },
  placeholders: {
    shareSummary: "Summary to share…",
    shareText: "Text to share…",
    emailBody: "Email body…",
    emailRecipient: "example@mail.com",
  },
  select: {
    externalSummary: "External summary / archive",
    localCopy: "Local copy",
    generalFeed: "Public feed",
    directMessage: "Direct message",
  },
  demo: {
    sendTitle: "Demo: real send is not connected",
    shareTitle: "Demo: real share is not connected",
    idleHint: "Demo mode: real send is not connected; preview only.",
    reviewHint: "Summary shown (demo). Send is off in this build; no connection yet.",
    approvedHint: "Summary confirmed. Press the button to send.",
    summaryFooter: "[Demo] No real send occurs.",
    summaryTarget: "Target: ",
    summaryContentPreview: "Content preview: ",
    summaryAttachmentCount: "Attachment count: ",
    summaryDataType: "Data type: ",
    medyaMsg: "Demo: media share is not connected yet.",
    sosyalMsg: "Demo: social share is not connected yet.",
    postaMsg: "Demo: email send is not connected yet.",
    defaultMsg: "Demo: real send is not connected yet.",
  },
};

const panel: typeof panelTr = {
  meta: {
    title: "Lumos Panel — Workspace",
  },
  header: {
    title: "Lumos Panel",
  },
  nav: {
    aria: "Workspace modules",
    lumos: "Lumos",
    panel: "panel",
    calisma: "Workspace",
    sohbet: "Chat",
    gorevler: "Tasks",
    ses: "Voice",
    medya: "Media",
    sosyal: "Social",
    posta: "Mail",
    dosyalar: "Files",
    kuantum: "Quantum",
    lumosCore: "Lumos core",
    yayincilik: "Publishing",
    yapayzeka: "AI",
    entegrasyon: "Integration",
    kimlik: "Identity",
    yetenekler: "Capabilities",
    guvenlik: "Security",
    dunya: "World",
    ayarlar: "Settings",
  },
  sections: {
    sohbet: "Chat",
    gorevler: "Tasks",
    ses: "Voice",
    medya: "Media",
    sosyal: "Social",
    posta: "Mail",
    dosyalar: "Files",
    kuantum: "Quantum",
    yayincilik: "Publishing",
    yapayzeka: "AI",
    entegrasyon: "Integration",
    kimlik: "Identity",
    yetenekler: "Capabilities",
    guvenlik: "Security",
    dunya: "World",
    ayarlar: "Settings",
  },
  common: panelCommon,
  modules: {
  chat: {
    historyAria: "Message history",
    empty: {
      default: "Lumos ready · Listening",
      limited: "Limited mode · Local actions available",
      limitedUser: "Limited mode · User choice",
      limitedSub: "Local tasks are available; actions that need the external bridge are on hold.",
      limitedUserSub: "Local tasks are available; the external chat bridge is not attempted in this mode.",
      offline: "Offline mode · No internet",
      offlineSub: "Local actions are available; external connections are not attempted in this mode.",
    },
    modeHints: {
      sendLimited: "Limited mode: no external chat bridge; local replies and task commands are available.",
      sendLimitedUser: "You are in limited mode (user choice); local replies and task commands are available.",
      sendOffline: "Offline mode: no internet or external bridge; local replies are available.",
    },
    capability: {
      title: "What can I do right now?",
      canDoSection: "I can",
      canDo1: "Save tasks, list them, and suggest short plans.",
      canDo2: "Read on-device settings and give practical notes.",
      wontDoSection: "I won't (yet)",
      wontDo1: "Run commands or change code.",
      wontDo2: "Perform permanent actions without approval.",
    },
    security: {
      approval: "Asks for approval before permanent actions.",
      secret: "Runs on-device; do not paste secrets into chat.",
      debugBridge: "Local bridge connected. Voice and task actions run on this device.",
      devicePerms: "Camera and microphone depend on device permissions.",
    },
    bubbles: {
      user: "You",
      lumos: "Lumos",
      warning: "Warning",
      actionsAria: "Reply actions",
    },
    compose: {
      placeholder: "Write your message",
      send: "Send",
      sendLoading: "Sending…",
      attachTitle: "Add",
      attachAria: "Add file or media",
      attachFile: "Upload file",
      attachPhoto: "Choose photo",
      attachCamera: "Open camera",
      attachClipboard: "Send clipboard text",
      attachAudio: "Upload audio file",
      attachRecord: "Record audio",
      attachRecordTitle: "Record with microphone; does not transcribe (unlike Speak to type)",
      cameraTitle: "Camera / image input",
      cameraAria: "Camera / image input",
      voiceTitleSupported: "Speak to type (transcribe) — uses browser speech recognition",
      voiceAriaSupported: "Speak to type and transcribe; uses browser speech recognition",
      voiceTitleUnsupported: "Speak to type not supported",
      voiceAriaUnsupported: "Speak to type is not supported in this browser",
      galleryAria: "Choose image from gallery",
      audioFileAria: "Choose audio file",
      audioPreviewAria: "Audio recording preview",
      stopRecord: "Stop",
      cancelRecord: "Cancel",
      rerecord: "Re-record",
      transcribe: "Transcribe",
      photoSelectedLabel: "Selected image",
      photoCapturedStatus: "Photo captured",
      photoAdded: "Photo added",
      clipboardConfirm: "Confirm and send",
      clipboardConfirmAria: "Confirm and send clipboard text",
      clipboardConfirmTitle: "Confirm and send clipboard text",
      audioFileAttached: "Audio file attached",
      audioRecordAttached: "Audio recording attached",
      audioRecordAria: "Audio recording",
      hints: {
        pickOneAttachment: "Choose one attachment at a time",
        photoReadFailed: "Could not read the photo.",
        audioOnly: "Choose an audio file only.",
        audioReadFailed: "Could not read the audio file.",
        photoOffline: "Image analysis is unavailable offline.",
        photoLimitedUser: "You are in limited mode (user choice); image analysis is not attempted.",
        photoLimited: "Image analysis is unavailable in limited mode.",
        audioOffline: "Audio stays in the local chat thread while offline.",
        audioLimitedUser:
          "You are in limited mode (user choice); audio is not sent to external chat.",
        audioLimited: "Audio stays in the local chat thread in limited mode.",
        limitedPhotoReply:
          "Photo analysis is unavailable in limited mode; the external image API bridge is not connected.",
        offlinePhotoReply:
          "Photo analysis is unavailable offline; internet access is disabled.",
        limitedAudioReply:
          "Audio recordings stay on this device in limited mode; they are not sent to external chat.",
        offlineAudioReply:
          "Audio recordings stay on this device while offline; they are not sent to external chat.",
        fullAudioReply:
          "Audio recordings stay on this device in full mode; they are not sent to the external bridge.",
        fullAudioHint:
          "In full mode audio is not sent to the external bridge; add text or use «Transcribe».",
        responseUnreadable: "Could not read the response.",
        sentOk: "Text delivered.",
        clipboardUnsupported: "Clipboard read is not supported in this browser.",
        clipboardDenied:
          "Clipboard access was denied. Check browser permission or page focus.",
        clipboardReadFailedPrefix: "Could not read clipboard: ",
        clipboardEmpty: "Clipboard appears empty.",
        clipboardReadFailed: "Could not read clipboard.",
        clipboardReadyWithSnippet:
          'Clipboard text ready: "{snippet}" Tap again to send.',
        clipboardReadyEmpty: 'Clipboard text ready: "" Tap again to send.',
        httpSendFailedDebugPrefix: "Send failed (HTTP ",
        httpSendFailedDebugSuffix: "). Try again.",
        requestErrorDebugPrefix: "Request error: ",
        emptyReply:
          "I could not produce a clear reply this turn; I will try again shortly.",
        responseUnusableBubble:
          "We could not process the server response. You can try again shortly.",
        gorevServerReplyPrefix: "Server reply:\n",
        gorevNoExtraServerText:
          "The server returned no extra text for this request (the task is already saved locally).",
        photoNoVision: "Photo added; image analysis is not active yet.",
      },
      cameraHints: {
        unsupported: "Camera input is not supported in this browser.",
        permissionDenied: "Camera permission was not granted.",
        pickImageFile: "Please choose an image file.",
        previewFailed: "Could not create preview.",
        captureUnsupported: "Camera is not supported in this browser.",
        photoPickUnsupported: "Image selection is not supported in this browser.",
        fileUploadPreparing: "File upload is being prepared in this view.",
      },
      record: {
        previewLabel: "Recording ready — add to chat with Send",
        unsupported: "Audio recording is not supported in this browser.",
        recordingHint: "Recording audio (not transcribed) — add with Send when done",
        recordingStatus: "Recording audio…",
        tooShort: "Recording too short or empty; try again.",
        stopFailed: "Could not stop recording.",
        startFailed: "Could not start audio recording in this browser.",
        errorDuring: "An error occurred during recording.",
        micDenied: "Microphone permission was not granted.",
        micUnavailable: "Microphone is unavailable.",
      },
      voiceHints: {
        serviceUnavailable: "Browser speech recognition service is currently unavailable.",
        unsupported: "Speak to type is not supported in this browser.",
        noSpeech: "No speech detected.",
        micUnavailable: "Microphone is unavailable.",
        micDenied: "Microphone permission was not granted.",
        aborted: "Voice input was cancelled.",
        failed: "Voice input failed.",
        startFailed: "Could not start speech recognition. Try again.",
        noResult: "No speech detected or the browser did not produce a result. Try again.",
      },
    },
    tts: {
      speak: "Read aloud",
      stopSpeaking: "Stop read aloud",
      stop: "Stop",
      stopped: "Stopped",
      failed: "Read aloud failed",
      error: "Error",
      unsupported: "Not supported",
      unsupportedFeature: "Read aloud not supported",
      empty: "Empty",
    },
    gorev: {
      confirmMini: "Mini task added: {title}",
      confirmWithWhen: "Task added: {title} — {when}",
      confirm: "Task added: {title}",
      deleteUnavailable: "Task delete is unavailable right now (task list not wired).",
      restoreUnavailable: "Task restore is unavailable right now (task list not wired).",
      deleteRestoreHint:
        ' To undo, type «görev geri al» or use «Restore last deleted» on the Tasks screen.',
      notFound:
        'Task not found: «{ref}». Check the title or task id (tsk_…).',
      deleted: 'Task deleted: "{title}".',
      deleteMissingRef: "Task name missing. Example: görev sil alışveriş",
      deleteConfirm: 'Delete "{ref}"?',
      deleteCancelled: "Delete cancelled.",
      deleteFailed: "Could not delete ({error}).",
      restoreNothing: "No deleted task to restore.",
      restoreVerifyFailed: "Task could not be added back to the list; restore not verified.",
      restored: 'Task restored: "{title}".',
    },
    localReply: {
      emptyMessage: "Type a message.",
      navGorevler:
        "Opened Tasks; browse the list or add one with «görev oluştur title».",
      navAyarlar:
        "Opened Settings. External chat is off without the bridge; local tasks still work.",
      navKimlik:
        "Opened Identity; connection and identity settings are here.",
      navAyarlarOffline:
        "Opened Settings. Offline mode; local tasks still work.",
      keywordGorev:
        "Open Tasks to see the list. To add: «görev oluştur title» (e.g. görev oluştur shopping).",
      keywordKayit: "Open Media to browse files.",
      keywordAkis: "Open Social to see the current feed.",
      limitedDefault:
        "You are in limited mode (user choice); local tasks and short hints work — e.g. «görev oluştur title» or «görevler».",
      offlineDefault:
        "You are offline; no internet. Local tasks work — e.g. «görev oluştur title» or «görevler».",
      timeBase: "Time {hh}:{mm}. Today {date}.",
      timeWeekdaySuffix: " Today is {weekday}.",
      weekday0: "Sunday",
      weekday1: "Monday",
      weekday2: "Tuesday",
      weekday3: "Wednesday",
      weekday4: "Thursday",
      weekday5: "Friday",
      weekday6: "Saturday",
    },
    bridgeBadgeLimited: "Limited mode",
    transcript: {
      engineMsg: "Speech-to-text engine is not connected yet.",
      limitedMsg: "Speech-to-text is unavailable in limited mode; external bridge is not connected.",
      limitedUserMsg:
        "You are in limited mode (user choice); speech-to-text is not attempted in this mode.",
      offlineMsg: "Speech-to-text is unavailable offline; internet access is disabled.",
      busyMsg: "Transcribing…",
      privacyMsg:
        "Text is preview only; «Add to chat» copies it to the compose field without sending.",
      musicWarnMsg:
        "This audio may contain music. Transcription results may be unreliable.",
      failedMusic:
        "Transcription failed. The audio may be music, noisy, or non-speech.",
      failedSpeech: "Transcription failed.",
      lowQualityWarnMsg:
        "Text may be low confidence; try again with a clearer speech recording.",
      missingAudio: "No audio data or clip is too short.",
      networkFailed: "Transcription failed. Check your connection and try again.",
      addToChat: "Add to chat",
      transcribing: "Transcribing…",
      previewAria: "Transcript preview",
    },
    errors: {
      network_error: "Delivery failed. Check your connection and try again.",
      timeout: "Response timed out. Try again in a moment.",
      unauthorized: "Connection could not be verified. Check device settings and try again.",
      server_error: "Chat is temporarily unavailable. Try again in a moment.",
      model_error: "Could not produce a reply. Try again in a moment.",
      unknown_error: "Something unexpected happened. Try again in a moment.",
    },
  },
  tasks: {
    eyebrow: "Operations",
    intro:
      "Tasks are written to the task record on your device; no transmission is required when adding a task. If the server is down, the list is shown from the browser cache.",
    form: {
      titleLabel: "Task name",
      titlePlaceholder: "Write a short title…",
      priorityLabel: "Priority",
      statusLabel: "Status",
      addBtn: "Add task",
    },
    priority: {
      dusuk: "Low",
      orta: "Medium",
      yuksek: "High",
    },
    status: {
      bekliyor: "Waiting",
      onay_bekliyor: "Awaiting approval",
      tamamlandi: "Completed",
    },
    list: {
      heading: "Task list",
      filterAria: "Task status filter",
      filterAll: "All",
      filterPending: "Pending",
      filterDone: "Completed",
      clearLocal: "Clear local list",
      restore: "Undo",
      syncBadge: "this device only / server sync off",
      syncBadgeTitle: "Tasks are kept on this device only; the server task API is unreachable.",
      listAria: "Task list",
      metaStatus: "Status",
      metaPriority: "Priority",
      cardAriaPrefix: "Task",
      cardAriaSuffix: "show details",
    },
    empty: {
      listDefault: "No tasks yet. Enter a short title above and use «Add task».",
      listFilter: "No tasks in this filter. Switch to «All» to see every task.",
      evidence: "No server evidence yet",
    },
    detail: {
      title: "Task",
      close: "Close",
      complete: "Complete",
      delete: "Delete",
      bridge: "Send task",
      bridgeNote: "Task transmission is waiting for bridge connection.",
      secTask: "Task",
      secPlan: "Task plan",
      secBridge: "Transmission response",
      planTitle: "Task plan",
      planConfirm: "Confirm plan",
      planDismiss: "Save only",
      lowRiskNote: "Low risk. Automatic plan; nothing was executed.",
      evidenceAria: "Latest operation evidence",
      evidenceSummaryPrefix: "Latest operation evidence: ",
      evidenceContinue: "Continue from here",
    },
    hints: {
      savedLocal: "Task saved locally.",
      titleEmpty: "Task name cannot be empty.",
      saveFailed: "Could not save task ({error}).",
      savedWithPlan: "Task saved; showing plan.",
      bridgeFailed: "Transmission failed. Check connection and try again.",
      bridgeSent: "Task sent.",
      bridgeAccepted: "Accepted for processing.",
      completeFailed: "Could not complete ({error}).",
      deleted: "Task deleted.",
      deleteFailed: "Could not delete ({error}).",
      restoreFailed: "Could not undo ({error}).",
      clearLocalDone: "Local list cleared; server records were not changed.",
    },
    confirm: {
      deleteOpen: "Delete this task?",
      clearLocal:
        "Clear the local task list? Server task records will not be changed.",
    },
  },
  files: {
    intro:
      "Pick a file from your device; the Lumos bridge ingests it and returns its name, type, and size. Plain-text formats (.txt, .md, .json, .csv) get a short summary. PDF and Word (DOCX) are not processed in this phase.",
    historyHeading: "Recent uploads",
    historyDeviceNote: "Stored on this device only; up to 5 entries.",
    form: {
      pickLabel: "Choose file",
      uploadBtn: "Upload and analyze",
    },
    hints: {
      attachNavigate: "Choose a file, then «Upload and analyze».",
      pickFirst: "Choose a file first.",
      readFailed: "Could not read the file as text.",
      unreachable: "Could not reach the server. Check connection settings.",
      writeFailed: "Could not write the file",
      readFailedBridge: "Could not read the file",
      sizeLimitPrefix: "File size exceeds the controlled write limit (",
      sizeLimitSuffix: " bytes).",
    },
    result: {
      metaTitle: "File details",
      infoTitle: "Info",
      alertTitle: "Warning",
      summaryTitle: "Short summary",
      transcriptTitle: "Transcribe",
      metaFilename: "File name",
      metaSize: "Size",
      metaKind: "Type",
      metaExt: "Extension",
    },
    history: {
      replayAriaPrefix: "Show results again: ",
      replayAria: "Show results again",
      statusAudio: "Audio — no analysis",
      statusWarn: "Warning",
      statusSummaryDone: "Summary generated",
      statusSummaryReady: "Summary ready",
      statusDone: "Completed",
    },
    messages: {
      unsupportedAudio:
        "File selected. Audio files are not analyzed in the Files tab in this phase.",
      unsupportedExe: "The file is not executed; only file metadata is recorded.",
      unsupportedDoc: "PDF and Word (DOCX) content is not processed in this phase.",
      unsupportedGeneric: "This file type is not processed in this phase.",
      infoSummary: "A summary was generated for this file.",
      infoPy: "The file is shown as plain text; code is not executed in this phase.",
      summaryJsonArray: "JSON array: {count} items.",
      summaryJsonObject: "JSON object: {count} keys.",
      summaryCsv: "CSV: about {count} rows.",
      bytesSuffix: " bytes",
    },
  },
  voice: {
    intro:
      "This tab summarizes an approach where voice input stays in the interface layer as it becomes text and commands, and the decision remains with you. The chat bar microphone depends on your device, browser, and granted permissions; it may not be supported in every environment.",
    c1Title: "Speech to text",
    c1Body:
      "Spoken input can be turned into text and command steps so it can be reviewed on screen.",
    c2Title: "Interface layer",
    c2Body:
      "Voice is not treated as a substitute authority; it is a layer the user can see and correct.",
    c3Title: "Decision with the user",
    c3Body: "Summarized commands or text should be clearly under your control before anything is applied.",
    c4Title: "Misunderstanding and confirmation",
    c4Body:
      "When recognition is uncertain or low-confidence, Lumos aims to pause and clarify rather than proceed alone.",
    c5Title: "Local processing first",
    c5Body:
      "Where possible the first step stays on the device; if a remote service is needed, that should remain visible.",
  },
  media: {
    intro:
      "This tab summarizes principles for organizing image, audio, video, and file flows: pre-share review, visible data paths, and separating source from output. The chat bar camera also depends on device, browser, and permission support; it may not work in every environment.",
    outboxTitle: "Latest output summary (read-only)",
    outboxIntro:
      "Summary read from transmission for the latest task or chat output. If there is no record, a short notice is shown.",
    outboxRefresh: "Refresh",
    outboxResultFailedWithSnippet: "Could not load result: {snippet}",
    outboxResultNotFound: "No result record found or connection could not be verified.",
    outboxFetchFailed: "Could not load result. Check your connection.",
    sharePreviewIntro: "Share draft preview — real send is off in this build.",
    dataType: "Media summary",
    c1Title: "Streams and types",
    c1Body:
      "Different media types can be followed in one working pattern; which file is used where can be easier to read.",
    c2Title: "Pre-share review",
    c2Body:
      "Before anything leaves the device, content summaries and intended use are meant to be shown to you.",
    c3Title: "Handoff to external services",
    c3Body:
      "Steps where a file or preview is sent for external processing are not hidden; connection and purpose stay clearer.",
    c4Title: "Editing and conversion",
    c4Body:
      "Trimming, format changes, or conversion are suggested as ordered, reversible steps.",
    c5Title: "Source and output",
    c5Body:
      "Original material and generated output are distinguished so you can see clearly what is being shared.",
  },
  social: {
    intro:
      "This tab summarizes keeping drafts with the user for outward-facing content, increasing platform awareness, and prioritizing explicit approval for lasting posts.",
    sharePreviewIntro: "Social share draft preview — real sharing is off in this build.",
    dataType: "Social text",
    c1Title: "Pre-share review",
    c1Body:
      "Before a post is published, summary, target, and visibility are meant to be shown to you one last time.",
    c2Title: "Target platform",
    c2Body:
      "How content will appear in a given environment and which rules apply can be made more visible.",
    c3Title: "Post draft",
    c3Body: "Text and attachments stay in draft form; nothing goes live without your edits.",
    c4Title: "Approval for risky sharing",
    c4Body:
      "Permanent, broad-audience, or hard-to-undo shares aim to require extra confirmation.",
    c5Title: "No automatic publishing",
    c5Body: "Lumos does not publish silently on your behalf; the send decision stays with you.",
  },
  mail: {
    intro:
      "This tab summarizes an approach centered on email drafts, attachment and recipient checks, and explicit approval before sending.",
    sharePreviewIntro: "Email draft preview — real send is off in this build.",
    dataType: "Email",
    c1Title: "Draft-first workflow",
    c1Body:
      "Messages are edited as drafts first; sending is not expected before you review the content.",
    c2Title: "Attachments and recipients",
    c2Body:
      "Attachment lists and recipient fields aim to be summarized clearly before send.",
    c3Title: "Approval before send",
    c3Body:
      "The Send step requires deliberate confirmation; invisible “one-click” send is not the goal.",
    c4Title: "Wrong recipient and sensitive data",
    c4Body:
      "Suspicious recipient matches or sensitive content aims to surface warnings.",
    c5Title: "No automatic send",
    c5Body:
      "Lumos does not deliver mail on its own; the final send decision remains yours.",
  },
  publishing: {
    intro:
      "This tab summarizes making it clear which content goes to which channel in live or recorded broadcast flows, with pre-broadcast checks and explicit approval for recording or sharing.",
    c1Title: "Live and recorded streams",
    c1Body:
      "Whether a broadcast is live or recording-based and the audience context aim to be clearly indicated.",
    c2Title: "Content and channel mapping",
    c2Body:
      "Which video or audio feeds which output can be made trackable with a clear summary.",
    c3Title: "Pre-broadcast checks",
    c3Body: "Preview and final warning steps should not be skipped before going on air.",
    c4Title: "Recording and sharing approval",
    c4Body:
      "Session recording or sharing a clip outward are treated as actions that require separate approval.",
    c5Title: "Broadcast risks",
    c5Body:
      "Visibility, copyright, and privacy risks aim to be recalled in short, plain language; no promise of specific legal outcomes is made.",
  },
  ai: {
    intro:
      "This tab summarizes treating AI not as an authority that decides for you, but as a helper layer that gathers context, organizes options, and makes the decision process clearer.",
    c1Title: "Gathering context",
    c1Body:
      "Lumos aims to build a clearer task context by weighing your request together with the current workspace and related information.",
    c2Title: "Suggestions and options",
    c2Body:
      "AI does not present a single outcome as unquestionably correct; it surfaces options, uncertainties, and points that need attention.",
    c3Title: "Decision with the user",
    c3Body:
      "Lumos may suggest, shorten paths, and reduce confusion; the final decision still belongs to you.",
    c4Title: "Pausing risky actions",
    c4Body:
      "For permanent, costly, or hard-to-reverse steps, AI should inform rather than auto-advance, and wait for explicit approval.",
    c5Title: "Surfacing uncertainty",
    c5Body:
      "When data is missing, confidence is low, or information conflicts, Lumos aims not to hide that, but to show where it is unsure.",
    c6Title: "Limits of AI",
    c6Body:
      "Lumos does not claim AI is always right. The goal is not to sideline you, but to help you act with clearer awareness and control.",
  },
  quantum: {
    intro:
      "This tab treats probability, uncertainty, and security research together; transparent limits take priority over hard promises.",
    c1Title: "Quantum security research",
    c1Body:
      "This area is where Lumos will evaluate post-quantum cryptography and advanced security approaches in the future. The current system does not claim to use quantum encryption.",
    c2Title: "Multiple possibilities",
    c2Body:
      "Lumos does not present one path as definitively certain; it keeps possible routes and uncertainties visible together.",
    c3Title: "Balancing uncertainty",
    c3Body:
      "When data is incomplete, Lumos does not fill gaps blindly; it separates what is known from what is not.",
    c4Title: "Boundary of decision",
    c4Body:
      "A quantum-oriented approach does not replace judgment; it organizes options and leaves the final direction to your will.",
  },
  integration: {
    intro:
      "This tab summarizes Lumos building a controlled bridge among local tools, external services, API connections, and applications. The goal is not to wire everything without limits, but to keep connection scope, data flow, and user approval visible.",
    c1Title: "Service connections",
    c1Body:
      "Lumos aims for services and apps to work in a cleaner shared flow. Each connection’s purpose and which action it affects should be explicit.",
    c2Title: "API bridge",
    c2Body:
      "API integrations let Lumos talk to external systems in a controlled way. These links mean scoped capabilities and clear intent—not unlimited privilege.",
    c3Title: "Local vs. external",
    c3Body:
      "Lumos aims to separate work that stays on-device from steps sent to external services, so you can see which step is which more clearly.",
    c4Title: "Scope and approval",
    c4Body:
      "Before a connection is used, what it can access, when it activates, and what approval you must give should be spelled out.",
    c5Title: "Data-flow visibility",
    c5Body:
      "Where files, text, media, or task data is shared and at which step it is processed should become easier to follow.",
    c6Title: "No unlimited power",
    c6Body:
      "Lumos integrations do not mean automatic, unlimited authority. Each connection should be designed to work within user control and security limits.",
  },
  identity: {
    intro:
      "This tab summarizes Lumos’s digital AI identity tied to the user. The goal is not to create an identity that replaces you, but to make your preferences, limits, permissions, and representational context easier to see and manage.",
    c1Title: "Digital AI identity",
    c1Body:
      "Lumos is structured around a digital AI identity linked to how you work, your preferences, and your boundaries. That identity does not replace you; it makes how you are represented in digital actions easier to understand.",
    c2Title: "Boundary of representation",
    c2Body:
      "Lumos is not meant to act without limits on your behalf. It aims to make clearer which actions run in which context and with which authority.",
    c3Title: "Sessions and service links",
    c3Body:
      "Connected services, sessions, and workspaces can be framed so which link is used for which task is easier to grasp.",
    c4Title: "Permission visibility",
    c4Body:
      "For apps, files, or services, what granted permissions might imply should be shown more openly so consent stays informed.",
    c5Title: "Preferences and memory limits",
    c5Body:
      "Lumos may honor preferences and habits, but how that information is used, bounded, and activated must remain explicit.",
    c6Title: "Identity security boundary",
    c6Body:
      "Lumos does not guarantee identity security absolutely. Instead it aims to make sessions, permissions, representation, and preferences easier to audit.",
  },
  security: {
    c1Title: "Explicit approval",
    c1Body: "For risky, permanent, or hard-to-reverse actions, Lumos leaves the final call with you.",
    c2Title: "Risk visibility",
    c2Body:
      "Lumos aims to surface likely outcomes, scope, and points to watch before an action starts.",
    c3Title: "Data-path awareness",
    c3Body:
      "Whether data stayed on-device, went to an external service, and where it was processed is made easier to understand.",
    c4Title: "Security boundary",
    c4Body:
      "Lumos does not promise absolute security; it aims to give you a more controlled, traceable, and conscious operating space.",
  },
  world: {
    intro:
      "This tab summarizes a measured, global product stance: sensitive to different languages, regions, and accessibility needs, without collapsing into a single culture.",
    c1Title: "Language, region, accessibility",
    c1Body:
      "Language choice, local formats, and accessibility options aim to be more visible in interface and content.",
    c2Title: "Adapting to how people work",
    c2Body:
      "The experience aims to adapt across devices, connectivity, and environments without excess.",
    c3Title: "Localization",
    c3Body:
      "Text and dates can follow local norms; translation and context issues aim to stay transparent.",
    c4Title: "Global, plural lens",
    c4Body:
      "Without locking to one center’s viewpoint, the frame respects diverse user needs.",
    c5Title: "Human-centered technology",
    c5Body:
      "Lumos aims to adopt a line that keeps decisions and privacy boundaries with people rather than replacing them with technology.",
  },
  settings: {
    intro:
      "This tab summarizes keeping preferences, connection and permission limits, and default behaviors under your control and visible.",
    c1Title: "User mode",
    c1Body:
      "You choose how much the panel runs. This preference is separate from infrastructure connection status; the bridge badge only shows technical status.",
    c2Title: "Infrastructure status",
    c2Body:
      "Bridge, key, health, and network status — a technical summary independent of user mode.",
    c3Title: "User preferences",
    c3Body: "Options like language, theme, and notification intensity aim to be grouped clearly.",
    c4Title: "Limits and permissions",
    c4Body:
      "Which feature depends on which permission is shown in short summaries; permissions you turned off are not silently re-enabled.",
    c5Title: "Connection settings",
    c5Body:
      "External service and account links can be seen in one place; disconnecting and reconnecting stays with you when needed.",
    c6Title: "Visibility and security preferences",
    c6Body:
      "Sharing, logging, or data retention options are separated from each other; each is presented with a clear explanation.",
    c7Title: "Defaults and control",
    c7Body:
      "Default behaviors are shown to you before acceptance; changes aim to remain reversible.",
    corsMsg: "This information cannot be read from the panel (CORS).",
    infraSummaryAria: "Infrastructure status summary",
    connectionLine: "Connection: {line}",
    healthWithConnection: "{health} · connection: {line}",
    visionConfiguredYes: "Yes (key configured for visual analysis)",
    visionConfiguredNo: "No",
    chatPingReady: "Chat connection ready",
    chatPingNoResponse: "Chat connection did not respond",
    chatPingUnreadable: "Chat connection could not be read",
    chatWithPing: "{chat} · {ping}",
  },
  capabilities: {
    intro:
      "Summarizes which operations Lumos connects to through which link or panel surface. «Connection test» only verifies rows 1–3; row 4 checks local evidence.",
    legendAria: "Status legend",
    legendActive: "ACTIVE — evidence exists or runs in limited mode",
    legendPassive: "PASSIVE — no working path right now",
    legendDev: "IN DEVELOPMENT — planned, not connected yet",
    testBtn: "Connection test",
    testRunning: "Test running…",
    testBridgeUnavailable: "Bridge is unavailable right now.",
    testDone: "Connection test completed.",
    testPartialFailed: "Connection test partially failed. Check device settings.",
    bridgePending: "Waiting for bridge connection.",
    routeTerminal: "Waiting for local device bridge.",
    routeNone: "—",
    routeManualApproval: "after manual approval",
    row1: "1. File read",
    row2: "2. File write",
    row3: "3. Task create",
    row4: "4. Task complete",
    row5: "5. Terminal command",
    row6: "6. Open Mac app",
    row7: "7. Live deploy",
    status: {
      active: "ACTIVE",
      passive: "PASSIVE",
      limited: "LIMITED",
      dev: "IN DEVELOPMENT",
    },
  },
  },
  shell: {
    conn: {
      pending: "Connecting",
      ok: "Connected",
      bad: "Offline",
      limited: "Limited mode",
      ariaLabel: "Infrastructure connection status",
      title: "Infrastructure: bridge connection",
    },
    infra: {
      tokenMissing: "Not configured",
      tokenPresent: "Configured",
      online: "Online",
      offline: "Offline",
      labelBridge: "Bridge",
      labelToken: "Key",
      labelHealth: "Health",
      labelInternet: "Internet",
      unavailableShort: "Bridge unavailable (infrastructure)",
      unavailableMsg:
        "Bridge unavailable (infrastructure). Check your connection and try again.",
      healthPending: "pending…",
      healthTrying: "trying…",
      healthOk: "OK",
      healthUnreachable: "unreachable",
    },
    userMode: {
      menuOffline: "Offline",
      menuLimited: "Limited",
      menuFull: "Full",
      badgeOffline: "Mode · Offline",
      badgeLimited: "Mode · Limited",
      badgeFull: "Mode · Full",
      badgeAria: "Select user mode",
      badgeTitle: "Change mode (Offline, Limited, Full)",
      menuAria: "Mode selection",
      segLegend: "Mode selection",
      segOffline: "Offline",
      segLimited: "Limited",
      segFull: "Full",
    },
  },
};

export default panel;
