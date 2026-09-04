"""
Agent Wall gözlem katmanı — Faz-1 testleri.

Sözleşme: `docs/contracts/agent-wall-observation-v1.md`.

Testlerin taşıdığı iddialar:
  * S1/S2/S3 doğru bulguyu üretir, üretmemesi gereken yerde susar.
  * Gözlemci **salt-okunurdur**: claim store'a, agent_status'a, çalışma
    ağacına yazmaz; tek yazma noktası kendi güncesidir.
  * Kanıtsız bulgu kaydedilemez; yollar repo-relative; serbest metin maskeli.
  * Beyan (claim.status alanı dışında agent_status) tespit dayanağı değildir.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lumos_board.task_claim import TaskClaimStore
from lumos_board.wall_observer import (
    OBSERVATION_SCHEMA,
    SIGNAL_FOREIGN_SCOPE,
    SIGNAL_OUT_OF_SCOPE,
    SIGNAL_SILENT_DRIFT,
    SIGNAL_STALE_CLAIM,
    Observation,
    observe,
    observe_drift,
    observe_rhythm,
    observe_scope,
    touched_paths,
    write_observations,
)

NOW = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)


def _store(tmp_path: Path, *, clock=None) -> TaskClaimStore:
    return TaskClaimStore(tmp_path / "board", clock=clock or (lambda: NOW))


def _claim(store: TaskClaimStore, **kw):
    params = {
        "task_id": "TD-99",
        "repo": "lumos-core",
        "branch": "codex/x",
        "worktree": "/tmp/does-not-exist",
        "owner": "agent-a",
        "scopes": ["src/lumos_board"],
        "ttl_seconds": 1800,
    }
    params.update(kw)
    result = store.claim(**params)
    assert result.accepted, result.conflicts
    return result.claim


# --- S1: kapsam dışı dokunuş -------------------------------------------------

def test_paths_inside_scope_produce_nothing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store)
    found = observe_scope(
        claim, ["src/lumos_board/wall_observer.py"], other_active=[claim], now=NOW
    )
    assert found == []


def test_path_outside_every_claim_is_out_of_scope(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store)
    found = observe_scope(claim, ["panel/scripts/panel_tasks_server.py"], other_active=[claim], now=NOW)
    assert [o.signal for o in found] == [SIGNAL_OUT_OF_SCOPE]
    assert found[0].evidence["paths"] == ["panel/scripts/panel_tasks_server.py"]
    assert found[0].evidence["declared_scopes"] == ["src/lumos_board"]


def test_path_owned_by_another_active_claim_is_foreign_scope(tmp_path: Path) -> None:
    """Anayasa §3 adayı: başkasının kapsamına yazma. OUT_OF_SCOPE'tan ağırdır."""
    store = _store(tmp_path)
    mine = _claim(store)
    theirs = _claim(
        store, task_id="TD-98", owner="agent-b", branch="codex/y", scopes=["panel/scripts"]
    )
    found = observe_scope(
        mine, ["panel/scripts/panel_tasks_server.py"], other_active=[mine, theirs], now=NOW
    )
    assert [o.signal for o in found] == [SIGNAL_FOREIGN_SCOPE]
    assert found[0].evidence["owned_by"] == "agent-b"
    assert found[0].evidence["owned_by_claim_id"] == theirs.claim_id


def test_foreign_and_orphan_paths_are_reported_separately(tmp_path: Path) -> None:
    store = _store(tmp_path)
    mine = _claim(store)
    theirs = _claim(store, task_id="TD-98", owner="agent-b", branch="codex/y", scopes=["panel/scripts"])
    found = observe_scope(
        mine,
        ["panel/scripts/panel_tasks_server.py", "docs/ROADMAP.md"],
        other_active=[mine, theirs],
        now=NOW,
    )
    by_signal = {o.signal: o for o in found}
    assert set(by_signal) == {SIGNAL_FOREIGN_SCOPE, SIGNAL_OUT_OF_SCOPE}
    assert by_signal[SIGNAL_OUT_OF_SCOPE].evidence["paths"] == ["docs/ROADMAP.md"]


