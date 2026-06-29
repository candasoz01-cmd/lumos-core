//! Plugin registry skeleton — built-in `audit` enabled; external plugins require explicit config.

use crate::error::Result;
use crate::event_log::EventRecord;
use std::path::Path;
use std::sync::{Arc, LazyLock, Mutex};

/// Hooks for vault lifecycle and event observation. Local only.
pub trait VaultPlugin: Send + Sync {
    fn name(&self) -> &str;
    fn on_unlock(&self, ctx: &PluginContext) -> Result<()>;
    fn on_lock(&self, ctx: &PluginContext) -> Result<()>;
    fn on_event(&self, ctx: &PluginContext, event: &EventRecord) -> Result<()>;
}

#[derive(Debug, Clone)]
pub struct PluginContext {
    pub vault_path: std::path::PathBuf,
}

impl PluginContext {
    pub fn new(path: &Path) -> Self {
        Self {
            vault_path: path.to_path_buf(),
        }
    }
}

/// Enterprise / external plugins stay off unless explicitly enabled.
#[derive(Debug, Clone, Default)]
pub struct PluginConfig {
    pub enable_external_plugins: bool,
}

impl PluginConfig {
    pub fn from_env() -> Self {
        let enable = std::env::var("ANCHORUSB_ENABLE_EXTERNAL_PLUGINS")
            .map(|v| v == "1" || v.eq_ignore_ascii_case("true"))
            .unwrap_or(false);
        Self {
            enable_external_plugins: enable,
        }
    }
}

struct AuditPlugin;

impl VaultPlugin for AuditPlugin {
    fn name(&self) -> &str {
        "audit"
    }

    fn on_unlock(&self, ctx: &PluginContext) -> Result<()> {
        eprintln!(
            "[anchorusb:audit] unlock path={}",
            ctx.vault_path.display()
        );
        Ok(())
    }

    fn on_lock(&self, ctx: &PluginContext) -> Result<()> {
        eprintln!("[anchorusb:audit] lock path={}", ctx.vault_path.display());
        Ok(())
    }

    fn on_event(&self, ctx: &PluginContext, event: &EventRecord) -> Result<()> {
        eprintln!(
            "[anchorusb:audit] event={} seq={} path={}",
            event.event_type.as_str(),
            event.sequence,
            ctx.vault_path.display()
        );
        Ok(())
    }
}

/// Placeholder for future enterprise plugins — never auto-registered.
pub struct ExternalPluginStub {
    pub name: String,
}

impl VaultPlugin for ExternalPluginStub {
    fn name(&self) -> &str {
        &self.name
    }

    fn on_unlock(&self, _: &PluginContext) -> Result<()> {
        Ok(())
    }

    fn on_lock(&self, _: &PluginContext) -> Result<()> {
        Ok(())
    }

    fn on_event(&self, _: &PluginContext, _: &EventRecord) -> Result<()> {
        Ok(())
    }
}

pub struct PluginRegistry {
    builtins: Vec<Arc<dyn VaultPlugin>>,
    external: Vec<Arc<dyn VaultPlugin>>,
    config: PluginConfig,
    /// Audit hook invocations (test observable).
    audit_unlock_count: Mutex<usize>,
}

impl PluginRegistry {
    pub fn new(config: PluginConfig) -> Self {
        let mut registry = Self {
            builtins: Vec::new(),
            external: Vec::new(),
            config,
            audit_unlock_count: Mutex::new(0),
        };
        registry.register_builtin(Arc::new(AuditPlugin));
        registry
    }

    pub fn default_local() -> Self {
        Self::new(PluginConfig::default())
    }

    pub fn register_builtin(&mut self, plugin: Arc<dyn VaultPlugin>) {
        self.builtins.push(plugin);
    }

    pub fn register_external(&mut self, plugin: Arc<dyn VaultPlugin>) {
        self.external.push(plugin);
    }

    fn active_plugins(&self) -> Vec<Arc<dyn VaultPlugin>> {
        let mut out = self.builtins.clone();
        if self.config.enable_external_plugins {
            out.extend(self.external.clone());
        }
        out
    }

    pub fn dispatch_unlock(&self, ctx: &PluginContext) -> Result<()> {
        for p in self.active_plugins() {
            if p.name() == "audit" {
                if let Ok(mut c) = self.audit_unlock_count.lock() {
                    *c += 1;
                }
            }
            p.on_unlock(ctx)?;
        }
        Ok(())
    }

    pub fn dispatch_lock(&self, ctx: &PluginContext) -> Result<()> {
        for p in self.active_plugins() {
            p.on_lock(ctx)?;
        }
        Ok(())
    }

    pub fn dispatch_event(&self, ctx: &PluginContext, event: &EventRecord) -> Result<()> {
        for p in self.active_plugins() {
            p.on_event(ctx, event)?;
        }
        Ok(())
    }

    pub fn audit_unlock_count(&self) -> usize {
        self.audit_unlock_count.lock().map(|c| *c).unwrap_or(0)
    }

    pub fn external_enabled(&self) -> bool {
        self.config.enable_external_plugins
    }
}

static GLOBAL_REGISTRY: LazyLock<Arc<PluginRegistry>> =
    LazyLock::new(|| Arc::new(PluginRegistry::default_local()));

/// Shared plugin registry (built-in `audit` always active).
pub fn shared_registry() -> Arc<PluginRegistry> {
    Arc::clone(&GLOBAL_REGISTRY)
}

pub fn ensure_global_registry() -> Result<()> {
    let _ = &*GLOBAL_REGISTRY;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::event_log::{EventRecord, EventType};

    #[test]
    fn audit_hook_called_on_unlock() {
        let registry = PluginRegistry::default_local();
        let ctx = PluginContext::new(Path::new("/tmp/test.vault"));
        assert_eq!(registry.audit_unlock_count(), 0);
        registry.dispatch_unlock(&ctx).unwrap();
        assert_eq!(registry.audit_unlock_count(), 1);
    }

    #[test]
    fn external_plugin_disabled_without_config() {
        let mut registry = PluginRegistry::default_local();
        registry.register_external(Arc::new(ExternalPluginStub {
            name: "backup_local".into(),
        }));
        assert!(!registry.external_enabled());
        let plugins = registry.active_plugins();
        assert_eq!(plugins.len(), 1);
        assert_eq!(plugins[0].name(), "audit");
    }

    #[test]
    fn external_plugin_enabled_with_config() {
        let mut registry = PluginRegistry::new(PluginConfig {
            enable_external_plugins: true,
        });
        registry.register_external(Arc::new(ExternalPluginStub {
            name: "backup_local".into(),
        }));
        assert_eq!(registry.active_plugins().len(), 2);
    }

    #[test]
    fn audit_on_event_echoes_type() {
        let registry = PluginRegistry::default_local();
        let ctx = PluginContext::new(Path::new("/tmp/x.vault"));
        let event = EventRecord::new(1, EventType::Locked, vec![], [0u8; 32]);
        registry.dispatch_event(&ctx, &event).unwrap();
    }
}
