/** Panel shell + module copy — Turkish (from panel.astro sections) */
const panelNav = {
  meta: {
    title: "Lumos Panel — Çalışma alanı",
  },
  header: {
    title: "Lumos Panel",
  },
  nav: {
    aria: "Çalışma modülleri",
    lumos: "Lumos",
    panel: "panel",
    calisma: "Çalışma",
    sohbet: "Sohbet",
    gorevler: "Görevler",
    ses: "Ses",
    medya: "Medya",
    sosyal: "Sosyal",
    posta: "Posta",
    dosyalar: "Dosyalar",
    kuantum: "Kuantum",
    lumosCore: "Lumos çekirdeği",
    yayincilik: "Yayıncılık",
    yapayzeka: "Yapay Zekâ",
    entegrasyon: "Entegrasyon",
    kimlik: "Kimlik",
    yetenekler: "Yetenekler",
    guvenlik: "Güvenlik",
    dunya: "Dünya",
    ayarlar: "Ayarlar",
  },
  sections: {
    sohbet: "Sohbet",
    gorevler: "Görevler",
    ses: "Ses",
    medya: "Medya",
    sosyal: "Sosyal",
    posta: "Posta",
    dosyalar: "Dosyalar",
    kuantum: "Kuantum",
    yayincilik: "Yayıncılık",
    yapayzeka: "Yapay Zekâ",
    entegrasyon: "Entegrasyon",
    kimlik: "Kimlik",
    yetenekler: "Yetenekler",
    guvenlik: "Güvenlik",
    dunya: "Dünya",
    ayarlar: "Ayarlar",
  },
} as const;

const panelCommon = {
  badges: {
    externalService: "[Harici Servis]",
    demoNotConnected: "[Demo — bağlı değil]",
    local: "[Yerel]",
    unknown: "[Bilinmiyor]",
  },
  form: {
    target: "Hedef",
    targetPlatform: "Hedef platform",
    recipient: "Alıcı",
    contentSummary: "İçerik özeti",
    postDraft: "Gönderi taslağı",
    messageDraft: "Mesaj taslağı",
    attachmentCount: "Ek sayısı",
    showSummary: "Özeti göster",
    sendDemoDisabled: "Gönder (demo kapalı)",
    shareDemoDisabled: "Paylaş (demo kapalı)",
  },
  placeholders: {
    shareSummary: "Paylaşılacak özet…",
    shareText: "Paylaşılacak metin…",
    emailBody: "E-posta metni…",
    emailRecipient: "ornek@posta.com",
  },
  select: {
    externalSummary: "Dış özet / arşiv",
    localCopy: "Yerel kopya",
    generalFeed: "Genel akış",
    directMessage: "Doğrudan mesaj",
  },
  demo: {
    sendTitle: "Demo: gerçek gönderim bağlı değil",
    shareTitle: "Demo: gerçek paylaşım bağlı değil",
    idleHint: "Demo modu: gerçek gönderim bağlı değil; yalnızca önizleme.",
    reviewHint: "Özet görüntülendi (demo). Gönderim bu sürümde kapalı; bağlantı henüz yok.",
    approvedHint: "Özet onaylandı. Göndermek için butona basın.",
    summaryFooter: "[Demo] Gerçek gönderim yapılmaz.",
    summaryTarget: "Hedef: ",
    summaryContentPreview: "İçerik önizleme: ",
    summaryAttachmentCount: "Ek sayısı: ",
    summaryDataType: "Veri türü: ",
    medyaMsg: "Demo: medya paylaşımı henüz bağlı değil.",
    sosyalMsg: "Demo: sosyal paylaşım henüz bağlı değil.",
    postaMsg: "Demo: e-posta gönderimi henüz bağlı değil.",
    defaultMsg: "Demo: gerçek gönderim henüz bağlı değil.",
  },
} as const;

