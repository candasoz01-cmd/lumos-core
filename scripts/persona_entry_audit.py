#!/usr/bin/env python3
"""Read-only audit for Lumos-outside Kando/Cando entry surfaces.

This module only reads and analyzes repository files; it never mutates state.
Security checkpoint plan: docs/lumos-persona-security-checkpoint.md
Entry surface classes (5 categories): docs/lumos-persona-bypass-entry-inventory.md

Heuristics (summary):
- bridge_gateway: kando_bridge POST handlers without run_lumos_gate / _complete_through_gate
  on the execution path; panel HTTP task mutations; auxiliary relay HTTP scripts.
- cli_task_engine: TaskEngine or brain.run usage under src/ without lumos_gate import.
- cando_recipe: scripts/cando_local.py and src/cando direct invocation surfaces.
- offline_push: panel offline-cache / reconnect task-source patterns; relay send scripts.
- secret_signature: HTTP handlers reachable without bridge secret checks; optional-token paths.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

# Public inventory labels (docs/lumos-persona-bypass-entry-inventory.md).
CATEGORIES: tuple[str, ...] = (
    "bridge_gateway",
    "cli_task_engine",
    "cando_recipe",
    "offline_push",
    "secret_signature",
)

GATE_MARKERS: tuple[str, ...] = ("run_lumos_gate", "_complete_through_gate")

BRIDGE_POST_HANDLERS: tuple[tuple[str, str], ...] = (
    ("/controlled", "_handle_controlled"),
    ("/agent-run", "_handle_agent_run"),
    ("/approve", "_handle_approve"),
    ("/replay", "_handle_replay"),
    ("/chat", "_handle_chat"),
    ("/task", "do_POST"),
)

GATE_PIPELINE_ALLOWLIST: tuple[str, ...] = (
    "packages/kando_runtime/src/kando_runtime/lumos_gate.py",
    "packages/kando_runtime/src/kando_runtime/executor_gate.py",
    "src/kando/agent_runner.py",
    "src/kando/cursor_bridge.py",
)

AGENT_BRIDGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bfrom\s+kando\.agent_runner\b"),
    re.compile(r"\bimport\s+kando\.agent_runner\b"),
    re.compile(r"\bfrom\s+kando\.cursor_bridge\b"),
    re.compile(r"\bfrom\s+kando\s+import\s+cursor_bridge\b"),
    re.compile(r"\bimport\s+kando\.cursor_bridge\b"),
)

OFFLINE_PUSH_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"offline-cache|OFFLINE_CACHE"), "offline task source / cache fallback"),
    (re.compile(r"local_chat_relay|post_relay|relay_agent"), "relay send path to bridge"),
    (re.compile(r"kando_send\.py"), "CLI client posts tasks to bridge"),
)

SECRET_SURFACE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'do_GET.*\n(?:.*\n){0,80}?/health'), "GET /health without secret gate"),
    (re.compile(r"_check_secret\(\)\s*\n\s*return\s+True"), "secret check always passes"),
    (re.compile(r"KANDO_BRIDGE_SECRET|X-Kando-Token"), "env/header token surface"),
    (re.compile(r'_task_actions_gate.*enabled:\s*True'), "panel task action gate disabled"),
)


@dataclass(frozen=True)
class Finding:
    category: str
    heuristic: str
    path: str
    line: int | None
    detail: str


@dataclass
class AuditReport:
    repo_root: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def category_counts(self) -> dict[str, int]:
        counts = Counter(f.category for f in self.findings)
        return {cat: int(counts.get(cat, 0)) for cat in CATEGORIES}

    @property
    def total(self) -> int:
        return len(self.findings)


def find_repo_root(start: Path | None = None) -> Path:
    """Locate lumos-core root from a starting path."""
    here = (start or Path(__file__).resolve()).resolve()
    for candidate in (here, *here.parents):
        marker = candidate / "pyproject.toml"
        if marker.is_file() and "lumos-core" in marker.read_text(encoding="utf-8"):
            return candidate
    raise RuntimeError("lumos-core repository root not found")


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _extract_method_body(source: str, method_name: str) -> tuple[str, int] | None:
    match = re.search(rf"^    def {re.escape(method_name)}\(", source, re.MULTILINE)
    if not match:
        return None
    start = match.start()
    start_line = _line_number(source, start)
    tail = source[match.end() :]
    next_def = re.search(r"^    def ", tail, re.MULTILINE)
    body = tail[: next_def.start()] if next_def else tail
    return body, start_line


def _add(
    findings: list[Finding],
    *,
    category: str,
    heuristic: str,
    path: Path,
    repo_root: Path,
    line: int | None,
    detail: str,
) -> None:
    findings.append(
        Finding(
            category=category,
            heuristic=heuristic,
            path=_rel(repo_root, path),
            line=line,
            detail=detail,
        )
    )


def _scan_bridge_handlers(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    bridge = repo_root / "packages/kando_bridge/src/kando_bridge/server.py"
    if not bridge.is_file():
        return findings
    source = _read_text(bridge)

    if "importlib.import_module(\"kando.agent_runner\")" in source:
        idx = source.index("importlib.import_module(\"kando.agent_runner\")")
        _add(
            findings,
            category="bridge_gateway",
            heuristic="bridge_module_level_agent_runner",
            path=bridge,
            repo_root=repo_root,
            line=_line_number(source, idx),
            detail="Bridge loads agent_runner at import time (outside gate pipeline).",
        )

    for route, handler in BRIDGE_POST_HANDLERS:
        if handler == "do_POST":
            match = re.search(r"def do_POST\(self\)", source)
            if not match:
                continue
            body = source[match.start() :]
            next_cls = re.search(r"\nclass ", body)
            body = body[: next_cls.start()] if next_cls else body
            start_line = _line_number(source, match.start())
        else:
            extracted = _extract_method_body(source, handler)
            if extracted is None:
                continue
            body, start_line = extracted

        has_gate = any(marker in body for marker in GATE_MARKERS)
        if not has_gate:
            _add(
                findings,
                category="bridge_gateway",
                heuristic="bridge_post_handler_without_gate",
                path=bridge,
                repo_root=repo_root,
                line=start_line,
                detail=f"POST {route} handler lacks run_lumos_gate / _complete_through_gate.",
            )

        if handler == "_handle_chat" and "simple_chat_task" in body:
            idx = body.index("simple_chat_task")
            _add(
                findings,
                category="bridge_gateway",
                heuristic="bridge_chat_simple_task_shortcut",
                path=bridge,
                repo_root=repo_root,
                line=start_line + body[:idx].count("\n"),
                detail="POST /chat can invoke simple_chat_task before lumos gate pipeline.",
            )

    panel = repo_root / "panel/scripts/panel_tasks_server.py"
    if panel.is_file():
        panel_src = _read_text(panel)
        if "run_lumos_gate" not in panel_src and "def do_POST" in panel_src:
            idx = panel_src.index("def do_POST")
            _add(
                findings,
                category="bridge_gateway",
                heuristic="panel_tasks_post_without_lumos_gate",
                path=panel,
                repo_root=repo_root,
                line=_line_number(panel_src, idx),
                detail="Panel tasks server mutates task state over HTTP without lumos_gate.",
            )

    relay = repo_root / "scripts/relay_agent.py"
    if relay.is_file() and "run_lumos_gate" not in _read_text(relay):
        _add(
            findings,
            category="bridge_gateway",
            heuristic="relay_http_without_gate",
            path=relay,
            repo_root=repo_root,
            line=1,
            detail="Relay agent exposes HTTP POST forwarding without lumos gate.",
        )

    return findings


def _scan_cli_task_engine(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    candidates = (
        repo_root / "src/cli/cli_tasks_mutation.py",
        repo_root / "src/core/brain.py",
        repo_root / "src/core/lumos_runtime.py",
    )
    for path in candidates:
        if not path.is_file():
            continue
        source = _read_text(path)
        if "TaskEngine" not in source and "brain_run" not in source and "brain.run" not in source:
            continue
        if "run_lumos_gate" in source or "lumos_gate" in source:
            continue
        idx = source.find("TaskEngine")
        if idx < 0:
            idx = source.find("brain.run")
        if idx < 0:
            idx = source.find("brain_run")
        _add(
            findings,
            category="cli_task_engine",
            heuristic="cli_task_engine_without_lumos_gate",
            path=path,
            repo_root=repo_root,
            line=_line_number(source, idx) if idx >= 0 else None,
            detail="TaskEngine/brain path without lumos_gate reference in module.",
        )
    return findings


def _scan_cando_surfaces(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    cando_local = repo_root / "scripts/cando_local.py"
    if cando_local.is_file():
        source = _read_text(cando_local)
        if "run_lumos_gate" not in source:
            _add(
                findings,
                category="cando_recipe",
                heuristic="cando_local_entry_script",
                path=cando_local,
                repo_root=repo_root,
                line=1,
                detail="cando_local.py invokes Cando recipes without lumos channel validation.",
            )

    cando_dir = repo_root / "src/cando"
    if cando_dir.is_dir():
        for path in sorted(cando_dir.glob("*.py")):
            if path.name == "__init__.py":
                continue
            source = _read_text(path)
            if "__main__" in source or "run_review" in source or "run_check" in source:
                _add(
                    findings,
                    category="cando_recipe",
                    heuristic="cando_module_direct_surface",
                    path=path,
                    repo_root=repo_root,
                    line=1,
                    detail="Cando recipe module callable without lumos gate contract.",
                )
    return findings


def _is_test_path(rel: str) -> bool:
    parts = rel.split("/")
    if "tests" in parts:
        return True
    name = parts[-1]
    return name.startswith("test_") or name.endswith("_test.py")


def _scan_agent_bridge_direct(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    scan_roots = (
        repo_root / "src",
        repo_root / "packages",
        repo_root / "scripts",
        repo_root / "panel/scripts",
    )
    for root in scan_roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            rel = _rel(repo_root, path)
            if _is_test_path(rel):
                continue
            if rel in GATE_PIPELINE_ALLOWLIST:
                continue
            try:
                source = _read_text(path)
            except OSError:
                continue
            if "run_lumos_gate" in source and rel.endswith("lumos_gate.py"):
                continue
            for pattern in AGENT_BRIDGE_PATTERNS:
                for match in pattern.finditer(source):
                    _add(
                        findings,
                        category="bridge_gateway",
                        heuristic="direct_agent_or_bridge_import",
                        path=path,
                        repo_root=repo_root,
                        line=_line_number(source, match.start()),
                        detail="Direct agent_runner/cursor_bridge import outside gate modules.",
                    )
                    break
    return findings


def _scan_offline_push(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    targets = (
        repo_root / "panel/js/app.js",
        repo_root / "scripts/local_chat_relay.py",
        repo_root / "scripts/kando_send.py",
    )
    for path in targets:
        if not path.is_file():
            continue
        source = _read_text(path)
        for pattern, label in OFFLINE_PUSH_PATTERNS:
            if pattern.search(source):
                _add(
                    findings,
                    category="offline_push",
                    heuristic="offline_or_relay_send_candidate",
                    path=path,
                    repo_root=repo_root,
                    line=1,
                    detail=label,
                )
                break
    return findings


def _scan_secret_surfaces(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    targets = (
        repo_root / "packages/kando_bridge/src/kando_bridge/server.py",
        repo_root / "panel/scripts/panel_tasks_server.py",
        repo_root / "scripts/kando_send.py",
    )
    for path in targets:
        if not path.is_file():
            continue
        source = _read_text(path)
        for pattern, label in SECRET_SURFACE_PATTERNS:
            match = pattern.search(source)
            if match:
                _add(
                    findings,
                    category="secret_signature",
                    heuristic="secret_or_auth_surface",
                    path=path,
                    repo_root=repo_root,
                    line=_line_number(source, match.start()),
                    detail=label,
                )
    return findings


def _dedupe(findings: Iterable[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, str, int | None, str]] = set()
    out: list[Finding] = []
    for f in findings:
        key = (f.category, f.heuristic, f.path, f.line, f.detail)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return sorted(out, key=lambda x: (x.category, x.path, x.line or 0, x.heuristic))


def run_audit(repo_root: Path | None = None) -> AuditReport:
    """Run all read-only heuristics and return structured findings."""
    root = (repo_root or find_repo_root()).resolve()
    findings: list[Finding] = []
    findings.extend(_scan_bridge_handlers(root))
    findings.extend(_scan_cli_task_engine(root))
    findings.extend(_scan_cando_surfaces(root))
    findings.extend(_scan_agent_bridge_direct(root))
    findings.extend(_scan_offline_push(root))
    findings.extend(_scan_secret_surfaces(root))
    return AuditReport(repo_root=str(root), findings=_dedupe(findings))


def format_summary(report: AuditReport) -> str:
    """Human-readable stdout summary with per-category counts."""
    lines = [
        "Lumos persona entry audit (read-only)",
        f"repo: {report.repo_root}",
        f"total findings: {report.total}",
        "",
        "category counts:",
    ]
    for cat in CATEGORIES:
        lines.append(f"  {cat}: {report.category_counts[cat]}")
    lines.append("")
    lines.append("findings:")
    for f in report.findings:
        loc = f"{f.path}:{f.line}" if f.line else f.path
        lines.append(f"  [{f.category}] {loc} — {f.heuristic}: {f.detail}")
    return "\n".join(lines)


def report_to_json(report: AuditReport) -> str:
    payload = {
        "repo_root": report.repo_root,
        "total": report.total,
        "category_counts": report.category_counts,
        "findings": [asdict(f) for f in report.findings],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Lumos persona entry audit")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: auto-detect from script location)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text summary")
    args = parser.parse_args(argv)
    report = run_audit(args.repo_root)
    if args.json:
        print(report_to_json(report))
    else:
        print(format_summary(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
