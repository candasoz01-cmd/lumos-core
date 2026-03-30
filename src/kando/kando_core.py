from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskType(str, Enum):
    CODE_CHANGE = "CODE_CHANGE"
    CODE_ANALYSIS = "CODE_ANALYSIS"
    INTEGRATION = "INTEGRATION"
    AUXILIARY = "AUXILIARY"
    UNKNOWN = "UNKNOWN"


class ToolName(str, Enum):
    CLAUDE = "Claude"
    CURSOR = "Cursor"
    CODEX = "Codex"
    DEEPSEEK = "DeepSeek"
    NONE = "None"


@dataclass
class UserRequest:
    raw_text: str
    goal: str = ""
    request: str = ""
    files: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    risk_level: str = "normal"


@dataclass
class RoutedTask:
    task_type: TaskType
    tool: ToolName
    reason: str
    packed_instruction: str
    files: List[str] = field(default_factory=list)


@dataclass
class ToolResult:
    tool: ToolName
    summary: str
    changed_files: List[str] = field(default_factory=list)
    risk: str = "unknown"
    scope_ok: bool = True
    notes: List[str] = field(default_factory=list)


# FIX 1: Robust parser — case-insensitive keys, flexible separator (spaces around colon)
class InputNormalizer:
    # Maps normalized field names to UserRequest attributes
    _FIELD_MAP = {
        "amaç": "goal",
        "amac": "goal",       # accent-free fallback
        "istek": "request",
        "dosya": "files",
        "varsa dosya": "files",
        "kısıt": "constraints",
        "kisit": "constraints",  # accent-free fallback
    }

    def normalize(self, raw_text: str) -> UserRequest:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        request = UserRequest(raw_text=raw_text)

        for line in lines:
            key, _, value = self._split_line(line)
            if key is None:
                continue

            field_name = self._FIELD_MAP.get(key)
            if field_name == "goal":
                request.goal = value
            elif field_name == "request":
                request.request = value
            elif field_name == "files":
                request.files = [item.strip() for item in value.split(",") if item.strip()]
            elif field_name == "constraints":
                request.constraints = [item.strip() for item in value.split(",") if item.strip()]

        if not request.request:
            request.request = raw_text.strip()

        request.risk_level = self._infer_risk(request)
        return request

    def _split_line(self, line: str):
        """Split 'Key : value' into (normalized_key, sep, value). Returns (None, None, None) if no colon."""
        if ":" not in line:
            return None, None, None
        raw_key, _, value = line.partition(":")
        normalized_key = raw_key.strip().lower()
        return normalized_key, ":", value.strip()

    def _infer_risk(self, request: UserRequest) -> str:
        text = f"{request.goal} {request.request} {' '.join(request.constraints)}".lower()
        high_risk_terms = [
            "refactor",
            "migration",
            "delete",
            "architecture",
            "auth",
            "payment",
            "security",
            "database",
            "çok dosya",
        ]
        if any(term in text for term in high_risk_terms):
            return "high"
        return "normal"


# FIX 2: Scoring-based classifier — tallies keyword hits per category, picks the winner
class TaskClassifier:
    _CATEGORY_TERMS: Dict[TaskType, List[str]] = {
        TaskType.INTEGRATION: ["plugin", "skill", "entegrasyon", "api", "repo bağla", "github", "slack", "notion"],
        TaskType.CODE_ANALYSIS: ["analiz", "incele", "neden", "niye", "risk", "açıkla", "ne yapıyor"],
        TaskType.CODE_CHANGE: ["düzelt", "ekle", "kaldır", "değiştir", "temizle", "fix", "implement", "update"],
        TaskType.AUXILIARY: ["alternatif", "taslak", "özet", "fikir"],
    }

    def classify(self, request: UserRequest) -> TaskType:
        text = f"{request.goal} {request.request} {' '.join(request.constraints)}".lower()

        scores: Dict[TaskType, int] = {task_type: 0 for task_type in self._CATEGORY_TERMS}
        for task_type, terms in self._CATEGORY_TERMS.items():
            for term in terms:
                if term in text:
                    scores[task_type] += 1

        # Files present are a strong signal for CODE_CHANGE
        if request.files:
            scores[TaskType.CODE_CHANGE] += 2

        best_type = max(scores, key=lambda t: scores[t])
        if scores[best_type] == 0:
            return TaskType.UNKNOWN
        return best_type


