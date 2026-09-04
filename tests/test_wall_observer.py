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
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lumos_board.task_claim import TaskClaimStore
from lumos_board.wall_observer import (
    OBSERVATION_SCHEMA,
    REASON_MISSING,
    REASON_NOT_A_DIR,
    REASON_NO_ROOT,
    REASON_OUTSIDE,
    SIGNAL_FOREIGN_SCOPE,
    SIGNAL_OUT_OF_SCOPE,
    SIGNAL_SILENT_DRIFT,
    SIGNAL_STALE_CLAIM,
    Observation,
    _git_env,
    inspect_decision,
    observe,
    observe_drift,
    observe_rhythm,
    observe_scope,
    resolve_inspectable_worktree,
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
    assert touched_paths(tmp_path / "yok", allowed_roots=[tmp_path]) == ()


# --- Gerçek git deposu: porcelain biçim regresyonları -------------------------
#
# Bu bloğun sebebi: ilk sürümde `touched_paths` satırı önce strip'leyip sonra
# `[3:]` alıyordu. Unstaged satırlar boşlukla başladığı için (` M path`) yolun
# ilk iki karakteri yeniyordu — hayalet yol üretiyor, kapsam içi dosyayı
# kapsam dışı gösteriyordu. Testler o yolu hiç koşmadığı için fark edilmedi;
# Bugbot yakaladı (#832). Artık gerçek bir depo kurulup dört durum biçimi de
# koşuluyor.

def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=str(repo), check=True, capture_output=True, text=True
    )


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    _git(repo.parent, "init", "-q", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")
    (repo / "src" / "base.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "src" / "renamed.py").write_text("y = 2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    return repo


def test_unstaged_change_path_is_read_whole(git_repo: Path) -> None:
    """` M path` — baştaki boşluk anlamlı; yolun ilk karakterleri yenmemeli."""
    (git_repo / "src" / "base.py").write_text("x = 2\n", encoding="utf-8")
    found = touched_paths(git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD")
    assert "src/base.py" in found
    assert not any(p.endswith("rc/base.py") and p != "src/base.py" for p in found)


def test_staged_change_path_is_read_whole(git_repo: Path) -> None:
    (git_repo / "src" / "base.py").write_text("x = 3\n", encoding="utf-8")
    _git(git_repo, "add", "src/base.py")
    assert "src/base.py" in touched_paths(git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD")


def test_untracked_path_is_read_whole(git_repo: Path) -> None:
    (git_repo / "src" / "brand_new.py").write_text("z = 1\n", encoding="utf-8")
    assert "src/brand_new.py" in touched_paths(git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD")


def test_rename_reports_both_sides(git_repo: Path) -> None:
    """`-z` kipinde rename iki ayrı kayıt: yeni yol, sonra eski yol."""
    _git(git_repo, "mv", "src/renamed.py", "src/moved.py")
    found = touched_paths(git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD")
    assert "src/moved.py" in found
    assert "src/renamed.py" in found


def test_path_with_space_survives(git_repo: Path) -> None:
    """`-z` kullanıldığı için git yolu tırnaklamaz; boşluk bozulmamalı."""
    (git_repo / "src" / "iki kelime.py").write_text("q = 1\n", encoding="utf-8")
    assert "src/iki kelime.py" in touched_paths(git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD")


def test_clean_worktree_reports_nothing(git_repo: Path) -> None:
    assert touched_paths(git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD") == ()


# --- Bugbot #3: sığ yollar da kümelenmeli ------------------------------------

def test_shallow_paths_under_one_directory_form_a_cluster(tmp_path: Path) -> None:
    """
    `docs/a.md` gibi doğrudan bir klasörün altındaki dosyalar da kümelenir.
    Önceki bucket ölçütü (`parts[:2]`) dosyanın kendisini bucket yapıyordu,
    bu yüzden bu şekil asla eşiğe ulaşmıyordu.
    """
    store = _store(tmp_path)
    claim = _claim(store)
    found = observe_drift(claim, ["docs/a.md", "docs/b.md", "docs/c.md"], now=NOW)
    assert [o.signal for o in found] == [SIGNAL_SILENT_DRIFT]
    assert found[0].evidence["cluster_root"] == "docs"


def test_paths_in_different_directories_still_do_not_cluster(tmp_path: Path) -> None:
    store = _store(tmp_path)
    claim = _claim(store)
    assert observe_drift(claim, ["docs/a.md", "ui/b.ts", "api/c.js"], now=NOW) == []


# --- Bugbot #2: FOREIGN_SCOPE repo sınırına saygı duymalı --------------------

def test_other_repo_claim_does_not_make_a_touch_foreign(tmp_path: Path) -> None:
    """
    Paylaşılan board: başka bir REPO aynı repo-relative kapsamı claim etmiş
    olabilir. Bu, bizim repomuzda ihlal değildir.
    """
    store = _store(tmp_path)
    mine = _claim(store, repo="lumos-core", scopes=["src/lumos_board"])
    other_repo = _claim(
        store,
        task_id="TD-97",
        repo="baska-repo",
        owner="agent-c",
        branch="codex/z",
        scopes=["docs"],
    )
    found = observe_scope(mine, ["docs/ROADMAP.md"], other_active=[mine, other_repo], now=NOW)
    assert [o.signal for o in found] == [SIGNAL_OUT_OF_SCOPE], "farklı repo FOREIGN_SCOPE olmamalı"


# --- Bugbot #4: güvenilmeyen claim verisi yürütme bağlamı SEÇEMEZ ------------
#
# Güvenlik özelliği, tek cümleyle:
#   Untrusted claim metadata can select data to inspect only inside an
#   operator-approved root; it can never select executable context.
#
# `TaskClaim.worktree` self-asserted'dır. Gözlemci o dizinde git çalıştırdığı
# için orası tespit değil YÜRÜTME BAĞLAMI seçimidir. Git, çalıştığı deponun
# `.git/config`'ini okur ve `core.fsmonitor` / `diff.external` gibi anahtarlar
# komut çalıştırır — yani jail olmadan claim sahibi gözlemcinin sürecinde kod
# koşturabilirdi (confused deputy).

def _plant_hostile_repo(root: Path, marker: Path) -> Path:
    """`.git/config`'ine komut çalıştıran anahtarlar ekilmiş depo."""
    repo = root / "hostile"
    repo.mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "t@e.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / "file.txt").write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")

    payload = root / "payload.sh"
    payload.write_text(f"#!/bin/sh\ntouch {marker}\nexit 0\n", encoding="utf-8")
    payload.chmod(0o755)

    # Repo-local config: gözlemci burada git koşarsa bunlar tetiklenir.
    _git(repo, "config", "core.fsmonitor", str(payload))
    _git(repo, "config", "diff.external", str(payload))

    (repo / "file.txt").write_text("v2\n", encoding="utf-8")  # kirli ağaç
    return repo


def test_hostile_repo_config_never_executes(tmp_path: Path) -> None:
    """Ekilmiş `core.fsmonitor`/`diff.external` marker dosyası YARATAMAMALI."""
    marker = tmp_path / "PWNED"
    repo = _plant_hostile_repo(tmp_path, marker)

    touched_paths(repo, allowed_roots=[tmp_path], base_ref="HEAD")

    assert not marker.exists(), "ekilmiş git config komutu çalıştı — jail/sertleştirme delik"


def test_worktree_outside_allowed_root_is_never_inspected(tmp_path: Path) -> None:
    """Kök dışı yol: git hiç çağrılmaz, sonuç boş."""
    marker = tmp_path / "PWNED_OUTSIDE"
    outside = tmp_path / "outside"
    outside.mkdir()
    repo = _plant_hostile_repo(outside, marker)
    approved = tmp_path / "approved"
    approved.mkdir()

    assert touched_paths(repo, allowed_roots=[approved], base_ref="HEAD") == ()
    assert not marker.exists()


def test_symlink_escape_from_allowed_root_is_refused(tmp_path: Path) -> None:
    """Onaylı kökün içinden dışarı gösteren symlink kabul edilmez."""
    outside = tmp_path / "outside"
    outside.mkdir()
    repo = _plant_hostile_repo(outside, tmp_path / "PWNED_SYMLINK")
    approved = tmp_path / "approved"
    approved.mkdir()
    (approved / "link").symlink_to(repo, target_is_directory=True)

    assert resolve_inspectable_worktree(approved / "link", [approved]) is None


@pytest.mark.parametrize(
    "roots",
    [(), (None,)],
    ids=["no-roots", "unresolvable-root"],
)
def test_no_approved_root_means_nothing_is_inspectable(git_repo: Path, roots) -> None:
    """Fail-closed: onaylı kök yoksa hiçbir yol kabul edilmez."""
    cleaned = tuple(r for r in roots if r is not None)
    assert resolve_inspectable_worktree(git_repo, cleaned) is None


def test_a_bare_string_root_is_one_root_not_its_characters(tmp_path: Path) -> None:
    """
    Tek bir `str` de geçerli bir Sequence'tır. Üzerinde dönmek karakterleri
    verir ve baştaki `"/"` kök sanılırsa HER mutlak yol jail'den geçer.
    """
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    # Tekil yol tek kök olarak kabul edilir…
    assert resolve_inspectable_worktree(approved, str(approved)) == approved.resolve()
    assert resolve_inspectable_worktree(approved, approved) == approved.resolve()
    # …ama karakterlerine bölünüp "/" kökü üretmez.
    assert resolve_inspectable_worktree(outside, str(approved)) is None
    assert resolve_inspectable_worktree(outside, approved) is None


@pytest.mark.parametrize("empty", ["", "   ", "\t"], ids=["empty", "spaces", "tab"])
def test_empty_root_is_no_root_not_the_working_directory(tmp_path: Path, monkeypatch, empty) -> None:
    """
    `Path("").resolve()` süreç çalışma dizinini verir. Boş kök kabul edilseydi
    `allowed_roots=""` jail'i sessizce cwd'ye açardı — fail-open. Boş girdi
    "kök yok" demeli.
    """
    victim = tmp_path / "victim"
    victim.mkdir()
    monkeypatch.chdir(tmp_path)

    assert resolve_inspectable_worktree(victim, empty) is None
    assert inspect_decision(victim, empty) == (None, REASON_NO_ROOT)
    # Sequence içindeki boş eleman da kök üretmemeli.
    assert resolve_inspectable_worktree(victim, [empty]) is None


def test_git_env_inherits_no_git_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    `GIT_DIR` / `GIT_WORK_TREE` git'in jail'lenmiş `cwd`'yi yok saymasına yol
    açar — yani jail env üzerinden atlanabilirdi. Ortam allowlist'li kurulur.
    """
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                 "GIT_EXTERNAL_DIFF", "GIT_SSH_COMMAND"):
        monkeypatch.setenv(name, "/tmp/attacker")

    env = _git_env()
    leaked = {k for k in env if k.startswith("GIT_")} - {
        "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM",
        "GIT_TERMINAL_PROMPT", "GIT_ASKPASS", "GIT_OPTIONAL_LOCKS",
        "GIT_ATTR_NOSYSTEM", "GIT_ALLOW_PROTOCOL",
    }
    assert leaked == set(), f"miras alınan GIT_* değişkeni: {leaked}"


def test_git_dir_in_environment_cannot_redirect_the_read(tmp_path: Path, git_repo: Path,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """Uçtan uca: ortamdaki GIT_DIR okumayı başka depoya yönlendirememeli."""
    other = tmp_path / "other"
    other.mkdir()
    _git(tmp_path, "init", "-q", "-b", "main", str(other))
    _git(other, "config", "user.email", "t@e.invalid")
    _git(other, "config", "user.name", "t")
    (other / "ONLY_IN_OTHER.txt").write_text("x\n", encoding="utf-8")

    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))

    (git_repo / "src" / "base.py").write_text("changed\n", encoding="utf-8")
    found = touched_paths(git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD")

    assert "src/base.py" in found
    assert "ONLY_IN_OTHER.txt" not in found


@pytest.mark.parametrize(
    ("make", "expected"),
    [
        (lambda tp: (tp / "nope", [tp]), REASON_MISSING),
        (lambda tp: ((tp / "afile.txt"), [tp]), REASON_NOT_A_DIR),
        (lambda tp: (tp, []), REASON_NO_ROOT),
    ],
    ids=["missing", "not-a-directory", "no-root"],
)
def test_skip_reason_names_the_actual_failure(tmp_path: Path, make, expected) -> None:
    """Her ret aynı etikete indirgenmemeli; kayıt gerçeği söylemeli."""
    (tmp_path / "afile.txt").write_text("x", encoding="utf-8")
    raw, roots = make(tmp_path)
    path, reason = inspect_decision(raw, roots)
    assert path is None
    assert reason == expected


def test_outside_root_reason_is_distinct(tmp_path: Path) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    assert inspect_decision(outside, [approved]) == (None, REASON_OUTSIDE)


def test_observe_skips_claims_pointing_outside_the_root(tmp_path: Path) -> None:
    """
    Uçtan uca: kök dışını gösteren claim atlanır, sebebi kaydedilir ve
    kök dışı yol günceye YAZILMAZ.
    """
    store = _store(tmp_path)
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    claim = _claim(store, worktree=str(outside))

    run = observe(store.store_dir, allowed_roots=[approved], now=NOW)

    assert any(REASON_OUTSIDE in s for s in run.skipped)
    assert all(claim.claim_id not in s or REASON_OUTSIDE in s for s in run.skipped)
    recorded = {p for o in run.observations for p in o.evidence.get("paths", [])}
    assert str(outside) not in recorded


def test_same_repo_claim_still_makes_a_touch_foreign(tmp_path: Path) -> None:
    """Repo eşleşmesi eklenirken asıl sinyalin kaybolmadığının kanıtı."""
    store = _store(tmp_path)
    mine = _claim(store, repo="lumos-core", scopes=["src/lumos_board"])
    same_repo = _claim(
        store,
        task_id="TD-96",
        repo="lumos-core",
        owner="agent-d",
        branch="codex/w",
        scopes=["docs"],
    )
    found = observe_scope(mine, ["docs/ROADMAP.md"], other_active=[mine, same_repo], now=NOW)
    assert [o.signal for o in found] == [SIGNAL_FOREIGN_SCOPE]
    assert found[0].evidence["owned_by"] == "agent-d"


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
