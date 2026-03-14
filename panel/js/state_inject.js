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
    }
  },
  "config": {
    "config_snapshot": {
      "profil": "—",
      "workspace_root": ".lumos",
      "write_status": "Salt okunur",
      "last_activity": null,
      "last_activity_text": "Backend yazım kapalı; yalnızca okuma."
    }
  },
  "identity": {
    "identity_state": "—",
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
    "list_updated": null
  },
  "trash": {
    "trash_location": "/Users/candasoz/WORK_2026/lumos-core/.lumos/trash",
    "trash_last_move": null,
    "trash_items": []
  },
  "logs": {
    "log_items": [],
    "log_filter": "all",
    "log_file_updated": "2026-03-13T22:16:18",
    "log_location": "/Users/candasoz/WORK_2026/lumos-core/.lumos/logs/log.txt"
  }
};