# FIX 3: ToolRouter actually selects Cursor for small-scoped code changes
class ToolRouter:
    def route(self, request: UserRequest, task_type: TaskType) -> RoutedTask:
        if task_type == TaskType.CODE_CHANGE:
            if len(request.files) <= 1 and self._is_small_scoped(request):
                tool = ToolName.CURSOR
                reason = "Dar kapsamlı kod değişikliği için Cursor seçildi."
            else:
                tool = ToolName.CLAUDE
                reason = "Çok dosyalı veya geniş kapsamlı kod değişikliği için Claude seçildi."
        elif task_type == TaskType.CODE_ANALYSIS:
            tool = ToolName.CLAUDE
            reason = "Analiz ve bağlam çözümleme için Claude seçildi."
        elif task_type == TaskType.INTEGRATION:
            tool = ToolName.CODEX
            reason = "Entegrasyon veya dış araç bağlantısı için Codex seçildi."
        elif task_type == TaskType.AUXILIARY:
            tool = ToolName.DEEPSEEK
            reason = "Düşük kritik yardımcı üretim için DeepSeek seçildi."
        else:
            tool = ToolName.CLAUDE
            reason = "Belirsiz görev güvenli varsayılan olarak Claude'a yönlendirildi."

        packed = TaskPacker().pack(request=request, task_type=task_type, tool=tool)
        return RoutedTask(
            task_type=task_type,
            tool=tool,
            reason=reason,
            packed_instruction=packed,
            files=list(request.files),
        )

    def _is_small_scoped(self, request: UserRequest) -> bool:
        text = f"{request.request} {' '.join(request.constraints)}".lower()
        broad_terms = ["refactor", "mimari", "çok dosya", "genel", "tüm proje", "cleanup all"]
        return not any(term in text for term in broad_terms)


class TaskPacker:
    def pack(self, request: UserRequest, task_type: TaskType, tool: ToolName) -> str:
        file_text = ", ".join(request.files) if request.files else "Belirtilmedi"
        constraint_text = "; ".join(request.constraints) if request.constraints else "Scope genişletme yok"

        return (
            f"AMAÇ: {request.goal or 'Belirtilmedi'}\n"
            f"GÖREV TİPİ: {task_type.value}\n"
            f"HEDEF ARAÇ: {tool.value}\n"
            f"İSTEK: {request.request}\n"
            f"DOSYALAR: {file_text}\n"
            f"KISITLAR: {constraint_text}\n"
            f"KURALLAR:\n"
            f"- Sadece istenen işi yap\n"
            f"- Scope büyütme\n"
            f"- Belirsizlik varsa açıkça yaz\n"
            f"- Değişiklik varsa etki/risk belirt\n"
            f"- Çıktıyı sabit formatta ver\n"
        )


class ResultFilter:
    def validate(self, routed_task: RoutedTask, result: ToolResult) -> Dict[str, Any]:
        problems: List[str] = []

        if result.tool != routed_task.tool:
            problems.append("Araç uyumsuzluğu var.")
        if not result.scope_ok:
            problems.append("Scope dışına çıkılmış.")
        if not result.summary.strip():
            problems.append("Özet boş döndü.")

        return {
            "ok": len(problems) == 0,
            "problems": problems,
            "final_output": self._format_final(routed_task, result, problems),
            "final_report": {
                "trace": _build_trace_dict(routed_task, result, problems),
                "execution": _build_execution_dict(result, problems),
            },
        }

    def _format_final(self, routed_task: RoutedTask, result: ToolResult, problems: List[str]) -> str:
        changed = ", ".join(result.changed_files) if result.changed_files else "Yok"
        risk = result.risk or "bilinmiyor"
        notes = "; ".join(result.notes) if result.notes else "Yok"
        status = "GEÇERLİ" if not problems else "İNCELE"
        issues = "; ".join(problems) if problems else "Yok"

        return (
            f"DURUM: {status}\n"
            f"SEÇİLEN ARAÇ: {routed_task.tool.value}\n"
            f"GÖREV: {routed_task.task_type.value}\n"
            f"GEREKÇE: {routed_task.reason}\n"
            f"YAPILAN: {result.summary}\n"
            f"DEĞİŞEN DOSYALAR: {changed}\n"
            f"RİSK: {risk}\n"
            f"NOTLAR: {notes}\n"
            f"SORUNLAR: {issues}"
        )


