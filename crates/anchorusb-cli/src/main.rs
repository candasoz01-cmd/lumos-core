//! AnchorUSB CLI — local-only vault management (no network).

use anchorusb_core::{create_vault, lock_vault, unlock_vault, vault_status, AnchorError, UnlockedVault};
use clap::{Parser, Subcommand};
use std::path::PathBuf;
use std::sync::Mutex;

static SESSION: Mutex<Option<UnlockedVault>> = Mutex::new(None);

#[derive(Parser)]
#[command(name = "anchorusb", about = "AnchorUSB encrypted vault (local only)")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Create a new .vault container (S1 — first setup)
    Init {
        #[arg(long)]
        path: PathBuf,
        #[arg(long, env = "ANCHORUSB_PASSPHRASE")]
        passphrase: Option<String>,
    },
    /// Unlock vault into session (S2)
    Unlock {
        #[arg(long)]
        path: PathBuf,
        #[arg(long, env = "ANCHORUSB_PASSPHRASE")]
        passphrase: Option<String>,
    },
    /// Lock active session (S5)
    Lock,
    /// Show on-disk vault status
    Status {
        #[arg(long)]
        path: PathBuf,
    },
}

fn main() {
    if let Err(e) = run() {
        eprintln!("error: {e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), AnchorError> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Init { path, passphrase } => {
            let pw = passphrase_or_prompt(passphrase, "New passphrase: ")?;
            create_vault(&path, &pw)?;
            println!("vault initialized: {}", path.display());
            Ok(())
        }
        Commands::Unlock { path, passphrase } => {
            let pw = passphrase_or_prompt(passphrase, "Passphrase: ")?;
            let vault = unlock_vault(&path, &pw)?;
            println!("vault unlocked: {}", path.display());
            let mut guard = SESSION.lock().map_err(|_| {
                AnchorError::Crypto("session lock poisoned".into())
            })?;
            *guard = Some(vault);
            Ok(())
        }
        Commands::Lock => {
            let mut guard = SESSION.lock().map_err(|_| {
                AnchorError::Crypto("session lock poisoned".into())
            })?;
            if let Some(vault) = guard.take() {
                lock_vault(vault)?;
                println!("vault locked");
                Ok(())
            } else {
                Err(AnchorError::VaultLocked)
            }
        }
        Commands::Status { path } => {
            let status = vault_status(&path)?;
            if !status.exists {
                println!("status: not_found path={}", path.display());
            } else {
                println!(
                    "status: locked={} events={} last={} payload_bytes={} created_at={}",
                    status.locked,
                    status.event_count,
                    status.last_event.as_deref().unwrap_or("-"),
                    status.payload_len,
                    status.created_at.unwrap_or(0)
                );
            }
            Ok(())
        }
    }
}

fn passphrase_or_prompt(
    from_flag: Option<String>,
    prompt: &str,
) -> Result<String, AnchorError> {
    if let Some(p) = from_flag {
        return Ok(p);
    }
    rpassword::read_password()
        .map_err(|e| AnchorError::Crypto(e.to_string()))
        .and_then(|s| {
            if s.is_empty() {
                Err(AnchorError::InvalidVault("empty passphrase".into()))
            } else {
                Ok(s)
            }
        })
        .map(|s| {
            // avoid echoing prompt when using env; for interactive, rpassword handles it
            let _ = prompt;
            s
        })
}
