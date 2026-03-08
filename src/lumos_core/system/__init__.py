"""System detection: env scan, capability report (read-only, no persistence)."""

from lumos_core.system.env_scan import (
    build_capability_report,
    get_macos_permission_readiness,
    print_onboarding_preview,
    print_permission_readiness,
    scan_apps_mac,
    scan_dev_environment,
    scan_permissions_mac,
    scan_system,
)

__all__ = [
    "build_capability_report",
    "get_macos_permission_readiness",
    "print_onboarding_preview",
    "print_permission_readiness",
    "scan_apps_mac",
    "scan_dev_environment",
    "scan_permissions_mac",
    "scan_system",
]
