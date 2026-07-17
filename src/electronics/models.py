"""
Elektronik Uzmanı — veri modelleri (Faz 1 pilot kapsamı).

Bu modül yalnızca in-memory veri yapıları ve saf (side-effect'siz) doğrulama
kurallarını tanımlar. Hiçbir dosya/veritabanı G/Ç, ağ çağrısı veya cihaz
etkileşimi yoktur. Tasarım kaynağı:
docs/analysis/electronics-expert-pilot-design.md

Kapsam dışı (bu fazda buraya eklenmez — design doc §8 NEVER_AUTO):
fotoğraf/OCR modeli, kamera ile otomatik teşhis, cihaz kontrolü,
programlayıcıya yazma, otomatik sipariş.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from task_engine.profiles import PROFILE_RAPOR

# --------------------------------------------------------------------------
# Ortak yardımcılar
# --------------------------------------------------------------------------


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------
# §3 Pilot kullanıcı yetkilendirmesi
# --------------------------------------------------------------------------

PilotGrantStatus = Literal["invited", "active", "revoked"]


@dataclass
class PilotAccessGrant:
    """Elektronik Uzmanı closed-pilot erişim kaydı (bkz. design doc §3).

    Kapsam daima `task_engine.profiles.PROFILE_RAPOR` (yalnızca analiz/öneri;
    hiçbir state-changing veya dış yazma eylemi bu scope'ta izinli değildir).
    """

    lumos_id: str
    grant_id: str = field(default_factory=new_id)
    pilot_program: Literal["electronics_expert_pilot"] = "electronics_expert_pilot"
    status: PilotGrantStatus = "invited"
    invited_at: datetime = field(default_factory=now_utc)
    activated_at: datetime | None = None
    revoked_at: datetime | None = None
    consent_version: str | None = None
    case_quota: int = 20
    cases_used: int = 0
    scope: str = PROFILE_RAPOR

    def __post_init__(self) -> None:
        if self.scope != PROFILE_RAPOR:
            raise ValueError(
                "PilotAccessGrant.scope must be task_engine.profiles.PROFILE_RAPOR "
                "(electronics expert pilot never grants safe_local/write_local/external)."
            )
        if self.case_quota < 0:
            raise ValueError("case_quota cannot be negative")


# --------------------------------------------------------------------------
# §4 Arıza Vakası
# --------------------------------------------------------------------------

FaultCaseStatus = Literal["open", "in_progress", "resolved", "archived"]

_FAULT_CASE_TRANSITIONS: dict[FaultCaseStatus, tuple[FaultCaseStatus, ...]] = {
    "open": ("in_progress", "archived"),
    "in_progress": ("resolved", "archived"),
    "resolved": ("archived",),
    "archived": (),
}


class InvalidFaultCaseTransition(ValueError):
    """Vaka durumu izin verilmeyen bir geçiş istediğinde fırlatılır."""


@dataclass
class DeviceBoardInfo:
    """Kullanıcının elle girdiği cihaz/kart bilgisi (bkz. design doc §4.1).

    Yalnızca manuel giriş alanlarıdır; fotoğraf/OCR bu fazda kapsam dışıdır.
    """

    device_type: str
    brand: str | None = None
    model: str | None = None
    board_id: str | None = None
    serial_number: str | None = None
    user_notes: str | None = None
    device_id: str = field(default_factory=new_id)


@dataclass
class FaultCase:
    """Arıza vakası (bkz. design doc §4)."""

    lumos_id: str
    title: str
    symptom_description: str
    device: DeviceBoardInfo
    case_id: str = field(default_factory=new_id)
    status: FaultCaseStatus = "open"
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    measurement_ids: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)
    risk_ids: list[str] = field(default_factory=list)
    paid_feature_status_snapshot: "PaidFeatureStatus" = "pilot"
    # "lumos_native" | "provider:<id>" — Faz 2 Provider katmanı için ayrılmış
    # alan (design doc §7). Bu fazda yalnızca "lumos_native" üretilir; hiçbir
    # canlı üçüncü taraf (E-Helper vb.) bağlantısı yoktur.
    source: str = "lumos_native"

    def transition_to(self, new_status: FaultCaseStatus) -> None:
        allowed = _FAULT_CASE_TRANSITIONS.get(self.status, ())
        if new_status not in allowed:
            raise InvalidFaultCaseTransition(
                f"{self.status} -> {new_status} is not an allowed FaultCase transition"
            )
        self.status = new_status
        self.updated_at = now_utc()

    def start_progress(self) -> None:
        self.transition_to("in_progress")

    def resolve(self) -> None:
        self.transition_to("resolved")

    def archive(self) -> None:
        self.transition_to("archived")

    def link_measurement(self, measurement_id: str) -> None:
        self.measurement_ids.append(measurement_id)
        self.updated_at = now_utc()

    def link_finding(self, finding_id: str) -> None:
        self.finding_ids.append(finding_id)
        self.updated_at = now_utc()

    def link_risk(self, risk_id: str) -> None:
        self.risk_ids.append(risk_id)
        self.updated_at = now_utc()


# --------------------------------------------------------------------------
# §6.1 Manuel Ölçüm Girişi
# --------------------------------------------------------------------------

MeasurementType = Literal[
    "voltage", "resistance", "current", "capacitance", "continuity", "frequency", "other"
]
MeasurementValueKind = Literal["numeric", "boolean", "categorical"]
CircuitState = Literal["deenergized", "energized", "unknown"]
ComparisonResult = Literal["below", "within", "above", "match", "mismatch", "unknown"]
ExpectedValueSource = Literal["user_entered", "datasheet_reference", "provider"]

DEFAULT_DEVIATION_TOLERANCE = 0.10  # %10 — yalnızca aritmetik yardım, teşhis değil


@dataclass
class MeasurementEntry:
    """Kullanıcının elle girdiği ölçüm kaydı (bkz. design doc §6.1).

    `entered_by` bu fazda daima "user"dır: ölçüm cihazından otomatik veri
    okuma (auto-import) kapsam dışıdır.
    """

    case_id: str
    test_point_label: str
    measurement_type: MeasurementType
    measured_value: float | bool | str
    unit: str | None
    measurement_id: str = field(default_factory=new_id)
    device_id: str | None = None
    reference_point: str | None = None
    instrument_mode: str = "manual"
    circuit_state: CircuitState = "deenergized"
    value_kind: MeasurementValueKind = "numeric"
    expected_min: float | None = None
    expected_nominal: float | None = None
    expected_max: float | None = None
    expected_text: str | None = None
    expected_value_source: ExpectedValueSource | None = None
    risk_check_ref: str | None = None
    entered_by: Literal["user"] = "user"
    recorded_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        if self.measurement_type == "voltage" and not self.reference_point:
            raise ValueError("voltage measurements require a reference_point")
        if self.circuit_state in ("energized", "unknown") and not self.risk_check_ref:
            raise ValueError(
                "energized or unknown circuit measurements require a risk_check_ref"
            )
        if self.value_kind == "numeric":
            if isinstance(self.measured_value, bool) or not isinstance(
                self.measured_value, (int, float)
            ):
                raise ValueError("numeric measurements require a numeric measured_value")
        elif self.value_kind == "boolean":
            if not isinstance(self.measured_value, bool):
                raise ValueError("boolean measurements require a bool measured_value")
        elif not isinstance(self.measured_value, str):
            raise ValueError("categorical measurements require a string measured_value")

        if (
            self.expected_min is not None
            and self.expected_max is not None
            and self.expected_min > self.expected_max
        ):
            raise ValueError("expected_min cannot be greater than expected_max")

    @property
    def comparison_result(self) -> ComparisonResult:
        """Yalnız karşılaştırma sonucu üretir; arıza bulgusu oluşturmaz."""
        if self.value_kind == "numeric":
            measured = float(self.measured_value)
            if self.expected_min is not None and measured < self.expected_min:
                return "below"
            if self.expected_max is not None and measured > self.expected_max:
                return "above"
            if self.expected_min is not None or self.expected_max is not None:
                return "within"
            if self.expected_nominal is not None:
                return "match" if measured == self.expected_nominal else "mismatch"
            return "unknown"

        if self.expected_text is None:
            return "unknown"
        expected = self.expected_text.strip().lower()
        actual = str(self.measured_value).strip().lower()
        return "match" if actual == expected else "mismatch"

    def deviation_flag(self, tolerance: float = DEFAULT_DEVIATION_TOLERANCE) -> bool | None:
        """Basit tolerans-dışı aritmetik yardım. Kesin arıza göstergesi DEĞİLDİR."""
        if self.expected_nominal is None:
            return None
        if self.value_kind != "numeric":
            return None
        if self.expected_nominal == 0:
            return self.measured_value != 0
        measured = float(self.measured_value)
        relative_gap = abs(measured - self.expected_nominal) / abs(self.expected_nominal)
        return relative_gap > tolerance


# --------------------------------------------------------------------------
# §6.2 Bulgu, kanıt ve güven derecesi
# --------------------------------------------------------------------------

ConfidenceLevel = Literal["low", "medium", "high"]
FindingCreatedBy = Literal["user", "lumos_assist"]
EvidenceKind = Literal["measurement"]  # yalnızca ölçüm; fotoğraf/OCR kanıtı bu fazda yok


@dataclass(frozen=True)
class EvidenceReference:
    kind: EvidenceKind
    ref_id: str


@dataclass
class Finding:
    """Bulgu (bkz. design doc §6.2). En az bir kanıt zorunludur (kanıt sistemi)."""

    case_id: str
    statement: str
    confidence_level: ConfidenceLevel
    evidence: list[EvidenceReference]
    finding_id: str = field(default_factory=new_id)
    created_by: FindingCreatedBy = "user"
    confidence_score: int | None = None
    disclaimer_shown: bool = False
    created_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError(
                "Finding requires at least one evidence reference (kanıt sistemi zorunludur)."
            )
        if self.created_by == "lumos_assist" and not self.disclaimer_shown:
            raise ValueError(
                "lumos_assist findings must set disclaimer_shown=True before creation "
                "('bu kesin teşhis değildir' uyarısı zorunlu)."
            )
        if self.confidence_score is not None and not (0 <= self.confidence_score <= 100):
            raise ValueError("confidence_score must be between 0 and 100")


# --------------------------------------------------------------------------
# §6.3 Yüksek risk uyarısı
# --------------------------------------------------------------------------

RiskCategory = Literal[
    "mains_voltage",
    "capacitor_stored_charge",
    "fire_smoke_smell",
    "battery_swelling",
    "high_current",
    "unknown_high_voltage",
    "other",
]
RiskSeverity = Literal["warn", "high", "critical"]
RiskTriggeredBy = Literal["user_reported_symptom", "keyword_match"]
RiskFlowAction = Literal["continue_after_ack", "restricted_after_ack", "block"]


@dataclass
class RiskFlag:
    """Yüksek risk uyarısı (bkz. design doc §6.3). Asla otomatik bastırılmaz."""

    case_id: str
    risk_category: RiskCategory
    severity: RiskSeverity
    triggered_by: RiskTriggeredBy
    risk_id: str = field(default_factory=new_id)
    required_ack: bool = True
    acknowledged: bool = False
    acknowledged_at: datetime | None = None
    created_at: datetime = field(default_factory=now_utc)

    @property
    def suppressed(self) -> Literal[False]:
        """Her zaman False. Bilinçli olarak set edilemez (NEVER_AUTO E-serisi ile hizalı)."""
        return False

    @property
    def flow_action(self) -> RiskFlowAction:
        return {
            "warn": "continue_after_ack",
            "high": "restricted_after_ack",
            "critical": "block",
        }[self.severity]

    @property
    def allows_flow(self) -> bool:
        """Kritik riskte kullanıcı onayı verilse bile akış açılmaz."""
        if self.flow_action == "block":
            return False
        return not self.required_ack or self.acknowledged

    def acknowledge(self) -> None:
        self.acknowledged = True
        self.acknowledged_at = now_utc()


# --------------------------------------------------------------------------
# §6.5 Ücretli özellik durumu — closed / pilot / validated / paid
# --------------------------------------------------------------------------

PaidFeatureStatus = Literal["closed", "pilot", "validated", "paid"]

PAID_FEATURE_TRANSITIONS: dict[PaidFeatureStatus, tuple[PaidFeatureStatus, ...]] = {
    "closed": ("pilot",),
    "pilot": ("validated",),
    "validated": ("paid",),
    "paid": (),
}


class InvalidPaidFeatureTransition(ValueError):
    """Doğrusal olmayan bir geçiş veya karar kaydı (decision_ref) olmadan
    yapılan bir geçiş denendiğinde fırlatılır."""


@dataclass
class PaidFeatureState:
    """Ücretli özellik durum akışı (bkz. design doc §6.5).

    Geçişler yalnızca doğrusal sırayla (closed -> pilot -> validated -> paid)
    yapılabilir ve her geçiş bir karar kaydı (`decision_ref`, örn. "ADR-017"
    veya "OD-0xx") gerektirir. Hiçbir geçiş otomatik tetiklenmez.
    """

    feature_key: str
    status: PaidFeatureStatus = "closed"
    changed_at: datetime = field(default_factory=now_utc)
    decision_ref: str | None = None
    rollback_reason: str | None = None

    def transition_to(self, new_status: PaidFeatureStatus, decision_ref: str) -> None:
        if not decision_ref:
            raise InvalidPaidFeatureTransition(
                "a decision_ref (e.g. an ADR/OD id) is required for every "
                "paid-feature status transition"
            )
        allowed = PAID_FEATURE_TRANSITIONS.get(self.status, ())
        if new_status not in allowed:
            raise InvalidPaidFeatureTransition(
                f"{self.status} -> {new_status} is not an allowed linear transition "
                f"(allowed: {allowed or 'none — terminal state'})"
            )
        self.status = new_status
        self.decision_ref = decision_ref
        self.rollback_reason = None
        self.changed_at = now_utc()

    def rollback_to(
        self, new_status: PaidFeatureStatus, decision_ref: str, reason: str
    ) -> None:
        """Güvenlik/veri olayı için daha kapalı bir duruma kontrollü dönüş."""
        order: tuple[PaidFeatureStatus, ...] = ("closed", "pilot", "validated", "paid")
        if not decision_ref or not reason:
            raise InvalidPaidFeatureTransition(
                "rollback requires both decision_ref and an audit reason"
            )
        if order.index(new_status) >= order.index(self.status):
            raise InvalidPaidFeatureTransition(
                f"{self.status} -> {new_status} is not a rollback to a more closed state"
            )
        self.status = new_status
        self.decision_ref = decision_ref
        self.rollback_reason = reason
        self.changed_at = now_utc()
