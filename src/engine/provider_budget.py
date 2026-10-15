"""OpenAI usage ledger and token budget gate.

Records model, token counts, purpose, and time. Never stores an API key,
prompt, or model response. When LUMOS_PROVIDER_BUDGET_TOKENS is unset, calls
proceed and the ledger is still appended. When it is set, each call reserves
the remaining budget before the provider request so concurrent callers cannot
all pass a check against the same remainder. Missing usage is not recorded as
zero: an in-flight reservation is charged in full, and a ledger row whose
spend cannot be proven blocks later budgeted calls.
"""

from __future__ import annotations

import fcntl
import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from core.lumos_base_dir import lumos_base_dir

LEDGER_NAME = "provider_usage.jsonl"
RESERVATION_NAME = "provider_budget_reservations.json"
LOCK_NAME = "provider_budget.lock"
STALE_RESERVATION_SECONDS = 120
PROVIDER_OPENAI = "openai"

REASON_EXHAUSTED = "provider_budget_exhausted"
REASON_RESERVED = "provider_budget_reserved"
REASON_USAGE_UNKNOWN = "provider_budget_usage_unknown"
REASON_CONFIG_INVALID = "provider_budget_config_invalid"
REASON_CALL_UNBOUNDED = "provider_budget_call_unbounded"

_MESSAGES = {
    REASON_EXHAUSTED: "sağlayıcı token bütçesi doldu; çağrı yapılmadı.",
    REASON_RESERVED: "eşzamanlı çağrı kalan bütçeyi tutuyor; çağrı yapılmadı.",
    REASON_USAGE_UNKNOWN: "kullanım bilgisi yok, sıfır sayılmadı; çağrı yapılmadı.",
    REASON_CONFIG_INVALID: "LUMOS_PROVIDER_BUDGET_TOKENS geçersiz; çağrı yapılmadı.",
    REASON_CALL_UNBOUNDED: "çağrı bütçe tavanına bağlanamadı; çağrı yapılmadı.",
}

_THREAD_LOCK = threading.Lock()


class BudgetConfigError(Exception):
    """LUMOS_PROVIDER_BUDGET_TOKENS is present but not a non-negative integer."""

    reason = REASON_CONFIG_INVALID


