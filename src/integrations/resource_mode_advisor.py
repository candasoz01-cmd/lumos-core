"""Shared resource usage mode advisor — observe, recommend, apply only with approval."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from core.lumos_base_dir import lumos_base_dir

ResourceMode = Literal["active", "passive", "insufficient_data"]

RESOURCE_USAGE_FILENAME = "resource_usage.jsonl"
RESOURCE_MODES_FILENAME = "resource_modes.json"

# Phase 1 thresholds — documented in docs/analysis/lumos-resource-mode-advisor.md
CONNECTS_PER_DAY_ACTIVE = 3
EVENTS_PER_WEEK_ACTIVE = 10
LOOKBACK_DAYS = 7
IDLE_DAYS_PASSIVE = 15
MAX_STORED_EVENTS = 500


class ResourceLayer(str, Enum):
    QUANTUM = "quantum"
    CYBER = "cyber"
    VISION = "vision"
    VOICE = "voice"
    INTEGRATIONS = "integrations"
    GPU = "gpu"
    LOCAL_MODELS = "local_models"


class ResourceModeApprovalRequired(Exception):
    """Mode change blocked — explicit user approval required."""

    def __init__(self, layer: ResourceLayer, proposed_mode: str) -> None:
        self.layer = layer
        self.proposed_mode = proposed_mode
        super().__init__(
            f"approval_required: cannot apply mode '{proposed_mode}' for layer '{layer.value}'",
        )


def resource_usage_path(base_dir: Path | None = None) -> Path:
    return (base_dir or lumos_base_dir()) / RESOURCE_USAGE_FILENAME


def resource_modes_path(base_dir: Path | None = None) -> Path:
    return (base_dir or lumos_base_dir()) / RESOURCE_MODES_FILENAME


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_ts(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _normalize_layer(layer: ResourceLayer | str) -> ResourceLayer:
    if isinstance(layer, ResourceLayer):
        return layer
    return ResourceLayer(str(layer).strip().lower())


def _load_events(path: Path, layer: ResourceLayer) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        if item.get("layer") != layer.value:
            continue
        if isinstance(item.get("timestamp"), str):
            events.append(item)
    return events


def _append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    _trim_events(path)


def _trim_events(path: Path) -> None:
    if not path.is_file():
        return
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        return
    if len(lines) <= MAX_STORED_EVENTS:
        return
    path.write_text("\n".join(lines[-MAX_STORED_EVENTS:]) + "\n", encoding="utf-8")


def record_event(
    layer: ResourceLayer | str,
    action: str,
    metadata: dict[str, Any] | None = None,
    *,
    base_dir: Path | None = None,
) -> None:
    """Append a usage event to `.lumos/resource_usage.jsonl` (not core state)."""
    normalized = _normalize_layer(layer)
    path = resource_usage_path(base_dir)
    payload: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "layer": normalized.value,
        "action": action.strip().lower(),
    }
    if metadata:
        payload["metadata"] = metadata
    _append_event(path, payload)


def _compute_stats(
    events: list[dict[str, Any]],
    *,
    lookback_days: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    window_start = now - timedelta(days=lookback_days)
    day_start = now - timedelta(days=1)

    recent: list[dict[str, Any]] = []
    connects_today = 0
    last_activity: datetime | None = None

    for event in events:
        ts = _parse_ts(str(event.get("timestamp", "")))
        if ts is None:
            continue
        if last_activity is None or ts > last_activity:
            last_activity = ts
        if ts < window_start:
            continue
        recent.append(event)
        if event.get("action") == "connect" and ts >= day_start:
            connects_today += 1

    idle_days: int | None = None
    if last_activity is not None:
        idle_days = (now - last_activity).days

    return {
        "events_last_7d": len(recent),
        "connects_last_24h": connects_today,
        "idle_days": idle_days,
        "last_activity": last_activity.isoformat() if last_activity else None,
    }


def recommend_mode(
    layer: ResourceLayer | str,
    *,
    base_dir: Path | None = None,
    lookback_days: int = LOOKBACK_DAYS,
) -> dict[str, Any]:
    """
    Recommend active, passive, or insufficient_data for a resource layer.

    Returns dict with recommended_mode, reason, stats, thresholds, default_mode.
    """
    normalized = _normalize_layer(layer)
    path = resource_usage_path(base_dir)
    events = _load_events(path, normalized)
    stats = _compute_stats(events, lookback_days=lookback_days)

    event_count_week = stats["events_last_7d"]
    connects_today = stats["connects_last_24h"]
    idle_days = stats["idle_days"]

    thresholds = {
        "connects_per_day_active": CONNECTS_PER_DAY_ACTIVE,
        "events_per_week_active": EVENTS_PER_WEEK_ACTIVE,
        "idle_days_passive": IDLE_DAYS_PASSIVE,
        "lookback_days": lookback_days,
    }

    base = {
        "layer": normalized.value,
        "recommended_mode": "passive",
        "default_mode": "passive",
        "reason": "",
        "stats": stats,
        "thresholds": thresholds,
    }

    if idle_days is not None and idle_days >= IDLE_DAYS_PASSIVE:
        base["recommended_mode"] = "passive"
        base["reason"] = (
            f"Son {idle_days} gündür kullanım yok — beklemeli (passive) mod önerilir."
        )
        return base

    if event_count_week < 2 and connects_today < CONNECTS_PER_DAY_ACTIVE:
        base["recommended_mode"] = "insufficient_data"
        base["reason"] = (
            f"Yetersiz kullanım geçmişi ({event_count_week} olay / {lookback_days} gün, "
            f"{connects_today} connect / 24 saat)."
        )
        return base

    if connects_today >= CONNECTS_PER_DAY_ACTIVE or event_count_week >= EVENTS_PER_WEEK_ACTIVE:
        base["recommended_mode"] = "active"
        base["reason"] = (
            f"Sık kullanım: {connects_today} connect / 24 saat, "
            f"{event_count_week} olay / {lookback_days} gün."
        )
        return base

    base["recommended_mode"] = "passive"
    base["reason"] = (
        f"Düşük kullanım: {connects_today} connect / 24 saat, "
        f"{event_count_week} olay / {lookback_days} gün."
    )
    return base


def propose_mode_change(
    layer: ResourceLayer | str,
    *,
    base_dir: Path | None = None,
    lookback_days: int = LOOKBACK_DAYS,
) -> dict[str, Any]:
    """
    Build a recommendation payload for UI/CLI — never applies a mode change.
    """
    normalized = _normalize_layer(layer)
    rec = recommend_mode(normalized, base_dir=base_dir, lookback_days=lookback_days)
    modes_path = resource_modes_path(base_dir)
    current_mode = _load_current_mode(modes_path, normalized)

    proposed = rec["recommended_mode"]
    if proposed == "insufficient_data":
        proposed = rec["default_mode"]

    return {
        "layer": normalized.value,
        "current_mode": current_mode,
        "proposed_mode": proposed,
        "recommended_mode": rec["recommended_mode"],
        "reason": rec["reason"],
        "stats": rec["stats"],
        "thresholds": rec["thresholds"],
        "requires_approval": True,
        "approval_hint": "Kullanıcı 'Geç' derse uygula; 'Hayır aktif kalsın' derse reddet.",
        "never_auto": True,
    }


def _load_current_mode(path: Path, layer: ResourceLayer) -> str | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    entry = raw.get(layer.value)
    if isinstance(entry, dict) and isinstance(entry.get("mode"), str):
        return entry["mode"]
    return None


def _save_mode(
    path: Path,
    layer: ResourceLayer,
    mode: str,
    *,
    user_approved: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                data = existing
        except (OSError, json.JSONDecodeError):
            pass
    data[layer.value] = {
        "mode": mode,
        "applied_at": _utc_now_iso(),
        "user_approved": user_approved,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass(frozen=True)
class ApplyModeResult:
    ok: bool
    layer: str
    mode: str
    error: str | None = None
    applied_at: str | None = None


def apply_mode_change(
    layer: ResourceLayer | str,
    mode: ResourceMode,
    *,
    user_approved: bool = True,
    base_dir: Path | None = None,
    raise_on_denied: bool = False,
) -> ApplyModeResult:
    """
    Persist a mode change only when user_approved is True.

    By default returns ApplyModeResult(ok=False, error='approval_required').
    Set raise_on_denied=True to raise ResourceModeApprovalRequired instead.
    """
    normalized = _normalize_layer(layer)
    if mode == "insufficient_data":
        mode = "passive"

    if not user_approved:
        if raise_on_denied:
            raise ResourceModeApprovalRequired(normalized, mode)
        return ApplyModeResult(
            ok=False,
            layer=normalized.value,
            mode=mode,
            error="approval_required",
        )

    modes_path = resource_modes_path(base_dir)
    applied_at = _utc_now_iso()
    _save_mode(modes_path, normalized, mode, user_approved=True)
    record_event(
        normalized,
        "mode_change",
        {"mode": mode, "user_approved": True},
        base_dir=base_dir,
    )
    return ApplyModeResult(
        ok=True,
        layer=normalized.value,
        mode=mode,
        applied_at=applied_at,
    )
