use crate::error::{AnchorError, Result};
use crate::header::{VaultHeader, VERIFIER_PLAINTEXT};
use aes_gcm::aead::{Aead, KeyInit};
use aes_gcm::{Aes256Gcm, Key, Nonce};
use argon2::{Algorithm, Argon2, Params, Version};
use zeroize::{Zeroize, ZeroizeOnDrop};

#[derive(Zeroize, ZeroizeOnDrop)]
pub struct VaultKey([u8; 32]);

impl VaultKey {
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

pub fn derive_key(header: &VaultHeader, passphrase: &str) -> Result<VaultKey> {
    let params = Params::new(
        header.argon2_m_cost,
        header.argon2_t_cost,
        header.argon2_p_cost,
        Some(32),
    )
    .map_err(|e| AnchorError::Crypto(e.to_string()))?;
    let argon2 = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);
    let mut key = [0u8; 32];
    argon2
        .hash_password_into(passphrase.as_bytes(), &header.salt, &mut key)
        .map_err(|e| AnchorError::Crypto(e.to_string()))?;
    Ok(VaultKey(key))
}

pub fn seal_verifier(key: &VaultKey, nonce: &[u8; 12]) -> Result<([u8; 16], [u8; 16])> {
    let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key.as_bytes()));
    let nonce = Nonce::from_slice(nonce);
    let sealed = cipher
        .encrypt(nonce, VERIFIER_PLAINTEXT.as_ref())
        .map_err(|e| AnchorError::Crypto(e.to_string()))?;
    let tag_start = sealed.len() - 16;
    let mut ciphertext = [0u8; 16];
    let mut tag = [0u8; 16];
    ciphertext.copy_from_slice(&sealed[..tag_start]);
    tag.copy_from_slice(&sealed[tag_start..]);
    Ok((ciphertext, tag))
}

pub fn verify_passphrase(key: &VaultKey, header: &VaultHeader) -> Result<()> {
    let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key.as_bytes()));
    let nonce = Nonce::from_slice(&header.verify_nonce);
    let mut blob = header.verify_ciphertext.to_vec();
    blob.extend_from_slice(&header.verify_tag);
    let plain = cipher
        .decrypt(nonce, blob.as_ref())
        .map_err(|_| AnchorError::WrongPassphrase)?;
    if plain.as_slice() != VERIFIER_PLAINTEXT.as_ref() {
        return Err(AnchorError::WrongPassphrase);
    }
    Ok(())
}

pub fn encrypt_payload(key: &VaultKey, nonce: &[u8; 12], plaintext: &[u8]) -> Result<Vec<u8>> {
    if plaintext.is_empty() {
        return Ok(Vec::new());
    }
    let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key.as_bytes()));
    let nonce = Nonce::from_slice(nonce);
    cipher
        .encrypt(nonce, plaintext)
        .map_err(|e| AnchorError::Crypto(e.to_string()))
}

pub fn decrypt_payload(
    key: &VaultKey,
    nonce: &[u8; 12],
    ciphertext: &[u8],
    tag: &[u8; 16],
) -> Result<Vec<u8>> {
    if ciphertext.is_empty() {
        return Ok(Vec::new());
    }
    let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key.as_bytes()));
    let nonce = Nonce::from_slice(nonce);
    let mut blob = ciphertext.to_vec();
    blob.extend_from_slice(tag);
    cipher
        .decrypt(nonce, blob.as_ref())
        .map_err(|e| AnchorError::Crypto(e.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::header::VaultHeader;

    #[test]
    fn kdf_and_verifier_roundtrip() {
        let header = VaultHeader::new_for_create([9u8; 32], 0);
        let key = derive_key(&header, "test-pass").unwrap();
        let nonce = [7u8; 12];
        let (ct, tag) = seal_verifier(&key, &nonce).unwrap();
        let mut h = header;
        h.verify_nonce = nonce;
        h.verify_ciphertext = ct;
        h.verify_tag = tag;
        verify_passphrase(&key, &h).unwrap();
    }

    #[test]
    fn wrong_passphrase_fails() {
        let header = VaultHeader::new_for_create([9u8; 32], 0);
        let key = derive_key(&header, "right").unwrap();
        let nonce = [7u8; 12];
        let (ct, tag) = seal_verifier(&key, &nonce).unwrap();
        let mut h = header;
        h.verify_nonce = nonce;
        h.verify_ciphertext = ct;
        h.verify_tag = tag;
        let wrong = derive_key(&h, "wrong").unwrap();
        assert!(matches!(
            verify_passphrase(&wrong, &h),
            Err(AnchorError::WrongPassphrase)
        ));
    }
}