class BudgetDenied(Exception):
    """Call blocked before the provider request."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)

    def public_message(self) -> str:
        detail = _MESSAGES.get(self.reason, "çağrı yapılmadı.")
        return f"{self.reason}: {detail}"


@dataclass
class UsageSnapshot:
    usage_known: bool
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


@dataclass
class Reservation:
    id: str
    enforced: bool
    tokens: int
    provider: str
    model: str
    purpose: str
    settled: bool = False


def public_message(reason: str) -> str:
    detail = _MESSAGES.get(reason, "çağrı yapılmadı.")
    return f"{reason}: {detail}"


def budget_limit() -> int | None:
    """None when the limit is unset. Invalid text is not treated as unlimited."""
    if "LUMOS_PROVIDER_BUDGET_TOKENS" not in os.environ:
        return None
    raw = os.environ.get("LUMOS_PROVIDER_BUDGET_TOKENS", "")
    if raw.strip() == "":
        return None
    try:
        value = int(raw.strip())
    except (TypeError, ValueError) as exc:
        raise BudgetConfigError from exc
    if value < 0:
        raise BudgetConfigError
    return value


def known_token_count(value: Any) -> int | None:
    """A real token count. Missing or mock values are unknown, not zero."""
    if isinstance(value, bool):
        return None
    if type(value) is int:
        return value if value >= 0 else None
    if type(value) is float:
        if value < 0 or value != value:
            return None
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def usage_snapshot_from_response(response: Any) -> UsageSnapshot:
    usage = getattr(response, "usage", None) or getattr(response, "usage_metadata", None)
    if usage is None:
        return UsageSnapshot(False, None, None, None)
    input_tokens = known_token_count(getattr(usage, "input_tokens", None))
    if input_tokens is None:
        input_tokens = known_token_count(getattr(usage, "prompt_tokens", None))
    output_tokens = known_token_count(getattr(usage, "output_tokens", None))
    if output_tokens is None:
        output_tokens = known_token_count(getattr(usage, "completion_tokens", None))
    total_tokens = known_token_count(getattr(usage, "total_tokens", None))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    if total_tokens is None:
        return UsageSnapshot(False, input_tokens, output_tokens, None)
    return UsageSnapshot(True, input_tokens, output_tokens, total_tokens)


def reserve_for_call(*, model: str, purpose: str, provider: str = PROVIDER_OPENAI) -> Reservation:
    """Reserve remaining budget, or return an unenforced handle when no limit is set."""
    limit = budget_limit()
    safe_model = _safe_label(model, 80)
    safe_purpose = _safe_label(purpose or "chat", 32) or "chat"
    reservation = Reservation(
        id=uuid.uuid4().hex,
        enforced=limit is not None,
        tokens=0,
        provider=provider,
        model=safe_model,
        purpose=safe_purpose,
    )
    if limit is None:
        return reservation
    with _exclusive(lumos_base_dir()):
        _sweep_stale_locked()
        spent, inflight = _spend_locked()
        if spent >= limit:
            raise BudgetDenied(REASON_EXHAUSTED)
        room = limit - spent - inflight
        if room <= 0:
            raise BudgetDenied(REASON_RESERVED if inflight else REASON_EXHAUSTED)
        reservation.tokens = room
        _write_reservations(_load_reservations() + [_reservation_row(reservation)])
    return reservation


def commit_call(reservation: Reservation, snapshot: UsageSnapshot) -> None:
    """Append one ledger row and drop the reservation. Idempotent per reservation id."""
    if reservation.settled:
        return
    charged: int | None
    if snapshot.usage_known and snapshot.total_tokens is not None:
        charged = snapshot.total_tokens
    elif reservation.enforced:
        charged = reservation.tokens
    else:
        charged = None
    row = {
        "ts": _now_iso(),
        "provider": reservation.provider,
        "model": reservation.model,
        "purpose": reservation.purpose,
        "input_tokens": snapshot.input_tokens,
        "output_tokens": snapshot.output_tokens,
        "total_tokens": snapshot.total_tokens if snapshot.usage_known else None,
        "usage_known": bool(snapshot.usage_known and snapshot.total_tokens is not None),
        "charged_tokens": charged,
        "reservation_id": reservation.id,
    }
    with _exclusive(lumos_base_dir()):
        if reservation.id in _reservation_ids_locked():
            _drop_reservation_locked(reservation.id)
            reservation.settled = True
            return
        _append_row_locked(row)
        _drop_reservation_locked(reservation.id)
        reservation.settled = True


def commit_unknown(reservation: Reservation) -> None:
    commit_call(
        reservation,
        UsageSnapshot(False, None, None, None),
    )


def release_unsent(reservation: Reservation) -> None:
    """Drop a reservation when the provider request was never sent."""
    if reservation.settled:
        return
    with _exclusive(lumos_base_dir()):
        _drop_reservation_locked(reservation.id)
        reservation.settled = True


def _safe_label(value: str, limit: int) -> str:
    text = "".join(ch for ch in str(value or "") if ch.isalnum() or ch in "._-")
    return text[:limit]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ledger_path(base: Path | None = None) -> Path:
    return (base or lumos_base_dir()) / LEDGER_NAME


def _reservation_path(base: Path | None = None) -> Path:
    return (base or lumos_base_dir()) / RESERVATION_NAME


@contextmanager
def _exclusive(base: Path) -> Iterator[None]:
    base.mkdir(parents=True, exist_ok=True)
    lock_path = base / LOCK_NAME
    with _THREAD_LOCK:
        handle = lock_path.open("a+")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()


def _append_row_locked(row: dict[str, Any]) -> None:
    path = _ledger_path()
    line = json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def _iter_rows_locked() -> list[dict[str, Any]]:
    path = _ledger_path()
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BudgetDenied(REASON_USAGE_UNKNOWN) from exc
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BudgetDenied(REASON_USAGE_UNKNOWN) from exc
        if not isinstance(item, dict):
            raise BudgetDenied(REASON_USAGE_UNKNOWN)
        rows.append(item)
    return rows


def _reservation_ids_locked() -> set[str]:
    found: set[str] = set()
    for row in _iter_rows_locked():
        reservation_id = row.get("reservation_id")
        if isinstance(reservation_id, str) and reservation_id:
            found.add(reservation_id)
    return found


def _charged_amount(row: dict[str, Any]) -> int:
    """Proven spend. Unknown spend is never coerced to zero."""
    if row.get("usage_known") is True:
        amount = row.get("charged_tokens")
        if type(amount) is int and amount >= 0:
            return amount
        total = row.get("total_tokens")
        if type(total) is int and total >= 0:
            return total
        raise BudgetDenied(REASON_USAGE_UNKNOWN)
    amount = row.get("charged_tokens")
    if type(amount) is int and amount >= 0:
        return amount
    raise BudgetDenied(REASON_USAGE_UNKNOWN)


def _spend_locked() -> tuple[int, int]:
    spent = 0
    for row in _iter_rows_locked():
        spent += _charged_amount(row)
    inflight = 0
    for item in _load_reservations():
        tokens = item.get("tokens")
        if type(tokens) is not int or tokens < 0:
            raise BudgetDenied(REASON_USAGE_UNKNOWN)
        inflight += tokens
    return spent, inflight


def _load_reservations() -> list[dict[str, Any]]:
    path = _reservation_path()
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BudgetDenied(REASON_USAGE_UNKNOWN) from exc
    if not isinstance(payload, dict):
        raise BudgetDenied(REASON_USAGE_UNKNOWN)
    items = payload.get("reservations")
    if items is None:
        return []
    if not isinstance(items, list):
        raise BudgetDenied(REASON_USAGE_UNKNOWN)
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise BudgetDenied(REASON_USAGE_UNKNOWN)
        rows.append(item)
    return rows


def _write_reservations(items: list[dict[str, Any]]) -> None:
    path = _reservation_path()
    payload = json.dumps({"reservations": items}, ensure_ascii=True, separators=(",", ":"))
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def _reservation_row(reservation: Reservation) -> dict[str, Any]:
    return {
        "id": reservation.id,
        "tokens": reservation.tokens,
        "created_unix": time.time(),
        "provider": reservation.provider,
        "model": reservation.model,
        "purpose": reservation.purpose,
    }


def _drop_reservation_locked(reservation_id: str) -> None:
    kept = [item for item in _load_reservations() if item.get("id") != reservation_id]
    if kept:
        _write_reservations(kept)
    else:
        path = _reservation_path()
        if path.is_file():
            path.unlink()


def _sweep_stale_locked() -> None:
    now = time.time()
    fresh: list[dict[str, Any]] = []
    already = _reservation_ids_locked()
    for item in _load_reservations():
        created = item.get("created_unix")
        if type(created) is not float and type(created) is not int:
            fresh.append(item)
            continue
        if now - float(created) < STALE_RESERVATION_SECONDS:
            fresh.append(item)
            continue
        reservation_id = item.get("id")
        if not isinstance(reservation_id, str) or not reservation_id:
            raise BudgetDenied(REASON_USAGE_UNKNOWN)
        if reservation_id not in already:
            tokens = item.get("tokens")
            if type(tokens) is not int or tokens < 0:
                raise BudgetDenied(REASON_USAGE_UNKNOWN)
            _append_row_locked(
                {
                    "ts": _now_iso(),
                    "provider": _safe_label(str(item.get("provider") or PROVIDER_OPENAI), 32),
                    "model": _safe_label(str(item.get("model") or ""), 80),
                    "purpose": _safe_label(str(item.get("purpose") or "chat"), 32) or "chat",
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "usage_known": False,
                    "charged_tokens": tokens,
                    "reservation_id": reservation_id,
                }
            )
            already.add(reservation_id)
    if fresh:
        _write_reservations(fresh)
    else:
        path = _reservation_path()
        if path.is_file():
            path.unlink()