def parse_llm_output(text: str) -> Dict[str, Any]:
    """Parse a sectioned LLM response into a dict with SUMMARY, CHANGES, RISK, NOTES.

    Expected format:
        SUMMARY:
        ...
        CHANGES:
        ...
        RISK:
        ...
        NOTES:
        ...

    - Missing sections get safe defaults.
    - Never raises.
    """
    defaults: Dict[str, Any] = {
        "summary": "No summary",
        "changes": [],
        "risk": "unknown",
        "notes": [],
    }

    try:
        known_headers = {"SUMMARY", "CHANGES", "RISK", "NOTES"}
        sections: Dict[str, List[str]] = {}
        current: Optional[str] = None

        for line in text.splitlines():
            stripped = line.strip()
            header = stripped.rstrip(":").upper()
            if header in known_headers and stripped.endswith(":"):
                current = header
                sections[current] = []
            elif current is not None:
                sections[current].append(stripped)

        def lines_of(key: str) -> List[str]:
            return [line for line in sections.get(key, []) if line]

        summary_lines = lines_of("SUMMARY")
        return {
            "summary": " ".join(summary_lines) if summary_lines else defaults["summary"],
            "changes": lines_of("CHANGES"),
            "risk": lines_of("RISK")[0] if lines_of("RISK") else defaults["risk"],
            "notes": lines_of("NOTES"),
        }
    except Exception:
        return defaults


_IMPORT_CLEANUP_KEYWORDS = (
    "unused import",
    "unused importları",
    "kullanılmayan import",
    "importları kaldır",
    "sadece importlara dokun",
)

def extract_explicit_target(task: str) -> str | None:
    m = re.search(r"(src/[a-zA-Z0-9_/.\-]+\.py)", task or "")
    return m.group(1) if m else None


def explicit_single_lock_path(text: str) -> str | None:
    """Metinde tam bir adet src/...py yolu varsa onu döndür; birden fazla varsa kilitleme yok."""
    ms = re.findall(r"(src/[a-zA-Z0-9_/.\-]+\.py)", text or "")
    if len(ms) != 1:
        return None
    return ms[0]


def _first_src_py_path_from_text(text: str) -> Optional[str]:
    return extract_explicit_target(text or "")


def _packed_field_after_colon(packed: str, label: str) -> str:
    if label not in packed:
        return ""
    try:
        return packed.split(label, 1)[1].split("\n", 1)[0].strip()
    except IndexError:
        return ""


def _single_dosyalar_path(packed: str) -> Optional[str]:
    line = _packed_field_after_colon(packed, "DOSYALAR:")
    if not line or line == "Belirtilmedi":
        return None
    parts = [p.strip() for p in line.split(",") if p.strip()]
    if len(parts) != 1:
        return None
    return parts[0]


def _resolve_file_path_for_deterministic(routed_task: RoutedTask) -> Optional[str]:
    if len(routed_task.files) == 1:
        p = routed_task.files[0].strip()
        if p.endswith(".py"):
            return p
    hit = _first_src_py_path_from_text(routed_task.packed_instruction)
    if hit:
        return hit
    return _single_dosyalar_path(routed_task.packed_instruction)


def _import_cleanup_keywords_present(text: str) -> bool:
    if not text:
        return False
    tl = text.lower()
    return any(k in tl for k in _IMPORT_CLEANUP_KEYWORDS)


def _normalize_repo_path(p: str) -> str:
    return p.strip().replace("\\", "/").lstrip("./")


def _explicit_single_file_target(routed_task: RoutedTask) -> Optional[str]:
    """Kullanıcı tek dosya verdiyse o yol; aksi halde None (çoklu veya belirsiz → zorlama yok)."""
    if len(routed_task.files) == 1:
        p = _normalize_repo_path(routed_task.files[0])
        if p:
            return p
    line = _packed_field_after_colon(routed_task.packed_instruction, "DOSYALAR:")
    if line and line != "Belirtilmedi":
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if len(parts) == 1:
            return _normalize_repo_path(parts[0])
    lock = explicit_single_lock_path(routed_task.packed_instruction or "")
    if lock:
        return _normalize_repo_path(lock)
    return None


def _change_line_might_be_path(line: str) -> str:
    s = line.strip().lstrip("-").strip()
    if not s:
        return ""
    return s.split()[0]


