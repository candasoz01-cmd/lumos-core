"""
Intent–surface mapper: map user intents (natural language) to device surfaces
(panels, settings pages, or system sections). Logic layer only; no UI.

Surfaces are identifiers such as privacy.camera, system.battery. Lumos can use
the result to answer the user, open the correct panel, or perform an allowed action.
"""

from __future__ import annotations

from typing import Any

# Surface identifiers (extendable).
SURFACE_PRIVACY_CAMERA = "privacy.camera"
SURFACE_PRIVACY_LOCATION = "privacy.location"
SURFACE_PRIVACY_MICROPHONE = "privacy.microphone"
SURFACE_SYSTEM_PROCESSES = "system.processes"
SURFACE_SYSTEM_BATTERY = "system.battery"
SURFACE_SYSTEM_NETWORK = "system.network"

# Registry entry: intent id, surface, description, and phrases/keywords to match (lowercased).
IntentMapping = tuple[str, str, str, tuple[str, ...]]

# Default registry: (intent_id, surface, description, match_phrases).
# Order matters: first match wins. Add new intents by appending to INTENT_REGISTRY or extending DEFAULT_PATTERNS.
DEFAULT_PATTERNS: list[IntentMapping] = [
    ("camera_permissions", SURFACE_PRIVACY_CAMERA, "Applications with camera access", (
        "kamera izinleri", "kamera izni", "kamera erişimi", "camera permissions",
        "camera access", "kameraya kim erişiyor", "hangi uygulamalar kamerayı kullanıyor",
    )),
    ("location_access", SURFACE_PRIVACY_LOCATION, "Applications with location access", (
        "konum erişimi", "konum izinleri", "location", "location access",
        "location permissions", "konuma kim erişiyor", "hangi uygulamalar konum kullanıyor",
    )),
    ("microphone_access", SURFACE_PRIVACY_MICROPHONE, "Applications with microphone access", (
        "mikrofon izinleri", "mikrofon erişimi", "microphone", "microphone access",
        "mikrofona kim erişiyor",
    )),
    ("background_processes", SURFACE_SYSTEM_PROCESSES, "Background and running processes", (
        "arka planda ne çalışıyor", "arka plan uygulamaları", "background processes",
        "çalışan uygulamalar", "running processes", "süreçler", "processes",
        "ne çalışıyor", "açık uygulamalar",
    )),
    ("battery_usage", SURFACE_SYSTEM_BATTERY, "Battery and power usage", (
        "pilimi ne tüketiyor", "pil tüketimi", "battery", "battery usage",
        "pil kullanımı", "güç tüketimi", "power usage",
    )),
    ("network_activity", SURFACE_SYSTEM_NETWORK, "Network and connectivity", (
        "ağ aktivitesi", "network", "network activity", "internet kullanımı",
        "bağlantılar", "connections",
    )),
]


def _normalize(text: str) -> str:
    """Normalize user input for matching: strip, lowercase, collapse spaces. No Turkish locale."""
    if not text:
        return ""
    t = text.strip().lower()
    while "  " in t:
        t = t.replace("  ", " ")
    return t


def _get_registry() -> list[IntentMapping]:
    """Return the intent registry (default; can be overridden or extended by callers)."""
    return list(DEFAULT_PATTERNS)


def resolve_intent_surface(user_text: str) -> dict[str, Any]:
    """
    Map user natural-language input to a device surface.

    Args:
        user_text: Raw user input (e.g. "kamera izinleri", "pilimi ne tüketiyor").

    Returns:
        Dict with:
          - intent: str (intent id) or None
          - surface: str (e.g. "privacy.camera") or None if no mapping
          - description: str (human-readable) or None
        If no clear mapping exists, surface is None and intent/description may be None.
    """
    normalized = _normalize(user_text)
    if not normalized:
        return {"intent": None, "surface": None, "description": None}

    for intent_id, surface, description, phrases in _get_registry():
        for phrase in phrases:
            if phrase in normalized or normalized in phrase:
                return {
                    "intent": intent_id,
                    "surface": surface,
                    "description": description,
                }

    return {"intent": None, "surface": None, "description": None}


def register_intent(intent_id: str, surface: str, description: str, match_phrases: tuple[str, ...]) -> None:
    """
    Extend the registry with a new intent->surface mapping.
    Call this at startup or when loading plugins to add intents without editing this module.
    """
    DEFAULT_PATTERNS.append((intent_id, surface, description, match_phrases))


# ---------------------------------------------------------------------------
# How Lumos can use this module later
# ---------------------------------------------------------------------------
#
# 1. Answer the user
#    - On queries like "kamera izinleri" or "pilimi ne tüketiyor", call resolve_intent_surface(user_text).
#    - If surface is not None, Lumos can respond with the description and/or: "Bunu ayarlarda şurada bulabilirsin: <surface>"
#    - Optional: combine with device_guard or system_monitor to add a one-line summary (e.g. "Şu an 3 uygulama kamera kullanıyor").
#
# 2. Open the correct panel
#    - A UI layer (CLI submenu, TUI, or desktop/Web UI) can subscribe to "open_surface(surface)".
#    - When the user asks to open a surface, resolve_intent_surface() gives surface e.g. "privacy.camera";
#    - The UI maps surface to a concrete panel (e.g. Settings > Privacy > Camera) and opens it, or shows a deep link.
#    - Lumos does not implement the panel; it only returns the surface id so the host or UI can decide how to open it.
#
# 3. Perform an action if allowed
#    - If the runtime has an "action" mode (e.g. user said "kamera izinlerini aç"), the same resolver can be used
#      to get surface; then a separate policy layer decides whether Lumos is allowed to trigger "open" (e.g. open
#      Settings to that panel). No automatic permission changes—only "navigate to the place where the user can change it."
#    - All sensitive actions (revoke permission, kill process) remain subject to existing Lumos rules (explicit user
#      command, no automatic termination, etc.). This module only provides intent->surface mapping.
