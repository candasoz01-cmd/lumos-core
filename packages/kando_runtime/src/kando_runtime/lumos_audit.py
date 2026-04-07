"""Lumos görev denetimi: JSONL günlük + kuru tekrar (replay)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LumosAuditCollector:
    """Gate / LLM / yürütme izlerini toplayıp tek log satırı üretir."""

    def __init__(self, log_id: str | None = None) -> None:
        self.log_id = log_id or uuid.uuid4().hex
        self._input: dict[str, Any] = {}
        self._plan: dict[str, Any] = {}
        self._step_results: list[Any] = []
        self._blocked = False
        self._reason = ""
        self._execution_result = ""
        self._execution_kind = ""
        self._job_id: str | None = None
        self._replay_mode = False
        self._plan_llm_checks: list[dict[str, Any]] = []
        self._exec_llm_checks: list[dict[str, Any]] = []
        self._step_rows: dict[int, dict[str, Any]] = {}

    def set_input(self, mode: str, payload: str) -> None:
        self._input = {"mode": str(mode), "payload": str(payload or "")}

    def set_replay_mode(self, v: bool) -> None:
        self._replay_mode = bool(v)

    def set_plan(self, plan: dict[str, Any]) -> None:
        self._plan = dict(plan) if isinstance(plan, dict) else {}

    def _row(self, idx: int, step: dict[str, Any], risk: str) -> dict[str, Any]:
        if idx not in self._step_rows:
            self._step_rows[idx] = {"step": dict(step), "risk": risk, "phases": []}
        return self._step_rows[idx]

    def record_policy_phase(
        self,
        idx: int,
        step: dict[str, Any],
        risk: str,
        allowed: bool,
        gate: dict[str, Any],
    ) -> None:
        row = self._row(idx, step, risk)
        row["phases"].append(
            {
                "phase": "policy",
                "decision": "allowed" if allowed else "blocked",
                "source": "policy",
                "detail": dict(gate) if isinstance(gate, dict) else gate,
            }
        )

    def record_plan_llm_phase(
        self,
        idx: int,
        step: dict[str, Any],
        risk: str,
        allowed: bool,
        check: dict[str, Any],
    ) -> None:
        row = self._row(idx, step, risk)
        fb = check.get("llm_substep_validation") == "fallback"
        src = "fallback" if fb else "llm"
        row["phases"].append(
            {
                "phase": "plan_llm",
                "decision": "allowed" if allowed else "blocked",
                "source": src,
                "detail": dict(check),
            }
        )
        self._plan_llm_checks.append({"step_index": idx, "ok": allowed, "check": dict(check)})

    def record_exec_llm_phase(
        self,
        idx: int,
        step: dict[str, Any],
        risk: str,
        allowed: bool,
        check: dict[str, Any],
    ) -> None:
        row = self._row(idx, step, risk)
        fb = check.get("execution_llm_check") == "fallback"
        src = "fallback" if fb else "llm"
        row["phases"].append(
            {
                "phase": "execution_llm",
                "decision": "allowed" if allowed else "blocked",
                "source": src,
                "detail": dict(check),
            }
        )
        self._exec_llm_checks.append({"step_index": idx, "ok": allowed, "check": dict(check)})

    def set_step_results(self, results: list[Any]) -> None:
        self._step_results = list(results)

    def set_summary(
        self,
        *,
        blocked: bool,
        reason: str,
        execution_result: str,
        execution_kind: str = "",
        job_id: str | None = None,
    ) -> None:
        self._blocked = blocked
        self._reason = reason
        self._execution_result = execution_result
        if execution_kind:
            self._execution_kind = execution_kind
        if job_id is not None:
            self._job_id = job_id

    def _build_step_decisions(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for idx in sorted(self._step_rows):
            row = self._step_rows[idx]
            phases = row["phases"]
            decision = "allowed"
            source = "policy"
            for ph in phases:
                if ph["decision"] == "blocked":
                    decision = "blocked"
                    source = str(ph.get("source") or "policy")
                    break
            if decision == "allowed" and phases:
                if any(p.get("source") == "fallback" for p in phases):
                    source = "fallback"
                else:
                    source = str(phases[-1].get("source") or "llm")
            out.append(
                {
                    "step": row["step"],
                    "decision": decision,
                    "source": source,
                    "risk": row.get("risk"),
                }
            )
        return out

    def to_log_entry(self) -> dict[str, Any]:
        return {
            "schema_version": "lumos.audit_log.v1",
            "log_id": self.log_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input": dict(self._input),
            "plan": dict(self._plan),
            "steps": list(self._step_results),
            "step_decisions": self._build_step_decisions(),
            "blocked": self._blocked,
            "reason": self._reason,
            "execution_result": self._execution_result,
            "execution_kind": self._execution_kind,
            "job_id": self._job_id,
            "llm_checks": {
                "plan": list(self._plan_llm_checks),
                "execution": list(self._exec_llm_checks),
            },
            "replay_mode": self._replay_mode,
        }


def append_audit_log(repo_root: Path, entry: dict[str, Any]) -> None:
    log_dir = repo_root / ".lumos" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".log"
    path = log_dir / name
    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)


def find_audit_entry(repo_root: Path, log_id: str) -> dict[str, Any] | None:
    root = repo_root / ".lumos" / "logs"
    if not root.is_dir():
        return None
    for path in sorted(root.glob("*.log"), reverse=True):
        try:
            with path.open(encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if d.get("log_id") == log_id:
                        return d
        except OSError:
            continue
    return None


_PLAN_FAIL = frozenset(
    {
        "step_failed",
        "unknown_step",
        "substep_gate_blocked",
        "substep_llm_blocked",
        "execution_time_blocked",
    }
)


def compare_audit_entries(
    orig: dict[str, Any],
    replay: dict[str, Any],
    *,
    dry_run: bool = False,
) -> tuple[bool, list[str]]:
    diffs: list[str] = []
    if bool(orig.get("blocked")) != bool(replay.get("blocked")):
        diffs.append(
            f"blocked: orig={orig.get('blocked')!r} replay={replay.get('blocked')!r}"
        )
    oer = str(orig.get("execution_result") or "")
    rer = str(replay.get("execution_result") or "")
    if not dry_run and oer != rer:
        diffs.append(f"execution_result: orig={oer!r} replay={rer!r}")

    sa = orig.get("step_decisions") or []
    sb = replay.get("step_decisions") or []
    if len(sa) != len(sb):
        diffs.append(f"step_decisions len: {len(sa)} vs {len(sb)}")
    else:
        for i, (xa, xb) in enumerate(zip(sa, sb)):
            if (xa or {}).get("decision") != (xb or {}).get("decision"):
                diffs.append(
                    f"step[{i}].decision: {xa.get('decision')!r} vs {xb.get('decision')!r}"
                )
            if (xa or {}).get("source") != (xb or {}).get("source"):
                diffs.append(
                    f"step[{i}].source: {xa.get('source')!r} vs {xb.get('source')!r}"
                )
    return (len(diffs) == 0, diffs)


def plan_execution_failed(execution_result: str) -> bool:
    return execution_result in _PLAN_FAIL
