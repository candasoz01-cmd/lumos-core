//! Local-only suspicious activity detector (S4). No network, no external notify.

use crate::event_log::EventRecord;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{LazyLock, Mutex};

/// Failed unlock attempts before local `SUSPICIOUS` flag is raised.
pub const ACCESS_DENIED_THRESHOLD: usize = 5;

/// Process-local session metadata keyed by vault path.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SessionFlags {
    pub failed_unlock_attempts: usize,
    pub suspicious: bool,
}

static SESSION_FLAGS: LazyLock<Mutex<HashMap<PathBuf, SessionFlags>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

fn normalize_path(path: &Path) -> PathBuf {
    path.canonicalize().unwrap_or_else(|_| path.to_path_buf())
}

/// Read process-local session flags for a vault path.
pub fn session_flags(path: &Path) -> SessionFlags {
    let key = normalize_path(path);
    SESSION_FLAGS
        .lock()
        .map(|g| g.get(&key).cloned().unwrap_or_default())
        .unwrap_or_default()
}

/// Reset session flags after successful unlock.
pub fn reset_session_flags(path: &Path) {
    if let Ok(mut guard) = SESSION_FLAGS.lock() {
        guard.remove(&normalize_path(path));
    }
}

/// Increment in-memory failed unlock counter; returns updated flags.
pub fn record_failed_unlock(path: &Path) -> SessionFlags {
    let key = normalize_path(path);
    let mut guard = SESSION_FLAGS.lock().ok();
    if let Some(ref mut g) = guard {
        let entry = g.entry(key).or_default();
        entry.failed_unlock_attempts += 1;
        if entry.failed_unlock_attempts >= ACCESS_DENIED_THRESHOLD {
            entry.suspicious = true;
        }
        return entry.clone();
    }
    SessionFlags::default()
}

/// Mark session suspicious from event log history (for status without active session).
pub fn suspicious_from_log(records: &[EventRecord]) -> bool {
    if records
        .iter()
        .any(|r| r.event_type == crate::event_log::EventType::SuspiciousFlag)
    {
        return true;
    }
    count_access_denied_records(records) >= ACCESS_DENIED_THRESHOLD
}

pub fn count_access_denied_records(records: &[EventRecord]) -> usize {
    records
        .iter()
        .filter(|r| r.event_type == crate::event_log::EventType::AccessDenied)
        .count()
}

pub fn log_already_suspicious(records: &[EventRecord]) -> bool {
    records
        .iter()
        .any(|r| r.event_type == crate::event_log::EventType::SuspiciousFlag)
}

/// Whether a new SUSPICIOUS_FLAG event should be appended after this ACCESS_DENIED.
pub fn should_append_suspicious_flag(denied_count: usize, records: &[EventRecord]) -> bool {
    denied_count >= ACCESS_DENIED_THRESHOLD && !log_already_suspicious(records)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::event_log::{EventRecord, EventType};
    use tempfile::tempdir;

    #[test]
    fn threshold_triggers_suspicious_flag() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("v.vault");
        reset_session_flags(&path);
        let mut flags = SessionFlags::default();
        for i in 1..=ACCESS_DENIED_THRESHOLD {
            flags = record_failed_unlock(&path);
            if i < ACCESS_DENIED_THRESHOLD {
                assert!(!flags.suspicious, "attempt {i}");
            }
        }
        assert!(flags.suspicious);
        assert_eq!(flags.failed_unlock_attempts, ACCESS_DENIED_THRESHOLD);
    }

    #[test]
    fn suspicious_from_log_counts_denied() {
        let mut head = [0u8; 32];
        let mut records = Vec::new();
        for i in 1..=ACCESS_DENIED_THRESHOLD {
            let rec = EventRecord::new(i as u64, EventType::AccessDenied, vec![], head);
            head = rec.record_hash;
            records.push(rec);
        }
        assert!(suspicious_from_log(&records));
    }
}