def test_subdirectory_of_declared_scope_counts_as_inside(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store, scopes=["src"])
    assert observe_scope(claim, ["src/lumos_board/deep/file.py"], other_active=[claim], now=NOW) == []


# --- S2: sessiz sapma --------------------------------------------------------

def test_scattered_touches_are_not_drift(tmp_path: Path) -> None:
    """Dağınık tek tük dokunuş sapma değildir — yalnız kümelenme sapmadır."""
    store = _store(tmp_path)
    claim = _claim(store)
    assert observe_drift(claim, ["docs/a.md", "ui/b.ts"], now=NOW) == []


def test_clustered_outside_touches_are_silent_drift(tmp_path: Path) -> None:
    """
    Gerçek örnek deseni: claim bir işi söylerken dosyalar başka bir işi
    anlatıyor (TD-29 / PR #827, `claude/console-lock-ast`).
    """
    store = _store(tmp_path)
    claim = _claim(store, task_id="TD-CONSOLE-LOCK")
    found = observe_drift(
        claim,
        [
            "ops/retention/install-retention-sweeper.sh",
            "ops/retention/sweep.plist.template",
            "ops/retention/notes.md",
        ],
        now=NOW,
    )
    assert [o.signal for o in found] == [SIGNAL_SILENT_DRIFT]
    assert found[0].evidence["cluster_root"] == "ops/retention"
    assert found[0].evidence["outside_total"] == 3


def test_drift_ignores_paths_inside_the_claim(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store, scopes=["ops/retention"])
    assert (
        observe_drift(
            claim,
            [
                "ops/retention/install-retention-sweeper.sh",
                "ops/retention/sweep.plist.template",
                "ops/retention/notes.md",
            ],
            now=NOW,
        )
        == []
    )


# --- S3: ritim / asılı claim -------------------------------------------------

def test_healthy_claim_has_no_rhythm_finding(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store)
    assert observe_rhythm(claim, last_event_at=NOW - timedelta(minutes=5), now=NOW) == []


def test_expired_but_active_claim_is_reported(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store, ttl_seconds=60)
    later = NOW + timedelta(hours=1)
    found = observe_rhythm(claim, last_event_at=NOW, now=later)
    assert [o.signal for o in found] == [SIGNAL_STALE_CLAIM]
    assert "ttl_expired_but_active" in found[0].evidence["reasons"]


def test_long_silence_is_reported_with_measured_gap(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store, ttl_seconds=86400)
    later = NOW + timedelta(hours=9)
    found = observe_rhythm(claim, last_event_at=NOW, now=later)
    assert "no_events_since_threshold" in found[0].evidence["reasons"]
    assert found[0].evidence["silent_for_seconds"] == 9 * 3600


# --- Sözleşme uyumu: salt-okunurluk ------------------------------------------

def test_observe_writes_nothing_anywhere(tmp_path: Path) -> None:
    """
    Sözleşme §4 kural 4: gözlemci claim store'a, agent_status'a veya
    çalışma ağacına yazmaz. Tur öncesi/sonrası dosya parmak izi aynı olmalı.
    """
    store = _store(tmp_path)
    claim = _claim(store)

    def fingerprint() -> dict[str, tuple[int, float]]:
        return {
            str(p.relative_to(tmp_path)): (p.stat().st_size, p.stat().st_mtime)
            for p in sorted(tmp_path.rglob("*"))
            if p.is_file()
        }

    before = fingerprint()
    run = observe(store.store_dir, worktree_paths={claim.claim_id: ["docs/ROADMAP.md"]}, now=NOW)
    after = fingerprint()

    assert run.observations, "bulgu üretilmeliydi"
    assert before == after, "gözlem turu hiçbir dosyayı değiştirmemeli"