def _clamp_changed_files_to_target(changed: List[str], target: str) -> List[str]:
    """Yalnızca resolved_target ile eşleşen yolu bırak; diğerlerini at."""
    tn = _normalize_repo_path(target)
    if not changed:
        return []
    for raw in changed:
        cand = _change_line_might_be_path(raw)
        if not cand:
            continue
        cn = _normalize_repo_path(cand)
        if cn == tn or cn.endswith(tn) or tn.endswith(cn):
            return [tn]
    return []


def _trace_hedef_dosya(routed_task: RoutedTask, result: ToolResult) -> str:
    for n in result.notes or []:
        if isinstance(n, str) and n.startswith("selected_target="):
            return n.split("=", 1)[1].strip()
    h = _explicit_single_file_target(routed_task)
    return h if h else "belirtilmedi"


def _build_trace_dict(routed_task: RoutedTask, result: ToolResult, problems: List[str]) -> Dict[str, str]:
    det = any(
        isinstance(n, str) and n.startswith("deterministic apply") for n in (result.notes or [])
    )
    if det:
        arac = "tek dosyalı güvenli düzenleme"
        yurutme = "deterministic apply"
    elif routed_task.tool == ToolName.CURSOR:
        arac = "dar kapsamlı kod değişikliği"
        yurutme = "cursor"
    elif routed_task.tool == ToolName.CLAUDE:
        arac = "analiz ve yorumlama"
        yurutme = "claude"
    else:
        arac = "diğer"
        yurutme = "unknown"

    hedef = _trace_hedef_dosya(routed_task, result)
    ok = len(problems) == 0
    if not ok:
        sonuc = "başarısız"
    elif result.changed_files:
        sonuc = "değişiklik yapıldı"
    else:
        sonuc = "değişiklik yok"

    return {
        "arac_secimi": arac,
        "hedef_dosya": hedef,
        "yurutme_modu": yurutme,
        "sonuc": sonuc,
    }


def _build_execution_dict(result: ToolResult, problems: List[str]) -> Dict[str, Any]:
    """exe.constraints['execution'] ile uyumlu: execution_result + patch sonrası gözlemlenebilir alanlar."""
    ok = len(problems) == 0
    det_failed = any(
        isinstance(n, str) and n == "deterministic apply failed" for n in (result.notes or [])
    )
    if not ok or det_failed:
        msg_parts = list(problems)
        for n in result.notes or []:
            if isinstance(n, str) and n == "deterministic apply failed":
                if result.summary:
                    msg_parts.append(result.summary)
                break
        detail = "; ".join(msg_parts) if msg_parts else (result.summary or "doğrulama veya deterministik uygulama başarısız")
        return {
            "execution_result": "patch_failed",
            "detail": f"patch başarısız: {detail}"[:2000],
        }
    if result.changed_files:
        applied = _normalize_repo_path(result.changed_files[0])
        return {
            "execution_result": "patch_applied",
            "applied_path": applied,
            "detail": (result.summary or f"patch uygulandı: {applied}")[:2000],
        }
    return {
        "execution_result": "no_change",
        "detail": (result.summary or "değişiklik yok")[:2000],
    }


def rollback_patch_from_memory_backup(
    target: str | Path,
    previous_content: str,
    *,
    file_existed_before: bool,
) -> tuple[bool, str]:
    """Patch öncesi bellekte tutulan içeriği diske geri yazar (.bak kullanılmaz)."""
    from kando.cursor_bridge import rollback_patch_file

    return rollback_patch_file(Path(target), previous_content, file_existed_before=file_existed_before)


def _enforce_single_target(routed_task: RoutedTask, result: ToolResult) -> ToolResult:
    t = _explicit_single_file_target(routed_task)
    if not t:
        return result
    cf = _clamp_changed_files_to_target(result.changed_files, t)
    notes = list(result.notes)
    tag = f"selected_target={t}"
    if tag not in notes:
        notes.append(tag)
    return ToolResult(
        tool=result.tool,
        summary=result.summary,
        changed_files=cf,
        risk=result.risk,
        scope_ok=result.scope_ok,
        notes=notes,
    )