const panelModules = {
  chat: {
    historyAria: "Mesaj geçmişi",
    empty: {
      default: "Lumos hazır · Dinliyor",
      limited: "Sınırlı mod · Yerel işlemler kullanılabilir",
      limitedUser: "Sınırlı mod · Kullanıcı seçimi",
      limitedSub: "Yerel görevler kullanılabilir; dış köprü gerektiren işlemler beklemede.",
      limitedUserSub: "Yerel görevler kullanılabilir; bu modda dış sohbet köprüsü denenmez.",
      offline: "Çevrimdışı mod · İnternet kullanılmaz",
      offlineSub: "Yerel işlemler kullanılabilir; dış bağlantı bu modda denenmez.",
    },
    modeHints: {
      sendLimited: "Sınırlı mod: dış sohbet köprüsü yok; yerel yanıtlar ve görev komutları kullanılabilir.",
      sendLimitedUser:
        "Sınırlı moddasın (kullanıcı seçimi); yerel yanıtlar ve görev komutları kullanılabilir.",
      sendOffline: "Çevrimdışı mod: internet ve dış köprü kullanılmaz; yerel yanıtlar kullanılabilir.",
    },
    capability: {
      title: "Şu an ne yapabilirim?",
      canDoSection: "Yapabilirim",
      canDo1: "Görev kaydeder, listeler ve kısa plan önerir.",
      canDo2: "Cihaz içi ayarlardan okur; pratik notlar verir.",
      wontDoSection: "Şu an yapmam",
      wontDo1: "Komut çalıştırmaz, kod değiştirmez.",
      wontDo2: "Onaysız kalıcı işlem yapmaz.",
    },
    security: {
      approval: "Kalıcı işlemler için onay ister.",
      secret: "Cihaz içinde çalışır; gizli bilgileri sohbete yazma.",
      debugBridge: "Yerel köprü bağlı. Ses ve görev işlemleri bu cihaz üzerinden yürütülür.",
      devicePerms: "Kamera ve mikrofon cihaz iznine bağlıdır.",
    },
    bubbles: {
      user: "Sen",
      lumos: "Lumos",
      warning: "Uyarı",
      actionsAria: "Yanıt işlemleri",
    },
    compose: {
      placeholder: "Mesajını yaz",
      send: "Gönder",
      sendLoading: "Gönderiliyor…",
      attachTitle: "Ekle",
      attachAria: "Dosya veya medya ekle",
      attachFile: "Dosya yükle",
      attachPhoto: "Fotoğraf seç",
      attachCamera: "Kamera aç",
      attachClipboard: "Panodaki metni ilet",
      attachAudio: "Ses dosyası yükle",
      attachRecord: "Ses kaydı",
      attachRecordTitle: "Mikrofonla ses kaydet; metne çevirmez (Sesle yaz düğmesinden farklı)",
      cameraTitle: "Kamera / görsel giriş",
      cameraAria: "Kamera / görsel giriş",
      voiceTitleSupported: "Sesle yaz (metne çevir) — tarayıcı ses tanıma servisine bağlı",
      voiceAriaSupported: "Sesle yaz, metne çevir; tarayıcı ses tanıma servisine bağlı",
      voiceTitleUnsupported: "Sesle yazma desteklenmiyor",
      voiceAriaUnsupported: "Bu tarayıcıda sesle yazma desteklenmiyor",
      galleryAria: "Galeriden görsel seç",
      audioFileAria: "Ses dosyası seç",
      audioPreviewAria: "Ses kaydı önizlemesi",
      stopRecord: "Durdur",
      cancelRecord: "İptal",
      rerecord: "Yeniden kaydet",
      transcribe: "Metne çevir",
      photoSelectedLabel: "Seçilen görsel",
      photoCapturedStatus: "Fotoğraf alındı",
      photoAdded: "Fotoğraf eklendi",
      clipboardConfirm: "Onayla ve gönder",
      clipboardConfirmAria: "Panodaki metni onayla ve gönder",
      clipboardConfirmTitle: "Onayla ve panodaki metni gönder",
      audioFileAttached: "Ses dosyası eklendi",
      audioRecordAttached: "Ses kaydı eklendi",
      audioRecordAria: "Ses kaydı",
      hints: {
        pickOneAttachment: "Önce tek ek seçin",
        photoReadFailed: "Fotoğraf okunamadı.",
        audioOnly: "Yalnızca ses dosyası seçin.",
        audioReadFailed: "Ses dosyası okunamadı.",
        photoOffline: "Çevrimdışı modda görsel analizi kullanılamaz.",
        photoLimitedUser: "Sınırlı moddasın (kullanıcı seçimi); görsel analizi denenmez.",
        photoLimited: "Sınırlı modda görsel analizi kullanılamaz.",
        audioOffline: "Çevrimdışı modda ses yalnızca yerel sohbette görünür.",
        audioLimitedUser: "Sınırlı moddasın (kullanıcı seçimi); ses dış sohbete iletilmez.",
        audioLimited: "Sınırlı modda ses yalnızca yerel sohbette görünür.",
        limitedPhotoReply:
          "Sınırlı modda fotoğraf analizi yapılamaz; dış görsel API köprüsü bağlı değil.",
        offlinePhotoReply:
          "Çevrimdışı modda fotoğraf analizi yapılamaz; internet erişimi kapalı.",
        limitedAudioReply:
          "Sınırlı modda ses kaydı yalnızca bu cihazda görünür; dış sohbete iletilmez.",
        offlineAudioReply:
          "Çevrimdışı modda ses kaydı yalnızca bu cihazda görünür; dış sohbete iletilmez.",
        fullAudioReply:
          "Tam modda ses kaydı yalnızca bu cihazda görünür; dış köprüye iletilmez.",
        fullAudioHint:
          "Tam modda ses kaydı dış köprüye iletilmez; metin ekleyin veya «Ses metne çevir» kullanın.",
        responseUnreadable: "Yanıt okunamadı.",
        sentOk: "Metin iletildi.",
        clipboardUnsupported: "Panodan okuma bu tarayıcıda desteklenmiyor.",
        clipboardDenied:
          "Pano erişimi reddedildi. Tarayıcı iznini veya sayfa odakını kontrol edin.",
        clipboardReadFailedPrefix: "Panodan okunamadı: ",
        clipboardEmpty: "Pano boş görünüyor.",
        clipboardReadFailed: "Panodan okunamadı.",
        clipboardReadyWithSnippet:
          'Panodaki metin hazır: "{snippet}" Göndermek için tekrar bas.',
        clipboardReadyEmpty: 'Panodaki metin hazır: "" Göndermek için tekrar bas.',
        httpSendFailedDebugPrefix: "Gönderilemedi (HTTP ",
        httpSendFailedDebugSuffix: "). Tekrar dene.",
        requestErrorDebugPrefix: "İstek hatası: ",
        emptyReply:
          "Bu turda net bir yanıt üretemedim; biraz sonra tekrar deneyeceğim.",
        responseUnusableBubble:
          "Sunucudan gelen yanıtı işleyemedik. Biraz sonra yeniden deneyebilirsin.",
        gorevServerReplyPrefix: "Sunucu yanıtı:\n",
        gorevNoExtraServerText:
          "Sunucu bu istek için ek metin dönmedi (görev zaten yerelde kayıtlı).",
        photoNoVision: "Fotoğraf eklendi; görsel analiz henüz aktif değil.",
      },
      cameraHints: {
        unsupported: "Bu tarayıcıda kamera girişi desteklenmiyor.",
        permissionDenied: "Kamera izni verilmedi.",
        pickImageFile: "Lütfen bir görsel dosyası seçin.",
        previewFailed: "Önizleme oluşturulamadı.",
        captureUnsupported: "Bu tarayıcıda kamera desteklenmiyor.",
        photoPickUnsupported: "Bu tarayıcıda görsel seçimi desteklenmiyor.",
        fileUploadPreparing: "Dosya yükleme bu görünümde hazırlanıyor.",
      },
      record: {
        previewLabel: "Ses kaydı hazır — Gönder ile sohbete ekle",
        unsupported: "Bu tarayıcıda ses kaydı desteklenmiyor.",
        recordingHint: "Ses kaydı yapılıyor (metne çevrilmez) — bitince Gönder ile ekleyin",
        recordingStatus: "Ses kaydı yapılıyor…",
        tooShort: "Kayıt çok kısa veya boş; tekrar deneyin.",
        stopFailed: "Kayıt durdurulamadı.",
        startFailed: "Bu tarayıcıda ses kaydı başlatılamadı.",
        errorDuring: "Kayıt sırasında hata oluştu.",
        micDenied: "Mikrofon izni verilmedi.",
        micUnavailable: "Mikrofon kullanılamıyor.",
      },
      voiceHints: {
        serviceUnavailable: "Tarayıcı ses tanıma servisi şu anda kullanılamıyor",
        unsupported: "Bu tarayıcıda sesle yazma desteklenmiyor.",
        noSpeech: "Konuşma algılanmadı.",
        micUnavailable: "Mikrofon kullanılamıyor.",
        micDenied: "Mikrofon izni verilmedi.",
        aborted: "Sesli giriş iptal edildi.",
        failed: "Sesli giriş başarısız oldu.",
        startFailed: "Ses tanıma başlatılamadı. Tekrar deneyin.",
        noResult:
          "Ses algılanmadı veya tarayıcı konuşma sonucu üretmedi. Tekrar deneyin.",
      },
    },
    tts: {
      speak: "Sesli oku",
      stopSpeaking: "Sesli okumayı durdur",
      stop: "Durdur",
      stopped: "Durduruldu",
      failed: "Sesli okuma başarısız",
      error: "Hata",
      unsupported: "Desteklenmiyor",
      unsupportedFeature: "Sesli okuma desteklenmiyor",
      empty: "Boş",
    },
    gorev: {
      confirmMini: "Mini görev eklendi: {title}",
      confirmWithWhen: "Görev eklendi: {title} — {when}",
      confirm: "Görev eklendi: {title}",
      deleteUnavailable: "Görev silme şu an kullanılamıyor (liste bağlanmadı).",
      restoreUnavailable: "Görev geri alma şu an kullanılamıyor (liste bağlanmadı).",
      deleteRestoreHint:
        ' Geri almak için «görev geri al» yazabilir veya Görevler\'de «Son silineni geri al» kullan.',
      notFound:
        'Görev bulunamadı: «{ref}». Başlık veya görev kimliği (tsk_…) kontrol edin.',
      deleted: 'Görev silindi: "{title}".',
      deleteMissingRef: "Görev adı eksik. Örnek: görev sil alışveriş",
      deleteConfirm: '"{ref}" silinsin mi?',
      deleteCancelled: "Silme iptal edildi.",
      deleteFailed: "Silinemedi ({error}).",
      restoreNothing: "Geri alınacak silinen görev yok.",
      restoreVerifyFailed: "Görev listesine eklenemedi; geri alma doğrulanamadı.",
      restored: 'Görev geri alındı: "{title}".',
    },
    localReply: {
      emptyMessage: "Bir mesaj yazın.",
      navGorevler:
        "Görevler ekranına geçtim; listeden görevleri görebilir veya «görev oluştur başlık» ile yeni görev ekleyebilirsin.",
      navAyarlar:
        "Ayarlar ekranına geçtim. Bağlantı köprüsü olmadan dış sohbet devre dışı; yerel görevler kullanılabilir.",
      navKimlik:
        "Kimlik ekranına geçtim; bağlantı ve kimlik ayarlarını buradan görebilirsin.",
      navAyarlarOffline:
        "Ayarlar ekranına geçtim. Çevrimdışı mod; yerel görevler kullanılabilir.",
      keywordGorev:
        "Görevler ekranından listeyi görebilirsin. Yeni görev için: «görev oluştur başlık» (ör. görev oluştur alışveriş).",
      keywordKayit: "Medya ekranına geçip dosyaları inceleyebilirsin.",
      keywordAkis: "Sosyal ekranına geçip güncel listeyi görebilirsin.",
      limitedDefault:
        "Sınırlı moddasın (kullanıcı seçimi); yerel görevler ve kısa yönlendirmeler kullanılabilir — örn. «görev oluştur başlık» veya «görevler».",
      offlineDefault:
        "Çevrimdışı moddasın; internet kullanılmaz. Yerel görevler kullanılabilir — örn. «görev oluştur başlık» veya «görevler».",
      timeBase: "Saat {hh}:{mm}. Bugün {date}.",
      timeWeekdaySuffix: " Günlerden {weekday}.",
      weekday0: "Pazar",
      weekday1: "Pazartesi",
      weekday2: "Salı",
      weekday3: "Çarşamba",
      weekday4: "Perşembe",
      weekday5: "Cuma",
      weekday6: "Cumartesi",
    },
    bridgeBadgeLimited: "Sınırlı mod",
    transcript: {
      engineMsg: "Ses metne çeviri motoru henüz bağlı değil.",
      limitedMsg: "Sınırlı modda ses metne çeviri kullanılamaz; dış köprü bağlı değil.",
      limitedUserMsg:
        "Sınırlı moddasın (kullanıcı seçimi); ses metne çeviri bu modda denenmez.",
      offlineMsg: "Çevrimdışı modda ses metne çeviri kullanılamaz; internet erişimi kapalı.",
      busyMsg: "Metne çevriliyor…",
      privacyMsg:
        "Metin yalnızca önizleme; «Sohbete ekle» ile yazma alanına kopyalanır, otomatik gönderilmez.",
      musicWarnMsg:
        "Bu ses müzik/şarkı içeriyor olabilir. Metne çeviri sonucu güvenilir olmayabilir.",
      failedMusic:
        "Metne çeviri tamamlanamadı. Ses müzik, gürültülü veya konuşma dışı olabilir.",
      failedSpeech: "Metne çeviri tamamlanamadı.",
      lowQualityWarnMsg:
        "Metin düşük güvenilirlikte olabilir; daha net bir konuşma kaydıyla tekrar deneyin.",
      missingAudio: "Ses verisi yok veya çok kısa.",
      networkFailed: "Metne çeviri tamamlanamadı. Bağlantıyı kontrol edip tekrar deneyin.",
      addToChat: "Sohbete ekle",
      transcribing: "Çevriliyor…",
      previewAria: "Transkript önizlemesi",
    },
    errors: {
      network_error: "İletim tamamlanamadı. Bağlantıyı kontrol edip tekrar dene.",
      timeout: "Yanıt süresi doldu. Biraz sonra tekrar dene.",
      unauthorized: "Bağlantı doğrulanamadı. Cihaz ayarlarını kontrol edip tekrar dene.",
      server_error: "Sohbet geçici olarak yanıt veremedi. Biraz sonra tekrar dene.",
      model_error: "Yanıt üretilemedi. Biraz sonra tekrar dene.",
      unknown_error: "Beklenmeyen bir sorun oluştu. Biraz sonra tekrar dene.",
    },
  },
  tasks: {
    eyebrow: "Operasyon",
    intro:
      "Görevler cihazınızdaki görev kaydına yazılır; görev eklerken iletim gerekmez. Sunucu kapalıysa liste tarayıcı önbelleğinden gösterilir.",
    form: {
      titleLabel: "Görev adı",
      titlePlaceholder: "Kısa bir başlık yazın…",
      priorityLabel: "Öncelik",
      statusLabel: "Durum",
      addBtn: "Görev ekle",
    },
    priority: {
      dusuk: "Düşük",
      orta: "Orta",
      yuksek: "Yüksek",
    },
    status: {
      bekliyor: "Bekliyor",
      onay_bekliyor: "Onay bekliyor",
      tamamlandi: "Tamamlandı",
    },
    list: {
      heading: "Görev listesi",
      filterAria: "Görev durumu filtresi",
      filterAll: "Tümü",
      filterPending: "Bekleyen",
      filterDone: "Tamamlanan",
      clearLocal: "Yerel listeyi temizle",
      restore: "Geri al",
      syncBadge: "yalnızca bu cihaz / sunucu senkronu kapalı",
      syncBadgeTitle: "Görevler yalnızca bu cihazda tutulur; sunucu görev API'sine erişilemiyor.",
      listAria: "Görev listesi",
      metaStatus: "Durum",
      metaPriority: "Öncelik",
      cardAriaPrefix: "Görev",
      cardAriaSuffix: "ayrıntıları göster",
    },
    empty: {
      listDefault: "Henüz görev yok. Yukarıdan kısa bir başlık yazıp «Görev ekle» kullanın.",
      listFilter: "Bu filtrede görev yok. «Tümü» ile tüm görevleri görebilirsin.",
      evidence: "Henüz sunucu kanıtı yok",
    },
    detail: {
      title: "Görev",
      close: "Kapat",
      complete: "Tamamla",
      delete: "Sil",
      bridge: "Görevi ilet",
      bridgeNote: "Görev iletimi köprü bağlantısı bekliyor.",
      secTask: "Görev",
      secPlan: "Görev planı",
      secBridge: "İletim yanıtı",
      planTitle: "Görev planı",
      planConfirm: "Planı onayla",
      planDismiss: "Sadece kaydet",
      lowRiskNote: "Düşük risk. Otomatik plan; hiçbir şey çalıştırılmadı.",
      evidenceAria: "Son işlem kanıtı",
      evidenceSummaryPrefix: "Son işlem kanıtı: ",
      evidenceContinue: "Buradan devam",
    },
    hints: {
      savedLocal: "Görev yerel olarak kaydedildi.",
      titleEmpty: "Görev adı boş olamaz.",
      saveFailed: "Görev kaydedilemedi ({error}).",
      createFailed: "kayıt başarısız",
      leakCompleteFailed: "kayıt tamamlanamadı",
      leakDeleteFailed: "silme başarısız",
      leakRestoreFailed: "geri alma başarısız",
      savedWithPlan: "Görev kaydedildi; plan gösteriliyor.",
      bridgeFailed: "İletim tamamlanamadı. Bağlantıyı kontrol edip tekrar dene.",
      bridgeSent: "Görev iletildi.",
      bridgeAccepted: "İşleme alındı.",
      completeFailed: "Tamamlanamadı ({error}).",
      deleted: "Görev silindi.",
      deleteFailed: "Silinemedi ({error}).",
      restoreFailed: "Geri alınamadı ({error}).",
      clearLocalDone: "Yerel liste temizlendi; sunucu kayıtlarına dokunulmadı.",
    },
    confirm: {
      deleteOpen: "Görev silinsin mi?",
      clearLocal:
        "Yerel görev listesi temizlensin mi? Sunucudaki görev kayıtlarına dokunulmaz.",
    },
  },
  files: {
    intro:
      "Dosyayı cihazınızdan seçin; Lumos köprüsü dosyayı alır, adı/türü/boyutu döner. Metin dosyalarında (.txt, .md, .json, .csv) kısa özet üretilir. PDF ve Word (DOCX) gibi biçimler bu fazda işlenmez.",
    historyHeading: "Son yüklemeler",
    historyDeviceNote: "Bu cihazda saklanır; en fazla 5 kayıt.",
    form: {
      pickLabel: "Dosya seç",
      uploadBtn: "Yükle ve analiz et",
    },
    hints: {
      attachNavigate: "Dosyayı seçin; ardından «Yükle ve analiz et».",
      pickFirst: "Önce bir dosya seçin.",
      readFailed: "Dosya metin olarak okunamadı.",
      unreachable: "Sunucuya ulaşılamadı. Bağlantı ayarlarını kontrol edin.",
      writeFailed: "Dosya yazılamadı",
      readFailedBridge: "Dosya okunamadı",
      sizeLimitPrefix: "Dosya boyutu kontrollü dosya yazma sınırını (",
      sizeLimitSuffix: " bayt) aşıyor.",
    },
    result: {
      metaTitle: "Dosya bilgisi",
      infoTitle: "Bilgi",
      alertTitle: "Uyarı",
      summaryTitle: "Kısa özet",
      transcriptTitle: "Metne çevir",
      metaFilename: "Dosya adı",
      metaSize: "Boyut",
      metaKind: "Tür",
      metaExt: "Uzantı",
    },
    history: {
      replayAriaPrefix: "Sonuçları yeniden göster: ",
      replayAria: "Sonuçları yeniden göster",
      statusAudio: "Ses — analiz yok",
      statusWarn: "Uyarı",
      statusSummaryDone: "Özet üretildi",
      statusSummaryReady: "Özet hazır",
      statusDone: "Tamamlandı",
    },
    messages: {
      unsupportedAudio:
        "Dosya başarıyla seçildi. Ses dosyaları Dosyalar sekmesinde bu fazda analiz edilmez.",
      unsupportedExe: "Dosya çalıştırılmaz; yalnızca dosya bilgisi kaydedilir.",
      unsupportedDoc: "PDF ve Word (DOCX) içeriği bu fazda işlenmez.",
      unsupportedGeneric: "Bu dosya türü bu fazda işlenmez.",
      infoSummary: "Bu dosya için özet üretildi.",
      infoPy: "Dosya metin dosyası gibi gösterilir; bu fazda kod çalıştırılmaz.",
      summaryJsonArray: "JSON dizi: {count} öğe.",
      summaryJsonObject: "JSON nesne: {count} anahtar.",
      summaryCsv: "CSV: yaklaşık {count} satır.",
      bytesSuffix: " bayt",
    },
  },
  voice: {
    intro:
      "Bu sekme, sesli girdinin metne ve komutlara dönüşürken arayüz katmanında kalması ve kararın yine kullanıcıda tutulması için tasarlanan yaklaşımı özetler. Sohbet alt çubuğundaki mikrofon, cihaz, tarayıcı ve verilen izinlere bağlıdır; bazı ortamlarda desteklenmeyebilir.",
    c1Title: "Sesten Metne",
    c1Body:
      "Sesli ifade, metin ve komut adımlarına aktarılarak ekranda izlenebilir hale getirilebilir.",
    c2Title: "Arayüz Katmanı",
    c2Body:
      "Ses, doğrudan yerine geçen bir otorite değil; kullanıcının gördüğü ve düzeltebildiği bir katman olarak ele alınır.",
    c3Title: "Karar Kullanıcıda",
    c3Body: "Özetlenen komut veya metin uygulanmadan önce kullanıcı net biçimde kontrol edebilmelidir.",
    c4Title: "Yanlış Anlama ve Onay",
    c4Body:
      "Belirsiz veya düşük güvenli algılarda Lumos duraklatmayı ve netleştirmeyi hedefler; tek başına ilerlemez.",
    c5Title: "Yerel İşlem Önceliği",
    c5Body:
      "Mümkün olduğunda ilk işlem cihaz içinde kalır; dış servise çıkış gerekiyorsa bu görünür tutulmalıdır.",
  },
  media: {
    intro:
      "Bu sekme, görsel, ses, video ve dosya akışlarının düzenlenmesinde paylaşım öncesi kontrol, veri yolu görünürlüğü ve kaynak ile çıktının ayrılması ilkelerini özetler. Sohbet alt çubuğundaki kamera da cihaz, tarayıcı ve izin desteğine bağlıdır; her ortamda çalışmayabilir.",
    outboxTitle: "Son çıktı özeti (salt okunur)",
    outboxIntro:
      "Son görev veya sohbet çıktısının iletimden okunan özeti. Kayıt yoksa kısa bilgi gösterilir.",
    outboxRefresh: "Yenile",
    outboxResultFailedWithSnippet: "Sonuç alınamadı: {snippet}",
    outboxResultNotFound: "Sonuç kaydı bulunamadı veya bağlantı doğrulanamadı.",
    outboxFetchFailed: "Sonuç alınamadı. Bağlantıyı kontrol edin.",
    sharePreviewIntro: "Paylaşım taslağı önizlemesi — gerçek gönderim bu sürümde kapalı.",
    dataType: "Medya özeti",
    c1Title: "Akışlar ve Türler",
    c1Body:
      "Farklı medya türleri tek çalışma düzeninde izlenebilir; hangi dosyanın nerede kullanıldığı daha okunaklı olabilir.",
    c2Title: "Paylaşım Öncesi Kontrol",
    c2Body: "Dışarıya çıkmadan önce içerik özeti ve hedef kullanım kullanıcıya gösterilmeyi hedefler.",
    c3Title: "Dış Servise Aktarım",
    c3Body:
      "Bir dosyanın veya önizlemenin harici işleme gönderildiği adımlar gizlenmez; bağlantı ve amaç daha net tutulur.",
    c4Title: "Düzenleme ve Dönüştürme",
    c4Body:
      "Kırpma, biçim değişimi veya dönüştürme gibi adımlar sıralı ve geri alınabilir bir akışta önerilir.",
    c5Title: "Kaynak ve Çıktı",
    c5Body:
      "Orijinal materyal ile üretilen çıktı birbirinden ayırt edilir; kullanıcı hangisinin paylaşıldığını net görebilir.",
  },
  social: {
    intro:
      "Bu sekme, dışa açılan içeriklerde taslağı kullanıcıda tutmayı, platform farkındalığını artırmayı ve kalıcı paylaşımlarda açık onayı öncelemeyi hedefleyen yaklaşımı özetler.",
    sharePreviewIntro: "Sosyal paylaşım taslağı önizlemesi — gerçek paylaşım bu sürümde kapalı.",
    dataType: "Sosyal metin",
    c1Title: "Paylaşım Öncesi Kontrol",
    c1Body:
      "Gönderi yayınlanmadan önce özet, hedef ve görünürlük kullanıcıya son kez gösterilmeyi hedefler.",
    c2Title: "Hedef Platform",
    c2Body:
      "İçeriğin hangi ortamda nasıl görüneceği ve hangi kurallara tabi olduğu daha görünür tutulabilir.",
    c3Title: "Gönderi Taslağı",
    c3Body: "Metin ve ekler taslak halinde saklanır; kullanıcı düzenlemeden yayına çıkmaz.",
    c4Title: "Riskli Paylaşımda Onay",
    c4Body:
      "Kalıcı, geniş kitleye açık veya geri alınması zor paylaşımlarda ek onay istenmesi hedeflenir.",
    c5Title: "Otomatik Yayın Yok",
    c5Body: "Lumos kullanıcı adına sessizce paylaşım yapmaz; gönderme kararı kullanıcıda kalır.",
  },
  mail: {
    intro:
      "Bu sekme, e-posta taslağı hazırlama, ek ve alıcı doğrulaması ile gönderim öncesi açık onayı merkeze alan yaklaşımı özetler.",
    sharePreviewIntro: "E-posta taslağı önizlemesi — gerçek gönderim bu sürümde kapalı.",
    dataType: "E-posta",
    c1Title: "Taslak Odaklı Çalışma",
    c1Body:
      "Mesajlar önce taslak olarak düzenlenir; kullanıcı içeriği gözden geçirmeden iletim beklenmez.",
    c2Title: "Ek ve Alıcı Kontrolü",
    c2Body: "Eklerin listesi ve alıcı alanları gönderim öncesi okunaklı biçimde özetlenmeyi hedefler.",
    c3Title: "Gönderim Öncesi Onay",
    c3Body:
      "\u201cGönder\u201d adımı bilinçli bir onay gerektirir; tek tıkla görünmez iletim hedeflenmez.",
    c4Title: "Yanlış Alıcı ve Hassas Bilgi",
    c4Body: "Şüpheli alıcı eşleşmeleri veya hassas içerik için uyarı gösterilmesi amaçlanır.",
    c5Title: "Otomatik Gönderim Yok",
    c5Body:
      "Lumos kullanıcı yerine postayı tek başına iletmez; son gönderme kararı kullanıcıdadır.",
  },
  publishing: {
    intro:
      "Bu sekme, canlı veya kayıtlı yayın akışlarında hangi içeriğin hangi kanala gittiğinin görünür olması; yayına alma öncesi kontrol ve kayıt paylaşımında onayı önceleyen yaklaşımı özetler.",
    c1Title: "Canlı ve Kayıtlı Akış",
    c1Body:
      "Yayının canlı mı yoksa kayıt tabanlı mı olduğu ve izleyici bağlamı kullanıcıya net gösterilmeyi hedefler.",
    c2Title: "İçerik ve Kanal Eşlemesi",
    c2Body:
      "Hangi görüntü veya sesin hangi çıkışa gittiği düzenli bir özetle izlenebilir hale getirilebilir.",
    c3Title: "Yayına Alma Öncesi Kontrol",
    c3Body: "Yayına çıkmadan önce önizleme ve son uyarı adımları atlanmamalıdır.",
    c4Title: "Kayıt ve Paylaşım Onayı",
    c4Body:
      "Oturum kaydı veya klibin dışarı paylaşılması ayrı onay gerektiren işlemler olarak ele alınır.",
    c5Title: "Yayın Riskleri",
    c5Body:
      "Görünürlük, telif ve özel hayat gibi riskler kısa ve anlaşılır biçimde hatırlatılmayı hedefler; kesin hukuki sonuç vaadi verilmez.",
  },
  ai: {
    intro:
      "Bu sekme, Lumos’un yapay zekâyı kullanıcı adına karar veren bir otorite olarak değil; bağlamı toparlayan, seçenekleri düzenleyen ve karar sürecini daha görünür hale getiren bir yardımcı katman olarak ele alma yaklaşımını özetler.",
    c1Title: "Bağlamı Toplama",
    c1Body:
      "Lumos, kullanıcının isteğini, mevcut çalışma alanını ve ilgili bilgileri birlikte değerlendirerek daha anlaşılır bir görev bağlamı oluşturmayı hedefler.",
    c2Title: "Öneri ve Seçenekler",
    c2Body:
      "Yapay zekâ tek bir sonucu kesin doğru gibi dayatmaz; mümkün olan seçenekleri, belirsizlikleri ve dikkat edilmesi gereken noktaları görünür kılar.",
    c3Title: "Karar Kullanıcıda",
    c3Body:
      "Lumos öneri sunabilir, yolu kısaltabilir ve karmaşayı azaltabilir; ancak nihai karar kullanıcının iradesinde kalmalıdır.",
    c4Title: "Riskli İşlem Duraklatma",
    c4Body:
      "Kalıcı, maliyetli veya geri dönüşü zor işlemlerde yapay zekâ otomatik ilerlemek yerine kullanıcıyı bilgilendirmeli ve açık onay beklemelidir.",
    c5Title: "Belirsizlik Bildirimi",
    c5Body:
      "Eksik veri, düşük güven veya çelişkili bilgi varsa Lumos bunu saklamaz; hangi noktada emin olmadığını kullanıcıya açıkça göstermeyi hedefler.",
    c6Title: "Yapay Zekâ Sınırı",
    c6Body:
      "Lumos yapay zekânın her şeyi doğru bileceğini iddia etmez. Amaç, kullanıcıyı devre dışı bırakmak değil; daha bilinçli ve kontrollü hareket etmesine yardımcı olmaktır.",
  },
  quantum: {
    intro:
      "Bu sekmede olasılık, belirsizlik ve güvenlik araştırması birlikte ele alınır; kesin vaatler yerine şeffaf sınırlar önceliklidir.",
    c1Title: "Kuantum Güvenlik Araştırması",
    c1Body:
      "Bu bölüm, Lumos’un gelecekte kuantum dayanıklı şifreleme ve ileri güvenlik yaklaşımlarını değerlendireceği araştırma alanıdır. Mevcut sistem, kuantum şifreleme kullandığını iddia etmez.",
    c2Title: "Çoklu İhtimal",
    c2Body:
      "Lumos tek bir sonucu kesinmiş gibi dayatmaz; olası yolları ve belirsizlikleri birlikte görünür tutar.",
    c3Title: "Belirsizlik Dengesi",
    c3Body: "Veri eksik olduğunda Lumos boşluk doldurmaz; neyin bilindiğini ve neyin bilinmediğini ayırır.",
    c4Title: "Karar Sınırı",
    c4Body:
      "Kuantum yaklaşımı kararın yerine geçmez; seçenekleri düzenler, son yönü kullanıcı iradesine bırakır.",
  },
  integration: {
    intro:
      "Bu sekme, Lumos’un yerel araçlar, harici servisler, API bağlantıları ve uygulamalar arasında kontrollü bir köprü kurma yaklaşımını özetler. Amaç her şeyi sınırsız bağlamak değil; bağlantı kapsamını, veri akışını ve kullanıcı onayını görünür tutmaktır.",
    c1Title: "Servis Bağlantıları",
    c1Body:
      "Lumos, farklı servis ve uygulamaların tek bir akışta daha düzenli çalışmasını hedefler. Her bağlantının ne için kullanıldığı ve hangi işlemi etkilediği açık olmalıdır.",
    c2Title: "API Köprüsü",
    c2Body:
      "API entegrasyonları, Lumos’un dış sistemlerle kontrollü biçimde iletişim kurmasını sağlar. Bu bağlantılar sınırsız yetki değil, belirlenmiş kapsam ve açık amaç üzerinden düşünülür.",
    c3Title: "Yerel ve Dış Servis Ayrımı",
    c3Body:
      "Lumos, cihaz içinde kalan işlemlerle dış servise aktarılan işlemleri birbirinden ayırmayı hedefler. Kullanıcı hangi adımın yerel, hangi adımın harici olduğunu daha net görebilmelidir.",
    c4Title: "Kapsam ve Onay",
    c4Body:
      "Bir bağlantı kullanılmadan önce neye erişeceği, hangi işlemde devreye gireceği ve kullanıcıdan hangi onayın gerektiği açık tutulmalıdır.",
    c5Title: "Veri Akışı Görünürlüğü",
    c5Body:
      "Dosya, metin, medya veya görev bilgisinin hangi servisle paylaşıldığı ve hangi adımda işlendiği daha izlenebilir hale getirilir.",
    c6Title: "Sınırsız Yetki Yok",
    c6Body:
      "Lumos entegrasyonları otomatik ve sınırsız yetki anlamına gelmez. Her bağlantı, kullanıcı kontrolü ve güvenlik sınırları içinde çalışacak şekilde tasarlanmalıdır.",
  },
  identity: {
    intro:
      "Bu sekme, Lumos’un kullanıcıya bağlı dijital AI kimlik yaklaşımını özetler. Amaç, kullanıcının yerine geçen bir kimlik oluşturmak değil; kullanıcının tercihlerini, sınırlarını, yetkilerini ve temsil edildiği bağlamı daha görünür ve yönetilebilir hale getirmektir.",
    c1Title: "Dijital AI Kimlik",
    c1Body:
      "Lumos, kullanıcının çalışma biçimi, tercihleri ve sınırlarıyla ilişkilenen dijital AI kimlik fikrini temel alan bir yapı olarak tasarlanır. Bu kimlik, kullanıcının yerine geçmez; kullanıcının dijital işlemlerde nasıl temsil edildiğini daha anlaşılır hale getirir.",
    c2Title: "Temsil Sınırı",
    c2Body:
      "Lumos’un amacı kullanıcı adına sınırsız hareket etmek değildir. Hangi işlemde, hangi bağlamda ve hangi yetkiyle hareket edildiğinin daha açık görülmesini hedefler.",
    c3Title: "Oturum ve Servis Bağlantıları",
    c3Body:
      "Kullanıcının bağlı olduğu servisler, oturumlar ve çalışma alanları daha düzenli bir çerçevede izlenebilir hale getirilebilir. Böylece hangi bağlantının hangi işlem için kullanıldığı daha kolay anlaşılır.",
    c4Title: "İzin Görünürlüğü",
    c4Body:
      "Uygulama, dosya veya servis bağlantılarında verilen izinlerin neye yol açabileceği kullanıcıya daha açık gösterilir. Amaç, onayın bilinçli verilmesini sağlamaktır.",
    c5Title: "Tercih ve Hafıza Sınırları",
    c5Body:
      "Lumos, kullanıcının tercihlerini ve çalışma alışkanlıklarını dikkate alabilir; ancak bu bilgilerin nasıl kullanılacağı, hangi sınırlar içinde tutulacağı ve ne zaman devreye gireceği açık olmalıdır.",
    c6Title: "Kimlik Güvenliği Sınırı",
    c6Body:
      "Lumos kimlik güvenliğini mutlak şekilde garanti etmez. Bunun yerine oturum, izin, temsil ve tercih bilgisini daha izlenebilir hale getirmeyi hedefler.",
  },
  security: {
    c1Title: "Açık Onay",
    c1Body: "Riskli, kalıcı veya geri dönüşü zor işlemlerde Lumos son kararı kullanıcıya bırakır.",
    c2Title: "Risk Görünürlüğü",
    c2Body:
      "Lumos, işlem başlamadan önce olası sonucu, kapsamı ve dikkat edilmesi gereken noktaları görünür kılmayı hedefler.",
    c3Title: "Veri Yolu Farkındalığı",
    c3Body:
      "Verinin cihazda mı kaldığı, dış servise mi aktarıldığı ve hangi adımda işlendiği daha anlaşılır hale getirilir.",
    c4Title: "Güvenlik Sınırı",
    c4Body:
      "Lumos mutlak güvenlik vaadi vermez; kullanıcıya daha kontrollü, izlenebilir ve bilinçli bir işlem alanı sunmayı hedefler.",
  },
  world: {
    intro:
      "Bu sekme, Lumos’un farklı dillere, bölgelere ve erişilebilirlik ihtiyaçlarına daha duyarlı; tek bir kültüre kapanmayan ve ölçülü bir küresel kullanım tasarımını özetler.",
    c1Title: "Dil, Bölge ve Erişilebilirlik",
    c1Body:
      "Arayüz ve içerik sunumunda dil seçimi, yerel biçimler ve erişilebilirlik seçenekleri daha görünür tutulmayı hedefler.",
    c2Title: "Kullanım Biçimlerine Uyum",
    c2Body:
      "Farklı cihaz, bağlantı ve çalışma ortamlarında deneyimin aşırıya kaçmadan uyarlanması amaçlanır.",
    c3Title: "Yerelleştirme",
    c3Body:
      "Metin ve tarih gibi öğeler yerel normlara göre düzenlenebilir; çeviri ve bağlam hatalarında şeffaflık korunur.",
    c4Title: "Küresel ve Çoğul Yaklaşım",
    c4Body:
      "Tek bir merkezin bakış açısına kilitlenmeden, çeşitli kullanıcıların ihtiyaçlarına saygılı bir çerçeve hedeflenir.",
    c5Title: "İnsan Odaklı Teknoloji",
    c5Body:
      "Lumos, teknolojiyi insanın yerine koymak yerine; karar ve mahremiyet sınırını kullanıcıda tutmayı önceleyen bir çizgiyi benimsemeyi hedefler.",
  },
  settings: {
    intro:
      "Bu sekme, kullanıcı tercihlerinin, bağlantı ve izin sınırlarının ve varsayılan davranışların kullanıcı kontrolünde ve görünür kalması için tasarlanan yaklaşımı özetler.",
    c1Title: "Kullanıcı modu",
    c1Body:
      "Panelin çalışma kapsamını siz seçersiniz. Bu tercih altyapı bağlantı durumundan ayrıdır; köprü rozeti yalnızca teknik durumu gösterir.",
    c2Title: "Altyapı durumu",
    c2Body:
      "Köprü, anahtar, sağlık ve ağ durumu — kullanıcı modundan bağımsız teknik özet.",
    c3Title: "Kullanıcı Tercihleri",
    c3Body: "Dil, tema, bildirim yoğunluğu gibi seçenekler anlaşılır gruplarda sunulmayı hedefler.",
    c4Title: "Sınırlar ve İzinler",
    c4Body:
      "Hangi özelliğin hangi izne bağlı olduğu kısa özetlerle gösterilir; kapalı tutulan izinler sessizce açılmaz.",
    c5Title: "Bağlantı Ayarları",
    c5Body:
      "Harici servis ve hesap bağlantıları tek yerden görülebilir; gerektiğinde kesme ve yeniden bağlanma kullanıcıdadır.",
    c6Title: "Görünürlük ve Güvenlik Tercihleri",
    c6Body:
      "Paylaşım, günlük veya veri saklama ile ilgili seçenekler birbirinden ayrılır; her biri net bir açıklamayla sunulur.",
    c7Title: "Varsayılanlar ve Kontrol",
    c7Body:
      "Öntanımlı davranışlar kabul edilmeden önce kullanıcıya gösterilir; değişiklikler geri alınabilir biçimde tutulmayı hedefler.",
    corsMsg: "Bu bilgi panelden okunamıyor (CORS).",
    infraSummaryAria: "Altyapı durumu özeti",
    connectionLine: "Bağlantı: {line}",
    healthWithConnection: "{health} · bağlantı: {line}",
    visionConfiguredYes: "Evet (görsel analiz için anahtar tanımlı)",
    visionConfiguredNo: "Hayır",
    chatPingReady: "Sohbet bağlantısı hazır",
    chatPingNoResponse: "Sohbet bağlantısı yanıt vermedi",
    chatPingUnreadable: "Sohbet bağlantısı okunamadı",
    chatWithPing: "{chat} · {ping}",
  },
  capabilities: {
    intro:
      "Lumos’un hangi işlemlere hangi bağlantı veya panel yüzeyi üzerinden bağlandığını özetler. «Bağlantı testi» yalnızca 1–3. satırlarda bağlantıyı doğrular; 4. satır yerel kanıtını kontrol eder.",
    legendAria: "Durum sözlüğü",
    legendActive: "AKTİF kanıtı var veya kısıtlı çalışır",
    legendPassive: "PASİF şu an çalışır hat yok",
    legendDev: "GELİŞTİRME AŞAMASINDA hedefleniyor, henüz bağlı değil",
    testBtn: "Bağlantı testi",
    testRunning: "Test çalışıyor…",
    testBridgeUnavailable: "Köprü şu an kullanılamıyor.",
    testDone: "Bağlantı testi tamamlandı.",
    testPartialFailed: "Bağlantı testi kısmen başarısız. Cihaz ayarlarını kontrol edin.",
    bridgePending: "Köprü bağlantısı bekleniyor.",
    routeTerminal: "Yerel cihaz köprüsü bekleniyor.",
    routeNone: "—",
    routeManualApproval: "manuel onay sonrası",
    row1: "1. Dosya okuma",
    row2: "2. Dosya yazma",
    row3: "3. Görev oluşturma",
    row4: "4. Görev tamamlama",
    row5: "5. Terminal komutu",
    row6: "6. Mac uygulaması açma",
    row7: "7. Canlı deploy",
    status: {
      active: "AKTİF",
      passive: "PASİF",
      limited: "KISITLI",
      dev: "GELİŞTİRME AŞAMASINDA",
    },
  },
} as const;

