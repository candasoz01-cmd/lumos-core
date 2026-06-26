use crate::error::{AnchorError, Result};
use getrandom::getrandom;
use serde::{Deserialize, Serialize};

/// Fixed-size vault superblock (unencrypted).
pub const HEADER_SIZE: usize = 256;
pub const MAGIC: &[u8; 8] = b"ANCUSB01";
pub const HEADER_VERSION: u16 = 1;
pub const ALGO_AES_256_GCM: u8 = 1;

/// Known plaintext encrypted in the header to verify passphrase without decrypting payload.
pub const VERIFIER_PLAINTEXT: &[u8; 16] = b"ANCHORUSB-VERIFY";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct VaultHeader {
    pub version: u16,
    pub algorithm: u8,
    pub salt: [u8; 32],
    pub argon2_m_cost: u32,
    pub argon2_t_cost: u32,
    pub argon2_p_cost: u32,
    pub verify_nonce: [u8; 12],
    pub verify_ciphertext: [u8; 16],
    pub verify_tag: [u8; 16],
    pub payload_nonce: [u8; 12],
    pub payload_tag: [u8; 16],
    pub payload_len: u64,
    pub event_log_offset: u64,
    pub event_log_len: u64,
    pub event_chain_head: [u8; 32],
    pub created_at: i64,
}

impl VaultHeader {
    pub fn new_for_create(salt: [u8; 32], created_at: i64) -> Self {
        Self {
            version: HEADER_VERSION,
            algorithm: ALGO_AES_256_GCM,
            salt,
            argon2_m_cost: 19_456,
            argon2_t_cost: 2,
            argon2_p_cost: 1,
            verify_nonce: [0u8; 12],
            verify_ciphertext: [0u8; 16],
            verify_tag: [0u8; 16],
            payload_nonce: [0u8; 12],
            payload_tag: [0u8; 16],
            payload_len: 0,
            event_log_offset: HEADER_SIZE as u64,
            event_log_len: 0,
            event_chain_head: [0u8; 32],
            created_at,
        }
    }

    pub fn to_bytes(&self) -> Result<[u8; HEADER_SIZE]> {
        let mut buf = [0u8; HEADER_SIZE];
        buf[..8].copy_from_slice(MAGIC);
        buf[8..10].copy_from_slice(&self.version.to_le_bytes());
        buf[10] = self.algorithm;
        buf[11..16].fill(0);
        buf[16..48].copy_from_slice(&self.salt);
        buf[48..52].copy_from_slice(&self.argon2_m_cost.to_le_bytes());
        buf[52..56].copy_from_slice(&self.argon2_t_cost.to_le_bytes());
        buf[56..60].copy_from_slice(&self.argon2_p_cost.to_le_bytes());
        buf[60..72].copy_from_slice(&self.verify_nonce);
        buf[72..88].copy_from_slice(&self.verify_ciphertext);
        buf[88..104].copy_from_slice(&self.verify_tag);
        buf[104..116].copy_from_slice(&self.payload_nonce);
        buf[116..132].copy_from_slice(&self.payload_tag);
        buf[132..140].copy_from_slice(&self.payload_len.to_le_bytes());
        buf[140..148].copy_from_slice(&self.event_log_offset.to_le_bytes());
        buf[148..156].copy_from_slice(&self.event_log_len.to_le_bytes());
        buf[156..188].copy_from_slice(&self.event_chain_head);
        buf[188..196].copy_from_slice(&self.created_at.to_le_bytes());
        Ok(buf)
    }

    pub fn from_bytes(buf: &[u8]) -> Result<Self> {
        if buf.len() < HEADER_SIZE {
            return Err(AnchorError::InvalidVault("header too short".into()));
        }
        if &buf[..8] != MAGIC {
            return Err(AnchorError::InvalidVault("bad magic".into()));
        }
        let version = u16::from_le_bytes([buf[8], buf[9]]);
        if version != HEADER_VERSION {
            return Err(AnchorError::InvalidVault(format!(
                "unsupported version {version}"
            )));
        }
        let algorithm = buf[10];
        if algorithm != ALGO_AES_256_GCM {
            return Err(AnchorError::InvalidVault(format!(
                "unsupported algorithm {algorithm}"
            )));
        }
        let mut salt = [0u8; 32];
        salt.copy_from_slice(&buf[16..48]);
        Ok(Self {
            version,
            algorithm,
            salt,
            argon2_m_cost: u32::from_le_bytes(buf[48..52].try_into().unwrap()),
            argon2_t_cost: u32::from_le_bytes(buf[52..56].try_into().unwrap()),
            argon2_p_cost: u32::from_le_bytes(buf[56..60].try_into().unwrap()),
            verify_nonce: buf[60..72].try_into().unwrap(),
            verify_ciphertext: buf[72..88].try_into().unwrap(),
            verify_tag: buf[88..104].try_into().unwrap(),
            payload_nonce: buf[104..116].try_into().unwrap(),
            payload_tag: buf[116..132].try_into().unwrap(),
            payload_len: u64::from_le_bytes(buf[132..140].try_into().unwrap()),
            event_log_offset: u64::from_le_bytes(buf[140..148].try_into().unwrap()),
            event_log_len: u64::from_le_bytes(buf[148..156].try_into().unwrap()),
            event_chain_head: buf[156..188].try_into().unwrap(),
            created_at: i64::from_le_bytes(buf[188..196].try_into().unwrap()),
        })
    }
}

pub fn random_bytes<const N: usize>() -> Result<[u8; N]> {
    let mut buf = [0u8; N];
    getrandom(&mut buf).map_err(|e| AnchorError::Crypto(e.to_string()))?;
    Ok(buf)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn header_roundtrip() {
        let mut h = VaultHeader::new_for_create([1u8; 32], 1_700_000_000);
        h.verify_nonce = [2u8; 12];
        h.payload_len = 42;
        let bytes = h.to_bytes().unwrap();
        let parsed = VaultHeader::from_bytes(&bytes).unwrap();
        assert_eq!(h, parsed);
    }
}
