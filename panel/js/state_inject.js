// Read-only bridge state (set by panel/scripts/read_backend_state.py --write)
window.__LUMOS_READ_STATE__ = {
  "dashboard": {
    "sandbox_mode": false,
    "writing_base_dir": "canlı",
    "guard_status": "KORUMA AKTİF",
    "recent_events": [],
    "warnings": []
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
        "status": "—",
        "note": "Görev listesi yok."
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
      "tasks_file_exists": false,
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
    "keystore_state": "Kilitli",
    "keystore_last_update": null,
    "keystore_write_scope": "Kilit açılmadan hassas yazım yapılmaz"
  },
  "tasks": {
    "task_list": [],
    "task_filter": "all",
    "selected_task_id": null,
    "list_updated": null,
    "list_updated_text": null,
    "tasks_file_path": null,
    "tasks_file_exists": false,
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
    "log_file_updated": "2026-03-20T19:14:46",
    "log_updated_text": "Son güncelleme: 20.03.2026 19:14",
    "log_location": "/Users/candasoz/WORK_2026/lumos-core/.lumos/logs/log.txt",
    "log_file_exists": true,
    "log_line_count": 0
  },
  "guidance": {
    "mode": "offline",
    "lock": "LOCKED",
    "consent": false,
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
      "Görev motoru: Görev listesi yok.",
      "tasks.json bulunamadı veya okunamadı; görev listesi boş sayılır."
    ],
    "recommendation": [
      "Çalışmaya devam için consent kaydını tamamlayın (startup_health; hassas yüzeyler kapalı kalır)."
    ],
    "questions": [
      "Kimlik dosyası yok; bu ortamda kimlik kurulumu gerekiyor mu?"
    ],
    "updated_at": null
  }
};
