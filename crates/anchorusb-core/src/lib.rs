//! AnchorUSB core — encrypted `.vault` container, Argon2id KDF, hash-chained event log.
//!
//! Local-only: no network, no external notification.

pub mod crypto;
pub mod detector;
pub mod error;
pub mod event_log;
pub mod header;
pub mod plugins;
pub mod report;
pub mod vault;

pub use detector::{session_flags, ACCESS_DENIED_THRESHOLD, SessionFlags};
pub use error::{AnchorError, Result};
pub use event_log::{EventRecord, EventType};
pub use header::VaultHeader;
pub use plugins::{ensure_global_registry, shared_registry, PluginConfig, PluginContext, PluginRegistry, VaultPlugin};
pub use report::{build_report, export_report, VaultReport};
pub use vault::{
    create_vault, lock_vault, read_vault_parts, unlock_vault, vault_status, UnlockedVault,
    VaultStatus,
};
