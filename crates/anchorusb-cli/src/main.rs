//! AnchorUSB CLI — local-only vault management (no network).

use anchorusb_core::{
    create_vault, export_report, lock_vault, unlock_vault, vault_status, AnchorError, UnlockedVault,
};
use anchorusb_core::plugins::ensure_global_registry;
use clap::{Parser, Subcommand};
use std::path::PathBuf;
use std::sync::Mutex;

static SESSION: Mutex<Option<UnlockedVault>> = Mutex::new(None);

const SUSPICIOUS_BANNER: &str = "⚠ SUSPICIOUS: repeated failed unlock attempts detected (local flag only; no network)";

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
    /// Export JSON report (S6 — user-initiated only)
    ExportReport {
        #[arg(long)]
        path: PathBuf,
        #[arg(long)]
        output: PathBuf,
    },
}

fn main() {
    if let Err(e) = run() {
        eprintln!("error: {e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), AnchorError> {
    let _ = ensure_global_registry();
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
            match unlock_vault(&path, &pw) {
                Ok(vault) => {
                    if vault.is_suspicious() {
                        eprintln!("{SUSPICIOUS_BANNER}");
                    }
                    println!("vault unlocked: {}", path.display());
                    let mut guard = SESSION.lock().map_err(|_| {
                        AnchorError::Crypto("session lock poisoned".into())
                    })?;
                    *guard = Some(vault);
                    Ok(())
                }
                Err(e) => {
                    let status = vault_status(&path)?;
                    if status.suspicious {
                        eprintln!("{SUSPICIOUS_BANNER}");
                        eprintln!(
                            "failed unlock attempts (session): {} denied (log): {}",
                            status.session_failed_attempts, status.access_denied_count
                        );
                    }
                    Err(e)
                }
            }
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
                if status.suspicious {
                    eprintln!("{SUSPICIOUS_BANNER}");
                }
                println!(
                    "status: locked={} suspicious={} events={} last={} payload_bytes={} created_at={} access_denied={}",
                    status.locked,
                    status.suspicious,
                    status.event_count,
                    status.last_event.as_deref().unwrap_or("-"),
                    status.payload_len,
                    status.created_at.unwrap_or(0),
                    status.access_denied_count
                );
            }
            Ok(())
        }
        Commands::ExportReport { path, output } => {
            export_report(&path, &output)?;
            println!("report exported: {}", output.display());
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
            let _ = prompt;
            s
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use anchorusb_core::create_vault;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn export_report_cli_integration() {
        let dir = tempdir().unwrap();
        let vault_path = dir.path().join("t.vault");
        let out = dir.path().join("out.json");
        create_vault(&vault_path, "pw").unwrap();
        export_report(&vault_path, &out).unwrap();
        let text = fs::read_to_string(&out).unwrap();
        assert!(text.contains("\"events\""));
        assert!(!text.contains("pw"));
    }
}
