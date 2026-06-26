use crate::crypto::{decrypt_payload, derive_key, encrypt_payload, seal_verifier, verify_passphrase, VaultKey};
use crate::error::{AnchorError, Result};
use crate::event_log::{append_record, parse_event_log, EventRecord, EventType};
use crate::header::{random_bytes, VaultHeader, HEADER_SIZE};
use serde::{Deserialize, Serialize};
use std::fs::{File, OpenOptions};
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

/// In-memory unlocked vault handle. Key is zeroized on drop.
pub struct UnlockedVault {
    path: PathBuf,
    header: VaultHeader,
    key: VaultKey,
    payload: Vec<u8>,
    session_open: bool,
}

impl Drop for UnlockedVault {
    fn drop(&mut self) {
        // VaultKey zeroizes via ZeroizeOnDrop when field is dropped
        self.session_open = false;
    }
}

impl UnlockedVault {
    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn payload(&self) -> &[u8] {
        &self.payload
    }

    pub fn write_payload(&mut self, data: &[u8]) -> Result<()> {
        self.payload = data.to_vec();
        self.flush_encrypted()?;
        self.append_event(EventType::IoSummary, b"payload_updated")?;
        Ok(())
    }

    fn flush_encrypted(&mut self) -> Result<()> {
        let payload_nonce = random_bytes()?;
        let sealed = encrypt_payload(&self.key, &payload_nonce, &self.payload)?;
        let (ciphertext, tag) = split_ciphertext_tag(sealed)?;
        self.header.payload_nonce = payload_nonce;
        self.header.payload_tag = tag;
        self.header.payload_len = ciphertext.len() as u64;

        let old_log_offset = self.header.event_log_offset;
        self.header.event_log_offset = HEADER_SIZE as u64 + self.header.payload_len;

        let mut file = OpenOptions::new()
            .read(true)
            .write(true)
            .open(&self.path)?;
        let mut log_bytes = vec![0u8; self.header.event_log_len as usize];
        if self.header.event_log_len > 0 {
            file.seek(SeekFrom::Start(old_log_offset))?;
            file.read_exact(&mut log_bytes)?;
        }
        file.seek(SeekFrom::Start(0))?;
        file.set_len(0)?;
        file.write_all(&self.header.to_bytes()?)?;
        file.write_all(&ciphertext)?;
        file.write_all(&log_bytes)?;
        file.sync_all()?;
        Ok(())
    }

