"""
Kando → Cursor köprüsü: yürütme ve sonuç paketi sözleşmesi (JSON uyumlu).

Amaç: Harici Cursor ajanı / araç zinciri bu şemayı okuyup uygulayabilsin;
patch / guard / profil semantiği ile uyumlu alanlar (hedef, adım türü, verify).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Outcome = Literal["applied", "blocked", "failed", "partial", "simulation"]


@dataclass
class PlannedStepV1:
    """TaskEngine adımı + runtime guard sonucu."""

    title: str
    kind: str
    guard_allowed: bool


@dataclass
class CursorExecutionPacketV1:
    """
    Yürütme öncesi plan: niyet → adımlar + profil + patch ipuçları.

    Tüketici uyumu (Cursor CLI / harici runner): üst düzey alanlar
    target_file, instruction, verify — örn. last_execution.json okuyan script'ler.
    """

    schema_version: str
    goal: str
    task_id: int
    permission_profile: str
    general_approval: bool
    steps: list[PlannedStepV1]
    patch: dict[str, Any] | None
    # constraints["execution"] veya constraints["force"]: instruction patch için giriş;
    # execution input ör. {"force": true} → yüksek riskli yamayı manuel zorla uygula.
    constraints: dict[str, Any] = field(default_factory=dict)
    # Harici tüketici sözleşmesi (cursor --apply vb.)
    execution_mode: str = "task"  # "patch" | "task"
    target_file: str = ""
    target_files: list[str] = field(default_factory=list)
    instruction: str = ""
    verify: str = ""

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CursorResultPacketV1:
    """Yürütme sonrası kısa sonuç (applied / blocked / failed + doğrulama özeti)."""

    schema_version: str
    goal_preview: str
    outcome: Outcome
    reason: str
    verification_summary: str
    task_id: int
    task_status: str
    brain_success: bool
    verified_count: int
    unverified_count: int
    simulation_count: int
    execution: dict[str, Any] | None = None
    execution_history_summary: list[dict[str, Any]] = field(default_factory=list)
    audit_id_chain: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


SCHEMA_EXECUTION = "kando.cursor.execution.v1"
SCHEMA_RESULT = "kando.cursor.result.v1"
