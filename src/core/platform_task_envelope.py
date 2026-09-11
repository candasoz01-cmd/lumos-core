"""Known platform-task envelopes (PR-006).

Not an AI Router (ADR-004) and not an Agent Network (ADR-008).
A chat sentence either matches one frozen catalog row or STOPs.
Unknown platforms are not inferred.

Output fields are the ones existing gates already accept:
Board claim (repo + repo-relative scopes), AGENTS.md work packet,
CU4 ``write_local``, and coordination ``INFORMATION`` + ``user_relevant``.
This module does not claim, spawn an agent, write files, or open a PR.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

# Existing gates — string values only; do not grow a parallel policy.
STEP_WRITE_LOCAL = "write_local"
EVIDENCE_KIND_INFORMATION = "INFORMATION"
STOP_REASON = "STOP"

_IOS_RE = re.compile(r"\b(ios|iphone|ipad|appicon)\b", re.IGNORECASE)
_LOGO_RE = re.compile(
    r"(logo|ikon|icon|işaret|isaret|appicon|chatlumos|chat-lumos|marka)",
    re.IGNORECASE,
)
_QUESTION_RE = re.compile(
    r"\b(neden|niçin|nicin|niye|why|sence|ne\s+dersin|what\s+do\s+you\s+think)\b",
    re.IGNORECASE,
)
_DRIVE_RE = re.compile(r"\b(drive|google\s+drive)\b", re.IGNORECASE)
_GITHUB_ONLY_RE = re.compile(r"\bgithub\b", re.IGNORECASE)

# Fake catalog paths from the lumos-ios architecture draft — not the live tree.
_FAKE_RESOURCES_APPICON = "Resources/Assets.xcassets"
_APPICON_SET_RE = re.compile(
    r"(?:^|[\s\"'`=(])((?:ios/)?(?:[\w./-]+/)*AppIcon\.appiconset)",
    re.IGNORECASE,
)
_SOURCE_MARK_RE = re.compile(
    r"(?:^|[\s\"'`=(])((?:ios/|ui/public/)?[\w./-]*chat-lumos-mark\.svg)",
    re.IGNORECASE,
)

IOS_LUMOS_REPO = "candasoz01-cmd/Lumos"
LUMOS_CORE_SOURCE_MARK = "ui/public/chat-lumos-mark.svg"
IOS_LOGO_PIPELINE_FILES = (
    "ios/README.md",
    "scripts/build_ios_logo_assets.py",
    "scripts/sync_ios_assets.py",
    "Makefile",
)
# AppIcon catalog under ios/ — not Resources/. Used when the private Lumos
# checkout is not readable from this environment (GitHub 404).
_DEFAULT_GENERATED_APPICON = "ios/Assets.xcassets/AppIcon.appiconset"


@dataclass(frozen=True)
class WorkPacket:
    hedef: str
    kapsam: str
    dokunma: str
    kanit: str

    def as_text(self) -> str:
        return (
            f"HEDEF: {self.hedef}\n"
            f"KAPSAM: {self.kapsam}\n"
            f"DOKUNMA: {self.dokunma}\n"
            f"KANIT: {self.kanit}"
        )


@dataclass(frozen=True)
class PlatformTaskEnvelope:
    task_key: str
    repo: str
    scopes: tuple[str, ...]
    forbidden: tuple[str, ...]
    risk_step: str
    confirmation_action_key: str
    evidence_kind: str
    user_relevant: bool
    packet: WorkPacket


@dataclass(frozen=True)
class EnvelopeDecision:
    status: str
    reason: str
    envelope: PlatformTaskEnvelope | None = None

    @property
    def matched(self) -> bool:
        return self.status == "matched" and self.envelope is not None


def _stop(reason: str) -> EnvelopeDecision:
    return EnvelopeDecision(status=STOP_REASON, reason=reason, envelope=None)


def lumos_checkout_root() -> Path | None:
    """Private candasoz01-cmd/Lumos tree, if this environment can see it."""
    candidates: list[Path] = []
    for key in ("LUMOS_IOS_ROOT", "LUMOS_CHECKOUT"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            candidates.append(Path(raw))
    here = Path(__file__).resolve()
    candidates.extend(
        (
            here.parents[2].parent / "Lumos",
            Path.cwd() / "Lumos",
            Path.cwd().parent / "Lumos",
        )
    )
    for root in candidates:
        try:
            if (root / "scripts" / "build_ios_logo_assets.py").is_file():
                return root.resolve()
        except OSError:
            continue
    return None


def _normalize_repo_rel(raw: str) -> str | None:
    cleaned = raw.strip().replace("\\", "/").lstrip("./")
    if not cleaned or cleaned.startswith("/") or ".." in PurePosixPath(cleaned).parts:
        return None
    lowered = cleaned.lower()
    if "apple-touch" in lowered or "launchimage" in lowered or "launch" in lowered:
        return None
    if cleaned.startswith(_FAKE_RESOURCES_APPICON) or cleaned.startswith(
        "Resources/Assets.xcassets/"
    ):
        return None
    return cleaned.rstrip("/")


def parse_ios_logo_scopes_from_lumos(lumos_root: Path) -> tuple[str, ...]:
    """Read AppIcon outputs from the named Lumos pipeline files. Never invent Resources/."""
    found: list[str] = []
    seen: set[str] = set()
    for rel in IOS_LOGO_PIPELINE_FILES:
        path = lumos_root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _APPICON_SET_RE.finditer(text):
            normalized = _normalize_repo_rel(match.group(1))
            if normalized and normalized not in seen:
                seen.add(normalized)
                found.append(normalized)
        for match in _SOURCE_MARK_RE.finditer(text):
            normalized = _normalize_repo_rel(match.group(1))
            if (
                normalized
                and normalized.endswith("chat-lumos-mark.svg")
                and not normalized.startswith("ui/public/")
                and normalized not in seen
            ):
                seen.add(normalized)
                found.append(normalized)
    return tuple(found)


def ios_logo_scopes(*, lumos_root: Path | None = None) -> tuple[str, ...]:
    root = lumos_root if lumos_root is not None else lumos_checkout_root()
    if root is not None:
        parsed = parse_ios_logo_scopes_from_lumos(root)
        if parsed:
            return parsed
    return (_DEFAULT_GENERATED_APPICON,)


def _ios_logo_packet(scopes: tuple[str, ...]) -> WorkPacket:
    scope_list = ", ".join(scopes)
    return WorkPacket(
        hedef="iOS AppIcon işaretini OD-050 ChatLumos'a hizala",
        kapsam=(
            f"Kaynak (lumos-core, bu zarfta yazılmaz): {LUMOS_CORE_SOURCE_MARK}. "
            f"Üretilen AppIcon ({IOS_LUMOS_REPO}): {scope_list}. "
            "Authority: ios/README.md, scripts/build_ios_logo_assets.py, "
            "scripts/sync_ios_assets.py, Makefile. "
            "apple-touch web varlığıdır (ui rel=apple-touch-icon); launch ayrı. "
            "İkisi bu zarfta yok — sonra ayrı platform anahtarı gerekir."
        ),
        dokunma=(
            "Swift, conductor (App/AI), Network, GitHub workflow (.github), "
            "lumos-core, main, açık PR branch'leri, kapsam dışı marka "
            "(lumos-tree-logo, lumos-skull-mark, lumos-logo-mark), "
            "apple-touch, launch, ajan spawn, iOS dosya yazımı bu dilimde yok, "
            "production deploy, merge"
        ),
        kanit=(
            "değişen dosya listesi, AppIcon asset diff; "
            "test yoksa çalıştırılmadı yazılır. Teslim Board'a INFORMATION "
            "+ user_relevant=true olarak düşer; RESULT kullanıcı rotası açılmaz."
        ),
    )


def build_ios_logo_envelope(*, lumos_root: Path | None = None) -> PlatformTaskEnvelope:
    scopes = ios_logo_scopes(lumos_root=lumos_root)
    return PlatformTaskEnvelope(
        task_key="ios-logo",
        repo=IOS_LUMOS_REPO,
        scopes=scopes,
        forbidden=(
            "App",
            "ios/App",
            "App/AI",
            "App/Network",
            "App/UI",
            ".github",
            "src",
            "docs",
            _FAKE_RESOURCES_APPICON,
            "Resources/Assets.xcassets/LaunchImage.imageset",
            "ui/public/lumos-tree-logo.svg",
            "ui/public/lumos-skull-mark.svg",
            "ui/public/lumos-logo-mark.svg",
        ),
        risk_step=STEP_WRITE_LOCAL,
        confirmation_action_key=STEP_WRITE_LOCAL,
        evidence_kind=EVIDENCE_KIND_INFORMATION,
        user_relevant=True,
        packet=_ios_logo_packet(scopes),
    )


IOS_LOGO_ENVELOPE = build_ios_logo_envelope()

CATALOG: Mapping[str, PlatformTaskEnvelope] = {
    IOS_LOGO_ENVELOPE.task_key: IOS_LOGO_ENVELOPE,
}


def resolve_platform_task(user_text: str) -> EnvelopeDecision:
    """Match a chat sentence to one catalog row, or STOP.

    Does not classify general TASK vs CHAT. Unknown or ambiguous input
    is fail-closed STOP so this catalog cannot become a router.
    """
    text = (user_text or "").strip()
    if not text:
        return _stop("empty")
    if _QUESTION_RE.search(text):
        return _stop("question")
    if _DRIVE_RE.search(text) and not _IOS_RE.search(text):
        return _stop("unknown_platform")
    if _GITHUB_ONLY_RE.search(text) and not (_IOS_RE.search(text) and _LOGO_RE.search(text)):
        return _stop("unknown_platform")

    matches: list[PlatformTaskEnvelope] = []
    if _IOS_RE.search(text) and _LOGO_RE.search(text):
        matches.append(IOS_LOGO_ENVELOPE)

    if not matches:
        return _stop("unknown_platform")
    if len(matches) > 1:
        return _stop("ambiguous")
    return EnvelopeDecision(status="matched", reason=matches[0].task_key, envelope=matches[0])


def format_work_packet(envelope: PlatformTaskEnvelope) -> str:
    return envelope.packet.as_text()


def claim_fields(envelope: PlatformTaskEnvelope) -> dict[str, object]:
    """Board claim kwargs. Caller still runs claim_cli / TaskClaimStore."""
    return {
        "task_id": envelope.task_key,
        "repo": envelope.repo,
        "scopes": list(envelope.scopes),
    }


class EnvelopeRejected(ValueError):
    """Proposed paths violate catalog DOKUNMA or allowed scopes."""


def _normalize_repo_path(raw: str) -> str:
    scope = (raw or "").strip().replace("\\", "/")
    path = PurePosixPath(scope)
    if path.is_absolute() or ".." in path.parts:
        raise EnvelopeRejected("kapsam repo-relative olmalı")
    cleaned = str(path).rstrip("/")
    if cleaned in {"", "."}:
        raise EnvelopeRejected("repo kökü kapsam olarak alınamaz")
    return cleaned


def _path_overlap(left: str, right: str) -> bool:
    left_path = PurePosixPath(left)
    right_path = PurePosixPath(right)
    return left_path == right_path or left_path in right_path.parents or right_path in left_path.parents


def _path_within(path: str, root: str) -> bool:
    candidate = PurePosixPath(path)
    base = PurePosixPath(root)
    return candidate == base or base in candidate.parents


def assert_paths_allowed(paths: Sequence[str], envelope: PlatformTaskEnvelope) -> None:
    """Reject DOKUNMA hits or paths outside the envelope scopes."""
    if not paths:
        raise EnvelopeRejected("en az bir yol zorunlu")
    for raw in paths:
        cleaned = _normalize_repo_path(raw)
        if any(_path_overlap(cleaned, forbidden) for forbidden in envelope.forbidden):
            raise EnvelopeRejected(f"DOKUNMA: {cleaned}")
        if not any(_path_within(cleaned, scope) for scope in envelope.scopes):
            raise EnvelopeRejected(f"kapsam dışı: {cleaned}")