    fn append_event(&mut self, event_type: EventType, payload: &[u8]) -> Result<()> {
        let mut file = OpenOptions::new()
            .read(true)
            .write(true)
            .open(&self.path)?;
        let mut log_bytes = vec![0u8; self.header.event_log_len as usize];
        if self.header.event_log_len > 0 {
            file.seek(SeekFrom::Start(self.header.event_log_offset))?;
            file.read_exact(&mut log_bytes)?;
        }
        let seq = parse_event_log(&log_bytes, self.header.event_chain_head)
            .map(|r| r.len() as u64 + 1)
            .unwrap_or(1);
        let record = EventRecord::new(
            seq,
            event_type,
            payload.to_vec(),
            self.header.event_chain_head,
        );
        log_bytes = append_record(&log_bytes, &record);
        self.header.event_log_len = log_bytes.len() as u64;
        self.header.event_chain_head = record.record_hash;

        let ciphertext_len = self.header.payload_len as usize;
        let mut ciphertext = vec![0u8; ciphertext_len];
        if ciphertext_len > 0 {
            file.seek(SeekFrom::Start(HEADER_SIZE as u64))?;
            file.read_exact(&mut ciphertext)?;
        }
        file.seek(SeekFrom::Start(0))?;
        file.set_len(0)?;
        file.write_all(&self.header.to_bytes()?)?;
        if !ciphertext.is_empty() {
            file.write_all(&ciphertext)?;
        }
        file.write_all(&log_bytes)?;
        file.sync_all()?;
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct VaultStatus {
    pub path: PathBuf,
    pub exists: bool,
    pub locked: bool,
    pub created_at: Option<i64>,
    pub event_count: usize,
    pub last_event: Option<String>,
    pub payload_len: u64,
}

/// Create a new `.vault` container at `path` with `passphrase`.
pub fn create_vault(path: &Path, passphrase: &str) -> Result<()> {
    if path.exists() {
        return Err(AnchorError::InvalidVault(format!(
            "{} already exists",
            path.display()
        )));
    }
    let salt = random_bytes()?;
    let created_at = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);
    let mut header = VaultHeader::new_for_create(salt, created_at);
    let key = derive_key(&header, passphrase)?;
    header.verify_nonce = random_bytes()?;
    (header.verify_ciphertext, header.verify_tag) =
        seal_verifier(&key, &header.verify_nonce)?;
    header.payload_nonce = random_bytes()?;
    let sealed = encrypt_payload(&key, &header.payload_nonce, &[])?;
    let (ct, tag) = split_ciphertext_tag(sealed)?;
    header.payload_tag = tag;
    header.payload_len = ct.len() as u64;
    header.event_log_offset = HEADER_SIZE as u64 + header.payload_len;

    let init_record = EventRecord::new(1, EventType::Initialized, b"vault_created".to_vec(), [0u8; 32]);
    let log_bytes = append_record(&[], &init_record);
    header.event_log_len = log_bytes.len() as u64;
    header.event_chain_head = init_record.record_hash;

    let mut file = File::create(path)?;
    file.write_all(&header.to_bytes()?)?;
    if !ct.is_empty() {
        file.write_all(&ct)?;
    }
    file.write_all(&log_bytes)?;
    file.sync_all()?;
    Ok(())
}

/// Unlock vault; returns in-memory handle. Wrong passphrase => `AnchorError::WrongPassphrase`.
pub fn unlock_vault(path: &Path, passphrase: &str) -> Result<UnlockedVault> {
    let (header, ciphertext, log_bytes) = read_vault_file(path)?;
    parse_event_log(&log_bytes, header.event_chain_head)?;
    let key = derive_key(&header, passphrase)?;
    if let Err(e) = verify_passphrase(&key, &header) {
        // append access denied without exposing key
        let _ = append_access_denied(path, &header, &log_bytes);
        return Err(e);
    }
    let payload = decrypt_payload(
        &key,
        &header.payload_nonce,
        &ciphertext,
        &header.payload_tag,
    )?;

    let mut vault = UnlockedVault {
        path: path.to_path_buf(),
        header,
        key,
        payload,
        session_open: true,
    };
    vault.append_event(EventType::Unlocked, b"session_start")?;
    Ok(vault)
}

/// Lock vault: zeroize key, append LOCKED event.
pub fn lock_vault(mut vault: UnlockedVault) -> Result<()> {
    if !vault.session_open {
        return Err(AnchorError::VaultLocked);
    }
    vault.append_event(EventType::Locked, b"session_end")?;
    vault.session_open = false;
    drop(vault);
    Ok(())
}

/// Read-only status from on-disk vault (always reports locked — unlock is session-local).
pub fn vault_status(path: &Path) -> Result<VaultStatus> {
    if !path.exists() {
        return Ok(VaultStatus {
            path: path.to_path_buf(),
            exists: false,
            locked: true,
            created_at: None,
            event_count: 0,
            last_event: None,
            payload_len: 0,
        });
    }
    let (header, _ct, log_bytes) = read_vault_file(path)?;
    let records = parse_event_log(&log_bytes, header.event_chain_head)?;
    let last_event = records.last().map(|r| r.event_type.as_str().to_string());
    Ok(VaultStatus {
        path: path.to_path_buf(),
        exists: true,
        locked: true,
        created_at: Some(header.created_at),
        event_count: records.len(),
        last_event,
        payload_len: header.payload_len,
    })
}

fn read_vault_file(path: &Path) -> Result<(VaultHeader, Vec<u8>, Vec<u8>)> {
    let mut file = File::open(path)?;
    let mut header_buf = [0u8; HEADER_SIZE];
    file.read_exact(&mut header_buf)?;
    let header = VaultHeader::from_bytes(&header_buf)?;
    let mut ciphertext = vec![0u8; header.payload_len as usize];
    if header.payload_len > 0 {
        file.read_exact(&mut ciphertext)?;
    }
    let mut log_bytes = vec![0u8; header.event_log_len as usize];
    if header.event_log_len > 0 {
        file.seek(SeekFrom::Start(header.event_log_offset))?;
        file.read_exact(&mut log_bytes)?;
    }
    Ok((header, ciphertext, log_bytes))
}

fn split_ciphertext_tag(sealed: Vec<u8>) -> Result<(Vec<u8>, [u8; 16])> {
    if sealed.len() < 16 {
        return Ok((sealed, [0u8; 16]));
    }
    let tag_start = sealed.len() - 16;
    let mut tag = [0u8; 16];
    tag.copy_from_slice(&sealed[tag_start..]);
    let ciphertext = sealed[..tag_start].to_vec();
    Ok((ciphertext, tag))
}

fn append_access_denied(path: &Path, header: &VaultHeader, existing_log: &[u8]) -> Result<()> {
    let seq = parse_event_log(existing_log, header.event_chain_head)
        .map(|r| r.len() as u64 + 1)
        .unwrap_or(1);
    let record = EventRecord::new(
        seq,
        EventType::AccessDenied,
        b"wrong_passphrase".to_vec(),
        header.event_chain_head,
    );
    let log_bytes = append_record(existing_log, &record);
    let mut new_header = header.clone();
    new_header.event_log_len = log_bytes.len() as u64;
    new_header.event_chain_head = record.record_hash;
    let mut file = OpenOptions::new()
        .read(true)
        .write(true)
        .open(path)?;
    file.seek(SeekFrom::Start(0))?;
    file.write_all(&new_header.to_bytes()?)?;
    file.seek(SeekFrom::Start(new_header.event_log_offset))?;
    file.write_all(&log_bytes)?;
    file.sync_all()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn create_unlock_lock_roundtrip() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("test.vault");
        create_vault(&path, "hunter2").unwrap();
        let status = vault_status(&path).unwrap();
        assert!(status.exists);
        assert_eq!(status.event_count, 1);
        let mut vault = unlock_vault(&path, "hunter2").unwrap();
        vault.write_payload(b"secret data").unwrap();
        lock_vault(vault).unwrap();
        let status = vault_status(&path).unwrap();
        assert!(status.event_count >= 4); // INIT, UNLOCK, IO, LOCK
    }

    #[test]
    fn wrong_passphrase_fails_and_logs() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("test.vault");
        create_vault(&path, "correct").unwrap();
        assert!(matches!(
            unlock_vault(&path, "wrong"),
            Err(AnchorError::WrongPassphrase)
        ));
        let status = vault_status(&path).unwrap();
        assert!(status.event_count >= 2);
        assert_eq!(status.last_event.as_deref(), Some("ACCESS_DENIED"));
    }

    #[test]
    fn event_log_has_required_types() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("test.vault");
        create_vault(&path, "pw").unwrap();
        let mut vault = unlock_vault(&path, "pw").unwrap();
        vault.write_payload(b"x").unwrap();
        lock_vault(vault).unwrap();
        let (header, _ct, log) = read_vault_file(&path).unwrap();
        let records = parse_event_log(&log, header.event_chain_head).unwrap();
        let types: Vec<_> = records.iter().map(|r| r.event_type).collect();
        assert!(types.contains(&EventType::Initialized));
        assert!(types.contains(&EventType::Unlocked));
        assert!(types.contains(&EventType::Locked));
        assert!(types.contains(&EventType::IoSummary));
    }
}