def test_observe_uses_declared_status_only_as_context(tmp_path: Path) -> None:
    """
    Güven modeli (§1): tespit türetilmiş kaynaklara dayanır. Üretilen her
    bulgunun `derived_from` listesi beyan kaynağı içermez.
    """
    store = _store(tmp_path)
    claim = _claim(store)
    run = observe(store.store_dir, worktree_paths={claim.claim_id: ["docs/ROADMAP.md"]}, now=NOW)
    for observation in run.observations:
        assert "agent_status" not in observation.derived_from


# --- Sözleşme uyumu: günce ---------------------------------------------------

def test_record_without_evidence_is_refused() -> None:
    """§4 kural 5: kanıtsız bulgu kaydedilmez."""
    bare = Observation(
        signal=SIGNAL_OUT_OF_SCOPE,
        claim_id="c1",
        task_id="TD-1",
        repo="lumos-core",
        owner="agent-a",
        evidence={},
        derived_from=("git",),
        at=NOW,
    )
    with pytest.raises(ValueError):
        bare.to_record()


def test_write_appends_and_never_rewrites(tmp_path: Path) -> None:
    """§4 kural 1: append-only."""
    store = _store(tmp_path)
    claim = _claim(store)
    log = tmp_path / "logs" / "wall_observations.jsonl"

    first = observe(store.store_dir, worktree_paths={claim.claim_id: ["docs/ROADMAP.md"]}, now=NOW)
    assert write_observations(log, first.observations) == len(first.observations)
    after_first = log.read_text(encoding="utf-8")

    second = observe(store.store_dir, worktree_paths={claim.claim_id: ["ui/x.ts"]}, now=NOW)
    write_observations(log, second.observations)
    after_second = log.read_text(encoding="utf-8")

    assert after_second.startswith(after_first), "önceki satırlar korunmalı"
    rows = [json.loads(line) for line in after_second.splitlines() if line.strip()]
    assert all(row["schema"] == OBSERVATION_SCHEMA for row in rows)
    assert all(row["evidence"] for row in rows)


def test_absolute_and_escaping_paths_are_dropped(tmp_path: Path) -> None:
    """§4 kural 2: mutlak yol ve makine yolu kaydedilmez."""
    store = _store(tmp_path)
    claim = _claim(store)
    run = observe(
        store.store_dir,
        worktree_paths={claim.claim_id: ["/Users/someone/secret.txt", "../outside.txt", "docs/ok.md"]},
        now=NOW,
    )
    recorded = {p for o in run.observations for p in o.evidence.get("paths", [])}
    assert recorded == {"docs/ok.md"}


def test_touched_paths_on_missing_worktree_is_empty(tmp_path: Path) -> None:
    assert touched_paths(tmp_path / "yok") == ()


def test_observer_never_reaches_the_claim_store_api() -> None:
    """
    Yapısal kilit: `TaskClaimStore.list_claims()` okuma niyetiyle çağrılsa
    bile `_write_state` çalıştırır ve exclusive flock tutar — yani hem
    `claims.json`'a yazar hem çalışan ajanların claim kapısını kilitler.
    Gözlemci bu API'ye hiç dokunmamalı; deposu doğrudan, kilitsiz okunur.

    Bu test AST üzerinden bakar: adın yalnız açıklama metninde geçmesi
    serbest, çalışan kodda geçmesi değil.
    """
    import ast

    source = Path("src/lumos_board/wall_observer.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"list_claims", "TaskClaimStore"}
    used: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        name = getattr(node, "attr", None) or getattr(node, "id", None)
        if isinstance(node, (ast.Attribute, ast.Name)) and name in forbidden:
            used.append((name, node.lineno))
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            used.extend((a.name, node.lineno) for a in node.names if a.name in forbidden)
    assert used == [], f"gözlemci claim store API'sine dokunuyor: {used}"
