use thiserror::Error;

#[derive(Debug, Error)]
pub enum AnchorError {
    #[error("invalid vault file: {0}")]
    InvalidVault(String),
    #[error("wrong passphrase")]
    WrongPassphrase,
    #[error("vault already unlocked in this process")]
    AlreadyUnlocked,
    #[error("vault is locked")]
    VaultLocked,
    #[error("event log tampered: {0}")]
    TamperedLog(String),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("crypto error: {0}")]
    Crypto(String),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

pub type Result<T> = std::result::Result<T, AnchorError>;