const panelShell = {
  conn: {
    pending: "Bağlanıyor",
    ok: "Bağlı",
    bad: "Çevrimdışı",
    limited: "Sınırlı mod",
    ariaLabel: "Altyapı bağlantı durumu",
    title: "Altyapı: köprü bağlantısı",
  },
  infra: {
    tokenMissing: "Yapılandırılmamış",
    tokenPresent: "Tanımlı",
    online: "Çevrimiçi",
    offline: "Çevrimdışı",
    labelBridge: "Köprü",
    labelToken: "Anahtar",
    labelHealth: "Sağlık",
    labelInternet: "İnternet",
    unavailableShort: "Köprü erişilemiyor (altyapı)",
    unavailableMsg:
      "Köprü erişilemiyor (altyapı). Bağlantıyı kontrol edip tekrar deneyin.",
    bridgeTokenMsg:
      "Panel bağlantısı yapılandırılmamış. Köprü ve pano işlemleri bu ortamda devre dışı; cihaz yöneticinizden bağlantı anahtarını tanımlamasını isteyin.",
    healthPending: "bekleniyor…",
    healthTrying: "deneniyor…",
    healthOk: "OK",
    healthUnreachable: "erişilemedi",
  },
  userMode: {
    menuOffline: "Offline",
    menuLimited: "Sınırlı",
    menuFull: "Tam",
    badgeOffline: "Mod · Çevrimdışı",
    badgeLimited: "Mod · Sınırlı",
    badgeFull: "Mod · Tam",
    badgeAria: "Kullanıcı modu seç",
    badgeTitle: "Mod değiştir (Offline, Sınırlı, Tam)",
    menuAria: "Mod seçimi",
    segLegend: "Mod seçimi",
    segOffline: "Çevrimdışı",
    segLimited: "Sınırlı",
    segFull: "Tam",
  },
} as const;

const panel = {
  ...panelNav,
  common: panelCommon,
  shell: panelShell,
  modules: panelModules,
};

export default panel;
export type PanelMessages = typeof panel;
