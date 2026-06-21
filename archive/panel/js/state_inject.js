// Read-only bridge state (set by panel/scripts/read_backend_state.py --write)
window.__LUMOS_READ_STATE__ = {
  "dashboard": {
    "sandbox_mode": false,
    "writing_base_dir": "canlı",
    "guard_status": "KORUMA AKTİF",
    "recent_events": [
      {
        "ts": "2026-03-25T07:32:59Z",
        "text": "Henüz aktivite yok."
      }
    ],
    "warnings": [],
    "last_activity": "2026-03-25T07:32:59Z"
  },
  "sandbox": {
    "sandbox_mode": false,
    "sandbox_source": "varsayılan",
    "writing_base_dir": "canlı"
  },
  "system": {
    "system_health": {
      "workspace_contract": {
        "status": "ok",
        "note": "Sözleşme yüklü; çekirdek path'ler tanımlı."
      },
      "task_engine": {
        "status": "ok",
        "note": "Görev listesi okunabiliyor."
      },
      "sandbox_source": {
        "status": "ok",
        "note": "Sandbox kaynağı sözleşmeden türetildi."
      },
      "trash_contract": {
        "status": "ok",
        "note": "Trash konumu sözleşmeyle sabit."
      },
      "config_sink": {
        "status": "ok",
        "note": "Config salt okunur alanlar bridge ile besleniyor."
      },
      "identity_sink": {
        "status": "ok",
        "note": "Identity salt okunur alanlar bridge ile besleniyor."
      },
      "keystore_sink": {
        "status": "uyarı",
        "note": "Keystore durumu consent ile türetildi; ifşa yok."
      },
      "general": {
        "status": "uyarı",
        "note": "Consent alınmadı."
      }
    },
    "system_paths": {
      "writing_base": "/Users/candasoz/WORK_2026/lumos-core/.lumos",
      "trash": "/Users/candasoz/WORK_2026/lumos-core/.lumos/trash",
      "sandbox_base": "/Users/candasoz/WORK_2026/lumos-core/.lumos/sandbox",
      "config": "/Users/candasoz/WORK_2026/lumos-core/.lumos/config.json",
      "logs": "/Users/candasoz/WORK_2026/lumos-core/.lumos/logs",
      "tasks": "/Users/candasoz/WORK_2026/lumos-core/.lumos/tasks.json"
    },
    "system_summary": {
      "config_exists": false,
      "tasks_file_exists": true,
      "task_count": 0,
      "trash_dir_exists": true,
      "trash_item_count": 0,
      "log_file_exists": true,
      "log_line_count": 0
    }
  },
  "config": {
    "config_snapshot": {
      "profil": "—",
      "workspace_root": ".lumos",
      "write_status": "Salt okunur",
      "last_activity": null,
      "last_activity_text": "Config dosyası yok veya okunamadı; yalnızca okuma."
    }
  },
  "identity": {
    "identity_state": "mevcut değil",
    "identity_last_write": null,
    "identity_target_scope": "çekirdek kimlik alanı",
    "identity_guard_result": "Korunuyor"
  },
  "keystore": {
    "keystore_ready": false,
    "keystore_state": "eksik",
    "consent_ok": false,
    "consent_proxy_state": "onay bekleniyor",
    "session_unlocked": null,
    "session_unlocked_note": "Panel köprüsü runtime oturum kilidini (session_unlocked) bu okuma yolunda doğrulamaz.",
    "keystore_last_update": null,
    "keystore_write_scope": "Kilit açılmadan hassas yazım yapılmaz",
    "display_note": "keystore_ready = dosya init; consent_proxy_state = genel onay vekili; session_unlocked bu köprüde doğrulanmaz."
  },
  "tasks": {
    "task_list": [],
    "task_filter": "all",
    "selected_task_id": null,
    "list_updated": "2026-03-21T13:23:27",
    "list_updated_text": "Son güncelleme: 21.03.2026 13:23",
    "tasks_file_path": "/Users/candasoz/WORK_2026/lumos-core/.lumos/tasks.json",
    "tasks_file_exists": true,
    "task_count": 0
  },
  "trash": {
    "trash_location": "/Users/candasoz/WORK_2026/lumos-core/.lumos/trash",
    "trash_last_move": null,
    "trash_items": [],
    "trash_dir_exists": true,
    "trash_item_count": 0,
    "trash_scope_fallback_note": "original_path ve scope dosya sisteminden okunamadı; meta yoksa — gösterilir."
  },
  "logs": {
    "log_items": [],
    "log_filter": "all",
    "log_file_updated": "2026-03-25T06:55:38",
    "log_updated_text": "Son güncelleme: 25.03.2026 06:55",
    "log_location": "/Users/candasoz/WORK_2026/lumos-core/.lumos/logs/log.txt",
    "log_file_exists": true,
    "log_line_count": 0
  },
  "guidance": {
    "mode": "offline",
    "lock": "LOCKED",
    "lock_scope": "consent_proxy",
    "consent": false,
    "consent_proxy_state": "onay bekleniyor",
    "session_unlocked": null,
    "session_unlocked_note": "Panel köprüsü runtime oturum kilidini (session_unlocked) bu okuma yolunda doğrulamaz.",
    "blocked_reason": null,
    "next_step": null
  },
  "yanit": {
    "summary": "Şu an mod çevrimdışı. Yazım hedefi canlı çalışma alanı. Genel onay henüz kayıtlı değil; hassas yazım ve keystore akışı kısıtlı kalır. Sistem özeti: Consent alınmadı.",
    "context_line": "Son karar kaydı: goal — Minimal, dar kapsamlı değişiklik: goal.",
    "understood": [
      "Mod: çevrimdışı.",
      "Kilit kapalı; koruma aktif.",
      "Genel onay: kapalı.",
      "Kimlik dosyası: mevcut değil.",
      "Anahtar kasası: Kilitli.",
      "Görev motoru: Görev listesi okunabiliyor.",
      "tasks.json içinde 0 görev kaydı var."
    ],
    "recommendation": [
      "Çalışmaya devam için consent kaydını tamamlayın (startup_health; hassas yüzeyler kapalı kalır)."
    ],
    "questions": [
      "Görev kuyruğu boş; ilk görevi hangi kanaldan oluşturacaksınız?",
      "Kimlik dosyası yok; bu ortamda kimlik kurulumu gerekiyor mu?"
    ],
    "updated_at": "2026-03-21T13:23:27"
  },
  "lumos_status": {
    "core_active": true,
    "online_mode": "offline",
    "sandbox_mode": false,
    "writing_base_dir": "canlı",
    "panel_bridge_built_at": "2026-03-25T07:32:59Z",
    "state_inject_note": "Canlı: GET /lumos-read-state (panel_tasks_server). İlk yükleme: state_inject.js.",
    "last_repo_query": "—",
    "pending_flow": "Yok",
    "last_output_preview": "—",
    "context_summary": "Boş",
    "repo_navigation": "Sonuç listesi yok",
    "kando_snapshot_at": "—",
    "kando_snapshot_note": "Kando bu süreçte henüz güncellenmedi (runtime boş).",
    "backend_live_at": "2026-03-25T07:32:59Z",
    "last_activity": "2026-03-25T07:32:36Z",
    "context_reuse_state": "mevcut",
    "context_last_repo_query": "llm"
  },
  "panel_meta": {
    "server_time_utc": "2026-03-25T07:32:59Z",
    "live_state_fresh": true
  },
  "internal_events": [
    {
      "ts": "2026-03-25T07:32:36Z",
      "type": "repo_search",
      "text": "Repo araması yapıldı: llm"
    },
    {
      "ts": "2026-03-25T07:16:35Z",
      "type": "pending_repo_complete",
      "text": "Pending repo sorgusu tamamlandı: intent score"
    },
    {
      "ts": "2026-03-25T07:16:35Z",
      "type": "pending_repo_wait",
      "text": "Repo için sorgu bekleniyor."
    },
    {
      "ts": "2026-03-25T07:16:35Z",
      "type": "repo_select",
      "text": "Repo sonucu seçildi: 1"
    },
    {
      "ts": "2026-03-25T07:16:35Z",
      "type": "repo_search",
      "text": "Repo araması yapıldı: llm"
    }
  ],
  "product_features": [
    {
      "key": "intent_engine",
      "ad": "Intent Engine",
      "durum": "planned",
      "panelde_gorunuyor": true,
      "aciklama": "Niyet eşleme motoru komut işleme sinyaliyle doğrulanır."
    },
    {
      "key": "repo_search",
      "ad": "Repo Search",
      "durum": "active",
      "panelde_gorunuyor": true,
      "aciklama": "Repo arama sinyali son repo sorgusu veya arama olayıyla doğrulanır."
    },
    {
      "key": "context_reuse",
      "ad": "Context Reuse",
      "durum": "active",
      "panelde_gorunuyor": true,
      "aciklama": "Context durumu: mevcut. Son repo sorgusu kalıcı store üzerinden okunur."
    },
    {
      "key": "pending_completion",
      "ad": "Pending Completion",
      "durum": "active",
      "panelde_gorunuyor": true,
      "aciklama": "Pending repo bekleme/tamamlama sinyaliyle doğrulanır."
    },
    {
      "key": "repo_navigation",
      "ad": "Repo Select/Next/Prev",
      "durum": "active",
      "panelde_gorunuyor": true,
      "aciklama": "Repo sonuç seti ve gezinme sinyalleriyle doğrulanır."
    },
    {
      "key": "live_backend_state",
      "ad": "Live Backend State",
      "durum": "connected",
      "panelde_gorunuyor": true,
      "aciklama": "Panel canlı state endpointinden periyodik veri çekiyor."
    },
    {
      "key": "panel_bridge",
      "ad": "Panel Bridge",
      "durum": "connected",
      "panelde_gorunuyor": true,
      "aciklama": "__LUMOS_READ_STATE__ köprüsü backend payload alanlarıyla doğrulanır."
    },
    {
      "key": "last_activity_card",
      "ad": "Son Aktivite Kartı",
      "durum": "in_progress",
      "panelde_gorunuyor": true,
      "aciklama": "Dashboard Son Aktivite alanı backend olaylarından besleniyor."
    }
  ]
};
