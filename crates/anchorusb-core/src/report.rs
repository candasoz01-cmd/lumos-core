//! User-initiated vault report export (S6). No secrets, no auto-upload.

use crate::detector::{count_access_denied_records, suspicious_from_log, ACCESS_DENIED_THRESHOLD};
use crate::error::Result;
use crate::event_log::{parse_event_log, EventRecord};
use crate::header::VaultHeader;
use crate::vault::read_vault_parts;
use serde::Serialize;
use std::fs::File;
use std::io::Write;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize)]
pub struct VaultReport {
    pub exported_at_unix: i64,
    pub vault: VaultReportMetadata,
    pub events: Vec<EventReportEntry>,
    pub suspicious: bool,
    pub access_denied_count: usize,
    pub flags: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct VaultReportMetadata {
    pub path: String,
    pub header_version: u16,
    pub created_at: i64,
    pub payload_len: u64,
    pub event_count: usize,
    pub argon2_m_cost: u32,
    pub argon2_t_cost: u32,
    pub argon2_p_cost: u32,
}

#[derive(Debug, Serialize)]
pub struct EventReportEntry {
    pub sequence: u64,
    pub timestamp_unix: i64,
    pub event_type: String,
    pub payload_utf8: Option<String>,
    pub prev_hash_hex: String,
    pub record_hash_hex: String,
}

fn record_to_entry(rec: &EventRecord) -> EventReportEntry {
    let payload_utf8 = String::from_utf8(rec.payload.clone()).ok();
    EventReportEntry {
        sequence: rec.sequence,
        timestamp_unix: rec.timestamp_unix,
        event_type: rec.event_type.as_str().to_string(),
        payload_utf8,
        prev_hash_hex: hex::encode(rec.prev_hash),
        record_hash_hex: hex::encode(rec.record_hash),
    }
}

/// Build report JSON from on-disk vault. Never includes passphrase or key material.
pub fn build_report(path: &Path) -> Result<VaultReport> {
    let (header, _ciphertext, log_bytes) = read_vault_parts(path)?;
    let records = parse_event_log(&log_bytes, header.event_chain_head)?;
    build_report_from_parts(path, &header, &records)
}

pub fn build_report_from_parts(
    path: &Path,
    header: &VaultHeader,
    records: &[EventRecord],
) -> Result<VaultReport> {
    let suspicious = suspicious_from_log(records);
    let access_denied_count = count_access_denied_records(records);
    let mut flags = Vec::new();
    if suspicious {
        flags.push("SUSPICIOUS".into());
    }
    if access_denied_count >= ACCESS_DENIED_THRESHOLD {
        flags.push("ACCESS_DENIED_THRESHOLD".into());
    }

    let exported_at_unix = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);

    Ok(VaultReport {
        exported_at_unix,
        vault: VaultReportMetadata {
            path: path.display().to_string(),
            header_version: header.version,
            created_at: header.created_at,
            payload_len: header.payload_len,
            event_count: records.len(),
            argon2_m_cost: header.argon2_m_cost,
            argon2_t_cost: header.argon2_t_cost,
            argon2_p_cost: header.argon2_p_cost,
        },
        events: records.iter().map(record_to_entry).collect(),
        suspicious,
        access_denied_count,
        flags,
    })
}

/// Write report to `output` path (user-initiated only).
pub fn export_report(path: &Path, output: &Path) -> Result<()> {
    let report = build_report(path)?;
    let json = serde_json::to_string_pretty(&report)?;
    if let Some(parent) = output.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent)?;
        }
    }
    let mut file = File::create(output)?;
    file.write_all(json.as_bytes())?;
    file.sync_all()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::vault::{create_vault, unlock_vault};
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn export_report_valid_json_no_passphrase() {
        let dir = tempdir().unwrap();
        let vault_path = dir.path().join("r.vault");
        let out_path = dir.path().join("report.json");
        create_vault(&vault_path, "super_secret_passphrase").unwrap();
        let _ = unlock_vault(&vault_path, "super_secret_passphrase").unwrap();

        export_report(&vault_path, &out_path).unwrap();
        let text = fs::read_to_string(&out_path).unwrap();
        assert!(!text.contains("super_secret_passphrase"));
        assert!(!text.contains("salt"));
        let parsed: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert!(parsed.get("events").is_some());
        assert!(parsed.get("vault").is_some());
        assert_eq!(parsed["suspicious"], false);
    }
}