class KandoCore:
    def __init__(self) -> None:
        self.normalizer = InputNormalizer()
        self.classifier = TaskClassifier()
        self.router = ToolRouter()
        self.result_filter = ResultFilter()

    def prepare_task(self, raw_text: str) -> Dict[str, Any]:
        request = self.normalizer.normalize(raw_text)
        task_type = self.classifier.classify(request)
        routed = self.router.route(request, task_type)
        return {
            "request": request,
            "routed_task": routed,
        }

    def execute(self, routed_task: RoutedTask) -> ToolResult:
        """Execute the routed task. CLAUDE: LLM; CURSOR: packed instruction for agent; others: defaults."""
        if routed_task.tool == ToolName.CLAUDE:
            # Simulated structured response — in production, replace with call_claude()
            fake_llm_text = (
                "SUMMARY:\n"
                f"Görev tamamlandı: {routed_task.packed_instruction.splitlines()[3]}\n"
                "CHANGES:\n"
                "- İlgili dosyada değişiklik yapıldı\n"
                "RISK:\n"
                "low\n"
                "NOTES:\n"
                "- Scope dışına çıkılmadı\n"
            )
            parsed = parse_llm_output(fake_llm_text)
        elif routed_task.tool == ToolName.CURSOR:
            if routed_task.task_type == TaskType.CODE_CHANGE:
                file_path = _resolve_file_path_for_deterministic(routed_task)
                task_text = _packed_field_after_colon(routed_task.packed_instruction, "İSTEK:")
                kw_text = task_text if task_text else routed_task.packed_instruction
                if (
                    file_path
                    and file_path.endswith(".py")
                    and _import_cleanup_keywords_present(kw_text)
                ):
                    sa_task = task_text if task_text else routed_task.packed_instruction
                    from kando.smart_apply import run_task as smart_apply_run_task

                    sa_out = smart_apply_run_task(file_path, sa_task)
                    ok = bool(sa_out.get("ok"))
                    changed = bool(sa_out.get("changed"))
                    message = str(sa_out.get("message", ""))
                    if not ok:
                        return _enforce_single_target(
                            routed_task,
                            ToolResult(
                                tool=routed_task.tool,
                                summary=message,
                                changed_files=[],
                                risk="medium",
                                scope_ok=True,
                                notes=["deterministic apply failed"],
                            ),
                        )
                    if not changed:
                        return _enforce_single_target(
                            routed_task,
                            ToolResult(
                                tool=routed_task.tool,
                                summary=message,
                                changed_files=[],
                                risk="low",
                                scope_ok=True,
                                notes=["deterministic apply: no change"],
                            ),
                        )
                    return _enforce_single_target(
                        routed_task,
                        ToolResult(
                            tool=routed_task.tool,
                            summary=message,
                            changed_files=[file_path],
                            risk="low",
                            scope_ok=True,
                            notes=["deterministic apply success"],
                        ),
                    )
            try:
                files_line = routed_task.packed_instruction.split("DOSYALAR:")[1].split("\n")[0]
                changed_files = [p.strip() for p in files_line.split(",") if p.strip()]
            except (IndexError, AttributeError):
                changed_files = []
            return _enforce_single_target(
                routed_task,
                ToolResult(
                    tool=routed_task.tool,
                    summary="Cursor için görev oluşturuldu",
                    changed_files=changed_files,
                    risk="low",
                    scope_ok=True,
                    notes=[routed_task.packed_instruction],
                ),
            )
        else:
            parsed = parse_llm_output("")

        return _enforce_single_target(
            routed_task,
            ToolResult(
                tool=routed_task.tool,
                summary=parsed["summary"],
                changed_files=parsed["changes"],
                risk=parsed["risk"],
                scope_ok=True,
                notes=parsed["notes"],
            ),
        )

    def finalize(self, routed_task: RoutedTask, result: ToolResult) -> Dict[str, Any]:
        return self.result_filter.validate(routed_task, result)


if __name__ == "__main__":
    demo = """
    AMAÇ: kod temizliği
    İSTEK: unused importları kaldır
    DOSYA: src/core/runtime_state.py
    KISIT: sadece importlara dokun
    """.strip()

    core = KandoCore()
    prepared = core.prepare_task(demo)
    routed = prepared["routed_task"]

    print("=== ROUTED TASK ===")
    print(routed.packed_instruction)

    result = core.execute(routed)
    final = core.finalize(routed, result)
    print("\n=== FINAL OUTPUT ===")
    print(final["final_output"])
