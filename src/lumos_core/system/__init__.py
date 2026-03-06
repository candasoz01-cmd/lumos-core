"""System detection: env scan, capability report (read-only, no persistence)."""

from lumos_core.system.env_scan import (
    build_capability_report,
    print_onboarding_preview,
    scan_apps_mac,
    scan_dev_environment,
    scan_permissions_mac,
    scan_system,
)

__all__ = [
    "build_capability_report",
    "print_onboarding_preview",
    "scan_apps_mac",
    "scan_dev_environment",
    "scan_permissions_mac",
    "scan_system",
]
