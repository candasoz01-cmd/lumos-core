use crate::error::{AnchorError, Result};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::time::{SystemTime, UNIX_EPOCH};

/// MVP event kinds per `anchorusb-mvp-plan.md`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EventType {
    Initialized,
    Unlocked,
    Locked,
    IoSummary,
    AccessDenied,
}

impl EventType {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Initialized => "INITIALIZED",
            Self::Unlocked => "UNLOCKED",
            Self::Locked => "LOCKED",
            Self::IoSummary => "IO_SUMMARY",
            Self::AccessDenied => "ACCESS_DENIED",
        }
    }

    fn wire_byte(self) -> u8 {
        match self {
            Self::Initialized => 1,
            Self::Unlocked => 2,
            Self::Locked => 3,
            Self::IoSummary => 4,
            Self::AccessDenied => 5,
        }
    }

    fn from_wire_byte(b: u8) -> Result<Self> {
        match b {
            1 => Ok(Self::Initialized),
            2 => Ok(Self::Unlocked),
            3 => Ok(Self::Locked),
            4 => Ok(Self::IoSummary),
            5 => Ok(Self::AccessDenied),
            _ => Err(AnchorError::InvalidVault(format!("unknown event type {b}"))),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EventRecord {
    pub sequence: u64,
    pub timestamp_unix: i64,
    pub event_type: EventType,
    pub payload: Vec<u8>,
    pub prev_hash: [u8; 32],
    pub record_hash: [u8; 32],
}

impl EventRecord {
    pub fn new(
        sequence: u64,
        event_type: EventType,
        payload: Vec<u8>,
        prev_hash: [u8; 32],
    ) -> Self {
        let timestamp_unix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0);
        let mut rec = Self {
            sequence,
            timestamp_unix,
            event_type,
            payload,
            prev_hash,
            record_hash: [0u8; 32],
        };
        rec.record_hash = rec.compute_hash();
        rec
    }

    fn body_bytes(&self) -> Vec<u8> {
        let mut v = Vec::new();
        v.extend_from_slice(&self.prev_hash);
        v.extend_from_slice(&self.sequence.to_le_bytes());
        v.extend_from_slice(&self.timestamp_unix.to_le_bytes());
        v.push(self.event_type.wire_byte());
        v.extend_from_slice(&(self.payload.len() as u32).to_le_bytes());
        v.extend_from_slice(&self.payload);
        v
    }

    pub fn compute_hash(&self) -> [u8; 32] {
        let mut hasher = Sha256::new();
        hasher.update(self.body_bytes());
        hasher.finalize().into()
    }

    pub fn to_wire_bytes(&self) -> Vec<u8> {
        let body = self.body_bytes();
        let mut out = Vec::with_capacity(4 + body.len() + 32);
        let total_len = (body.len() + 32) as u32;
        out.extend_from_slice(&total_len.to_le_bytes());
        out.extend_from_slice(&body);
        out.extend_from_slice(&self.record_hash);
        out
    }

    pub fn from_wire_bytes(buf: &[u8], expected_prev: [u8; 32]) -> Result<(Self, usize)> {
        if buf.len() < 4 {
            return Err(AnchorError::InvalidVault("truncated event record".into()));
        }
        let total_len = u32::from_le_bytes(buf[0..4].try_into().unwrap()) as usize;
        if buf.len() < 4 + total_len {
            return Err(AnchorError::InvalidVault("truncated event body".into()));
        }
        let body = &buf[4..4 + total_len - 32];
        let record_hash: [u8; 32] = buf[4 + total_len - 32..4 + total_len]
            .try_into()
            .unwrap();
        if body.len() < 32 + 8 + 8 + 1 + 4 {
            return Err(AnchorError::InvalidVault("event body too short".into()));
        }
        let prev_hash: [u8; 32] = body[0..32].try_into().unwrap();
        if prev_hash != expected_prev {
            return Err(AnchorError::TamperedLog(
                "prev_hash mismatch in chain".into(),
            ));
        }
        let sequence = u64::from_le_bytes(body[32..40].try_into().unwrap());
        let timestamp_unix = i64::from_le_bytes(body[40..48].try_into().unwrap());
        let event_type = EventType::from_wire_byte(body[48])?;
        let payload_len =
            u32::from_le_bytes(body[49..53].try_into().unwrap()) as usize;
        let payload = body[53..53 + payload_len].to_vec();
        let rec = Self {
            sequence,
            timestamp_unix,
            event_type,
            payload,
            prev_hash,
            record_hash,
        };
        if rec.compute_hash() != record_hash {
            return Err(AnchorError::TamperedLog("record hash mismatch".into()));
        }
        Ok((rec, 4 + total_len))
    }
}

pub fn parse_event_log(bytes: &[u8], chain_head: [u8; 32]) -> Result<Vec<EventRecord>> {
    let mut records = Vec::new();
    let mut offset = 0;
    let mut prev = [0u8; 32];
    while offset < bytes.len() {
        let (rec, consumed) = EventRecord::from_wire_bytes(&bytes[offset..], prev)?;
        prev = rec.record_hash;
        records.push(rec);
        offset += consumed;
    }
    match records.last() {
        Some(last) if last.record_hash != chain_head => {
            return Err(AnchorError::TamperedLog(
                "chain head does not match last record".into(),
            ));
        }
        None if chain_head != [0u8; 32] => {
            return Err(AnchorError::TamperedLog(
                "non-zero chain head with empty log".into(),
            ));
        }
        _ => {}
    }
    Ok(records)
}

pub fn append_record(existing: &[u8], record: &EventRecord) -> Vec<u8> {
    let mut out = existing.to_vec();
    out.extend_from_slice(&record.to_wire_bytes());
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hash_chain_links() {
        let r0 = EventRecord::new(1, EventType::Initialized, b"init".to_vec(), [0u8; 32]);
        let r1 = EventRecord::new(2, EventType::Unlocked, vec![], r0.record_hash);
        let wire = append_record(&[], &r0);
        let wire = append_record(&wire, &r1);
        let parsed = parse_event_log(&wire, r1.record_hash).unwrap();
        assert_eq!(parsed.len(), 2);
        assert_eq!(parsed[1].prev_hash, r0.record_hash);
    }

    #[test]
    fn tamper_detected() {
        let r0 = EventRecord::new(1, EventType::Initialized, vec![], [0u8; 32]);
        let mut wire = r0.to_wire_bytes();
        wire[10] ^= 0xff;
        assert!(parse_event_log(&wire, r0.record_hash).is_err());
    }
}
