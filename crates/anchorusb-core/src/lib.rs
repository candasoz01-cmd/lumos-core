//! AnchorUSB core — encrypted `.vault` container, Argon2id KDF, hash-chained event log.
//!
//! Local-only: no network, no external notification.

pub mod crypto;
pub mod error;
pub mod event_log;
pub mod header;
pub mod vault;

pub use error::{AnchorError, Result};
pub use event_log::{EventRecord, EventType};
pub use header::VaultHeader;
pub use vault::{create_vault, lock_vault, unlock_vault, vault_status, UnlockedVault, VaultStatus};
