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
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lumos_board.task_claim import TaskClaimStore
from lumos_board.wall_observer import (
    OBSERVATION_SCHEMA,
    REASON_INDEX_REDIRECTED,
    REASON_MISSING,
    REASON_NOT_A_DIR,
    REASON_NO_REPO,
    REASON_NO_ROOT,
    REASON_OBJECTS_OUTSIDE,
    REASON_OUTSIDE,
    REASON_REPO_MALFORMED,
    REASON_REPO_OUTSIDE,
    SIGNAL_FOREIGN_SCOPE,
    SIGNAL_OUT_OF_SCOPE,
    SIGNAL_SILENT_DRIFT,
    SIGNAL_STALE_CLAIM,
    GitReadError,
    Observation,
    _git_env,
    inspect_decision,
    last_event_times,
    pin_repository,
    observe,
    observe_drift,
    observe_rhythm,
    observe_scope,
    resolve_inspectable_worktree,
    resolve_pinned_gitdir,
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


# --- Bugbot #5: jail dizini doğruluyordu, DEPOYU değil ----------------------
#
# Dizinin onaylı kökün içinde olması yetmiyor: git depoyu ayrıca keşfeder.
# `.git` bir gitfile olabilir ve kök dışını gösterebilir; `.git` hiç yoksa git
# üst dizinlerde ebeveyn depo arar. Jail içindeki boş bir dizin, kök dışındaki
# bir depoyu inceletebiliyordu ve o ağacın yolları günceye yazılabiliyordu.

def _repo_with_dirty_file(root: Path, name: str, filename: str) -> Path:
    repo = root / name
    repo.mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "t@e.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / filename).write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    (repo / filename).write_text("v2\n", encoding="utf-8")
    return repo


def test_gitfile_pointing_outside_the_root_is_refused(tmp_path: Path) -> None:
    """Jail içindeki stub dizin, kök dışındaki depoyu inceletememeli."""
    approved = tmp_path / "approved"
    approved.mkdir()
    secret = _repo_with_dirty_file(tmp_path, "secret_repo", "SECRET_ONLY_HERE.txt")

    stub = approved / "innocent"
    stub.mkdir()
    (stub / ".git").write_text(f"gitdir: {secret / '.git'}\n", encoding="utf-8")

    assert resolve_pinned_gitdir(stub, [approved]) is None
    found = touched_paths(stub, allowed_roots=[approved], base_ref="HEAD")
    assert found == ()
    assert not any("SECRET_ONLY_HERE" in p for p in found)


def test_legitimate_git_worktree_gitfile_still_works(tmp_path: Path) -> None:
    """
    `git worktree add` gitfile üretir; meşrudur. Sertleştirme gerçek
    kullanımı kırmamalı — hedef kökün içinde olduğu sürece çalışmalı.
    """
    approved = tmp_path / "approved"
    approved.mkdir()
    main_repo = _repo_with_dirty_file(approved, "main_repo", "a.txt")
    _git(main_repo, "add", "-A")
    _git(main_repo, "commit", "-qm", "second")
    linked = approved / "linked_wt"
    _git(main_repo, "worktree", "add", "-q", str(linked))

    assert (linked / ".git").is_file(), "git worktree gitfile üretmeliydi"
    assert resolve_pinned_gitdir(linked, [approved]) is not None

    (linked / "in_worktree.txt").write_text("x\n", encoding="utf-8")
    assert "in_worktree.txt" in touched_paths(linked, allowed_roots=[approved], base_ref="HEAD")


def test_directory_without_a_repo_does_not_discover_a_parent(tmp_path: Path) -> None:
    """`.git` yoksa git üst dizine tırmanabilir; keşif kapalı olmalı."""
    approved = tmp_path / "approved"
    approved.mkdir()
    parent_repo = _repo_with_dirty_file(approved, "parent_repo", "PARENT_FILE.txt")
    child = parent_repo / "plain_subdir"
    child.mkdir()

    assert resolve_pinned_gitdir(child, [approved]) is None
    assert touched_paths(child, allowed_roots=[approved], base_ref="HEAD") == ()


def test_chained_gitfile_cannot_bounce_out_of_the_root(tmp_path: Path) -> None:
    """
    Gitfile'ı tek hop takip edip kök kontrolü yapmak yetmez: git kalan
    zinciri kendi takip eder. Kök İÇİNDE duran bir 'bounce' gitfile, okumayı
    kök dışındaki bir depoya yönlendirebiliyordu.
    """
    approved = tmp_path / "approved"
    approved.mkdir()
    secret = _repo_with_dirty_file(tmp_path, "secret_repo", "SECRET_ONLY_HERE.txt")

    bounce = approved / "bounce"  # dosya, dizin değil — zincirin ikinci halkası
    bounce.write_text(f"gitdir: {secret / '.git'}\n", encoding="utf-8")
    stub = approved / "innocent"
    stub.mkdir()
    (stub / ".git").write_text(f"gitdir: {bounce}\n", encoding="utf-8")

    assert resolve_pinned_gitdir(stub, [approved]) is None
    found = touched_paths(stub, allowed_roots=[approved], base_ref="HEAD")
    assert found == ()
    assert not any("SECRET_ONLY_HERE" in p for p in found)


def test_refused_repository_is_recorded_as_a_skip(tmp_path: Path) -> None:
    """
    Worktree kök içinde ama DEPO reddedilmişse, bu sessizce 'temiz worktree'
    gibi görünmemeli — atlama kaydı düşmeli.
    """
    store = _store(tmp_path)
    approved = tmp_path / "approved"
    approved.mkdir()
    secret = _repo_with_dirty_file(tmp_path, "secret_repo", "SECRET.txt")
    stub = approved / "innocent"
    stub.mkdir()
    (stub / ".git").write_text(f"gitdir: {secret / '.git'}\n", encoding="utf-8")
    claim = _claim(store, worktree=str(stub))

    run = observe(store.store_dir, allowed_roots=[approved], now=NOW)

    assert any(REASON_REPO_OUTSIDE in s and claim.claim_id in s for s in run.skipped)


def _repo_with_two_commits(root: Path, name: str, filename: str) -> tuple[Path, str, str]:
    repo = root / name
    repo.mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "t@e.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / filename).write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "one")
    (repo / filename).write_text("v2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "two")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True, text=True, check=True
    ).stdout.strip()
    prev = subprocess.run(
        ["git", "rev-parse", "HEAD~1"], cwd=str(repo), capture_output=True, text=True, check=True
    ).stdout.strip()
    return repo, head, prev


def test_alternates_pointing_outside_the_root_is_refused(tmp_path: Path) -> None:
    """
    Depo yolunu hapsetmek yetmez: `objects/info/alternates` başka bir nesne
    deposunu ekleyebilir ve HEAD oradaki commit'e çevrilirse kök dışı ağacın
    yolları okunurdu.
    """
    approved = tmp_path / "approved"
    approved.mkdir()
    outside, head, prev = _repo_with_two_commits(tmp_path, "outside_repo", "OUTSIDE_SECRET.txt")

    victim = approved / "agent_wt"
    victim.mkdir()
    _git(approved, "init", "-q", "-b", "main", str(victim))
    _git(victim, "config", "user.email", "t@e.invalid")
    _git(victim, "config", "user.name", "t")
    (victim / "ok.txt").write_text("x\n", encoding="utf-8")
    _git(victim, "add", "-A")
    _git(victim, "commit", "-qm", "base")

    info = victim / ".git" / "objects" / "info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "alternates").write_text(
        str((outside / ".git" / "objects").resolve()) + "\n", encoding="utf-8"
    )
    (victim / ".git" / "HEAD").write_text(head + "\n", encoding="utf-8")

    assert pin_repository(victim, [approved]) == (None, REASON_OBJECTS_OUTSIDE)
    found = touched_paths(victim, allowed_roots=[approved], base_ref=prev)
    assert found == ()
    assert not any("OUTSIDE_SECRET" in p for p in found)


def test_objects_symlinked_outside_the_root_is_refused(tmp_path: Path) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    outside, _, _ = _repo_with_two_commits(tmp_path, "outside_repo", "OUTSIDE.txt")

    victim = approved / "agent_wt"
    victim.mkdir()
    _git(approved, "init", "-q", "-b", "main", str(victim))
    _git(victim, "config", "user.email", "t@e.invalid")
    _git(victim, "config", "user.name", "t")
    (victim / "ok.txt").write_text("x\n", encoding="utf-8")
    _git(victim, "add", "-A")
    _git(victim, "commit", "-qm", "base")

    objects = victim / ".git" / "objects"
    shutil.rmtree(objects)
    objects.symlink_to((outside / ".git" / "objects").resolve(), target_is_directory=True)

    assert pin_repository(victim, [approved]) == (None, REASON_OBJECTS_OUTSIDE)


@pytest.mark.parametrize(
    ("prepare", "expected"),
    [
        (lambda approved: (approved / "no_repo_here").mkdir() or (approved / "no_repo_here"),
         REASON_NO_REPO),
        (lambda approved: _write_bad_gitfile(approved), REASON_REPO_MALFORMED),
    ],
    ids=["no-repository", "malformed-gitfile"],
)
def test_repository_refusals_name_their_own_reason(tmp_path: Path, prepare, expected) -> None:
    """
    Her depo reddi `repository_outside_approved_root` diye kaydediliyordu;
    eksik `.git`, bozuk gitfile ve fazla uzun zincir de aynı etikete
    düşüyordu. Kayıt gerçek sebebi söylemeli.
    """
    approved = tmp_path / "approved"
    approved.mkdir()
    target = prepare(approved)
    assert pin_repository(target, [approved]) == (None, expected)


def _write_bad_gitfile(approved: Path) -> Path:
    stub = approved / "bad_gitfile"
    stub.mkdir()
    (stub / ".git").write_text("this is not a gitdir pointer\n", encoding="utf-8")
    return stub


@pytest.mark.parametrize("driver", ["evil", "Odd.Name-42"])
@pytest.mark.parametrize("filter_kind", ["clean", "process"])
def test_in_root_filters_never_execute(tmp_path: Path, driver: str, filter_kind: str) -> None:
    """Gerçek repo-local sürücü gözlemci sürecinde çalışmamalı."""
    approved = tmp_path / "approved"
    approved.mkdir()
    repo = approved / "agent_wt"
    repo.mkdir()
    _git(approved, "init", "-q", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "t@e.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / "data.bin").write_text("v1\n", encoding="utf-8")
    (repo / ".gitattributes").write_text(f"data.bin filter={driver}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")

    marker = tmp_path / "FILTER_RAN"
    payload = tmp_path / "filter.sh"
    payload.write_text(f"#!/bin/sh\ntouch {marker}\ncat\n", encoding="utf-8")
    payload.chmod(0o755)
    _git(repo, "config", f"filter.{driver}.{filter_kind}", str(payload))
    _git(repo, "config", f"filter.{driver}.required", "true")
    (repo / "data.bin").write_text("v2\n", encoding="utf-8")

    assert "data.bin" in touched_paths(repo, allowed_roots=[approved], base_ref="HEAD")
    assert not marker.exists()

    store = _store(tmp_path)
    _claim(store, worktree=str(repo))
    observe(store.store_dir, allowed_roots=[approved], now=NOW)
    assert not marker.exists()


def test_commondir_pointing_outside_the_root_is_refused(tmp_path: Path) -> None:
    """Bağlı worktree'nin gerçek nesne deposu da kökün içinde olmalı."""
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = _repo_with_dirty_file(tmp_path, "outside_repo", "b.txt")

    fake_gitdir = approved / "planted.git"
    fake_gitdir.mkdir()
    (fake_gitdir / "commondir").write_text(f"{outside / '.git'}\n", encoding="utf-8")
    stub = approved / "stub"
    stub.mkdir()
    (stub / ".git").write_text(f"gitdir: {fake_gitdir}\n", encoding="utf-8")

    assert resolve_pinned_gitdir(stub, [approved]) is None


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


@pytest.mark.parametrize("relative", [False, True])
def test_nested_alternates_cannot_bounce_outside(tmp_path: Path, relative: bool) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    outside, head, prev = _repo_with_two_commits(tmp_path, "secret", "SECRET_OUTSIDE.txt")
    victim = _repo_with_dirty_file(approved, "victim", "ok.txt")
    bounce = approved / "bounce"
    (bounce / "info").mkdir(parents=True)
    (bounce / "info" / "alternates").write_text(str(outside / ".git" / "objects") + "\n")
    objects = victim / ".git" / "objects"
    (objects / "info" / "alternates").write_text("../../../bounce\n" if relative else str(bounce) + "\n")
    (victim / ".git" / "HEAD").write_text(head + "\n")
    # Kontrol: aynı fixture gerçekten Git'e yabancı ağacı okutabiliyor.
    leaked = subprocess.run(["git", "diff", "--name-only", f"{prev}...HEAD"],
                            cwd=victim, capture_output=True, text=True, check=True).stdout
    assert "SECRET_OUTSIDE.txt" in leaked
    assert pin_repository(victim, [approved]) == (None, REASON_OBJECTS_OUTSIDE)
    assert touched_paths(victim, allowed_roots=[approved], base_ref=prev) == ()
    store = _store(tmp_path)
    claim = _claim(store, worktree=str(victim))
    run = observe(store.store_dir, allowed_roots=[approved], base_ref=prev, now=NOW)
    assert any(REASON_OBJECTS_OUTSIDE in s and claim.claim_id in s for s in run.skipped)
    assert "SECRET_OUTSIDE" not in str(run.observations)


@pytest.mark.parametrize("child", ["pack", "ab", "info", "info/alternates", "ab/object"])
def test_object_store_child_symlinks_are_refused(tmp_path: Path, child: str) -> None:
    approved = tmp_path / "approved"
    repo = _repo_with_dirty_file(approved, "repo", "ok.txt")
    external = tmp_path / "external"
    external.mkdir()
    target = repo / ".git" / "objects" / child
    target.parent.mkdir(exist_ok=True)
    if target.exists():
        target.rename(target.with_name(target.name + "-saved"))
    target.symlink_to(external, target_is_directory=True)
    assert pin_repository(repo, [approved]) == (None, REASON_OBJECTS_OUTSIDE)
    assert touched_paths(repo, allowed_roots=[approved]) == ()


def test_safe_nested_alternates_and_cycle_remain_usable(tmp_path: Path) -> None:
    source, head, prev = _repo_with_two_commits(tmp_path, "source", "allowed.txt")
    repo = _repo_with_dirty_file(tmp_path, "victim", "ok.txt")
    objects = repo / ".git" / "objects"
    bounce = tmp_path / "bounce"
    (bounce / "info").mkdir(parents=True)
    (objects / "info" / "alternates").write_text(str(bounce) + "\n")
    source_objects = source / ".git" / "objects"
    (bounce / "info" / "alternates").write_text(str(source_objects) + "\n")
    (source_objects / "info" / "alternates").write_text(str(objects) + "\n")
    (repo / ".git" / "HEAD").write_text(head + "\n")
    assert pin_repository(repo, [tmp_path])[0] == repo / ".git"
    assert "allowed.txt" in touched_paths(repo, allowed_roots=[tmp_path], base_ref=prev)


@pytest.mark.parametrize("alternate", ['"/quoted/path"', "/missing/store"])
def test_unverifiable_alternates_fail_closed(git_repo: Path, alternate: str) -> None:
    (git_repo / ".git" / "objects" / "info" / "alternates").write_text(alternate + "\n")
    assert pin_repository(git_repo, [git_repo.parent]) == (None, REASON_OBJECTS_OUTSIDE)


def test_tracked_deletion_is_observed(git_repo: Path) -> None:
    (git_repo / "src" / "base.py").rename(git_repo / "moved.py")
    assert {"src/base.py", "moved.py"} <= set(touched_paths(
        git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD"))


def test_worktree_symlink_reads_link_not_target(git_repo: Path) -> None:
    link = git_repo / "link"
    link.symlink_to("missing-target")
    _git(git_repo, "add", "link")
    _git(git_repo, "commit", "-qm", "symlink")
    assert touched_paths(git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD") == ()
    link.rename(git_repo / "old-link")
    link.symlink_to("different-target")
    assert "link" in touched_paths(git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD")


@pytest.mark.parametrize("replacement", ["symlink", "fifo", "directory"])
def test_tracked_file_type_changes_do_not_follow_or_block(git_repo: Path, replacement: str) -> None:
    target = git_repo / "src" / "base.py"
    target.rename(git_repo / "original.py")
    if replacement == "symlink":
        target.symlink_to("../original.py")
    elif replacement == "fifo":
        os.mkfifo(target)
    else:
        target.mkdir()
    assert "src/base.py" in touched_paths(git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD")


def test_filter_from_include_and_info_attributes_never_runs(git_repo: Path, tmp_path: Path) -> None:
    marker = tmp_path / "FILTER_RAN"
    config = tmp_path / "included.config"
    config.write_text(f'[filter "injected"]\nclean = "touch {marker}; cat"\n')
    _git(git_repo, "config", "include.path", str(config))
    (git_repo / ".git" / "info" / "attributes").write_text("* filter=injected\n")
    (git_repo / "src" / "base.py").write_text("changed\n")
    assert "src/base.py" in touched_paths(git_repo, allowed_roots=[tmp_path], base_ref="HEAD")
    assert not marker.exists()


def test_raw_comparison_conservatively_reports_normalized_content(git_repo: Path) -> None:
    # Güvenilmeyen dönüşüm çalıştırılmaz; ham fark kaybolmamalı.
    (git_repo / "src" / "base.py").write_bytes(b"x = 1\r\n")
    _git(git_repo, "config", "core.autocrlf", "true")
    assert "src/base.py" in touched_paths(git_repo, allowed_roots=[git_repo.parent], base_ref="HEAD")


@pytest.mark.parametrize("separator", ["\v", "\r", "\f"])
def test_alternate_path_control_characters_are_not_line_separators(
    git_repo: Path, tmp_path: Path, separator: str
) -> None:
    objects = git_repo / ".git" / "objects"
    (objects / "safe").mkdir()
    (objects / "bounce").mkdir()
    outside = tmp_path / "outside-store"
    outside.mkdir()
    (objects / f"safe{separator}bounce").symlink_to(outside, target_is_directory=True)
    (objects / "info" / "alternates").write_bytes(f"safe{separator}bounce\n".encode())
    assert pin_repository(git_repo, [git_repo]) == (None, REASON_OBJECTS_OUTSIDE)


def test_index_symlinked_to_foreign_repo_is_refused(tmp_path: Path) -> None:
    """
    Depo, commondir ve nesne deposu hapsedildi diye index hapsedilmiş olmaz:
    `ls-files --stage` ile `diff --cached`'in okuduğu veri `$GIT_DIR/index`'tir
    ve git oradaki symlink'i takip eder. Kök içindeki bir worktree index'i
    başka bir okunabilir deponun index'ine bağlarsa, o deponun izlenen yolları
    bu claim'in dokunuşu gibi günceye yazılırdı.
    """
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = _repo_with_dirty_file(tmp_path, "secret_repo", "OUTSIDE_SECRET.txt")
    victim = _repo_with_dirty_file(approved, "innocent", "ok.txt")
    index = victim / ".git" / "index"
    index.unlink()
    index.symlink_to(outside / ".git" / "index")

    # Kontrol: aynı fixture gerçekten Git'e yabancı index'i okutabiliyor.
    leaked = subprocess.run(["git", "ls-files"], cwd=victim,
                            capture_output=True, text=True, check=True).stdout
    assert "OUTSIDE_SECRET.txt" in leaked

    assert pin_repository(victim, [approved]) == (None, REASON_INDEX_REDIRECTED)
    assert touched_paths(victim, allowed_roots=[approved], base_ref="HEAD") == ()
    store = _store(tmp_path)
    claim = _claim(store, worktree=str(victim))
    run = observe(store.store_dir, allowed_roots=[approved], now=NOW)
    assert any(REASON_INDEX_REDIRECTED in s and claim.claim_id in s for s in run.skipped)
    assert "OUTSIDE_SECRET" not in str(run.observations)


def test_sharedindex_symlink_is_refused(tmp_path: Path) -> None:
    # Split-index parçaları da index gibi `$GIT_DIR`'den okunur; symlink'leri
    # aynı yönlendirme kapısıdır.
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = _repo_with_dirty_file(tmp_path, "secret_repo", "OUTSIDE_SECRET.txt")
    repo = _repo_with_dirty_file(approved, "repo", "ok.txt")
    shared = repo / ".git" / "sharedindex.0000"
    shared.symlink_to(outside / ".git" / "index")
    assert pin_repository(repo, [approved]) == (None, REASON_INDEX_REDIRECTED)
    assert touched_paths(repo, allowed_roots=[approved]) == ()


def test_missing_index_is_not_a_refusal(tmp_path: Path) -> None:
    # Index'in hiç olmaması yönlendirme değildir; taze depo incelenebilir kalır.
    repo = _repo_with_dirty_file(tmp_path, "repo", "ok.txt")
    (repo / ".git" / "index").unlink()
    assert pin_repository(repo, [tmp_path])[0] == repo / ".git"


def test_non_utf8_filename_does_not_abort_observation(tmp_path: Path) -> None:
    """
    Git `-z` çıktısı ham bayttır; UTF-8 olmayan tek bir dosya adı strict
    decode ile bütün turu düşürürdü — gözlenen tarafın gözlemciyi kapattığı
    bir fail-open. Bozuk ad maskelenmiş biçimde kaydedilir, tur yaşar.
    """
    approved = tmp_path / "approved"
    approved.mkdir()
    repo = _repo_with_dirty_file(approved, "repo", "ok.txt")
    with open(os.path.join(os.fsencode(repo), b"bad\xffname.txt"), "wb") as handle:
        handle.write(b"x")

    found = touched_paths(repo, allowed_roots=[approved], base_ref="HEAD")
    assert "ok.txt" in found
    assert any("�" in p for p in found)

    store = _store(tmp_path)
    poisoned = _claim(store, worktree=str(repo))
    healthy = _claim(store, task_id="TD-98", owner="agent-b", branch="codex/y", scopes=["docs"])
    run = observe(
        store.store_dir,
        allowed_roots=[approved],
        worktree_paths={healthy.claim_id: ["panel/x.py"]},
        base_ref="HEAD",
        now=NOW,
    )
    assert any(o.claim_id == poisoned.claim_id for o in run.observations)
    assert any(o.claim_id == healthy.claim_id for o in run.observations)


def test_unexpected_inspection_error_is_a_skip_not_an_abort(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Tek claim'in beklenmedik hatası diğer claim'lerin gözlemini kapatamaz;
    # hata gerekçesiyle skip kaydına iner.
    import lumos_board.wall_observer as wall_observer_module

    store = _store(tmp_path)
    repo = _repo_with_dirty_file(tmp_path, "repo", "ok.txt")
    broken = _claim(store, worktree=str(repo))
    healthy = _claim(store, task_id="TD-98", owner="agent-b", branch="codex/y", scopes=["docs"])

    def boom(*args: object, **kwargs: object) -> tuple[str, ...]:
        raise RuntimeError("boom")

    monkeypatch.setattr(wall_observer_module, "touched_paths", boom)
    run = observe(
        store.store_dir,
        allowed_roots=[tmp_path],
        worktree_paths={healthy.claim_id: ["panel/x.py"]},
        now=NOW,
    )
    assert any(
        broken.claim_id in s and "inspection_error:RuntimeError" in s for s in run.skipped
    )
    assert any(o.claim_id == healthy.claim_id for o in run.observations)


def test_clean_tracked_non_utf8_name_stays_clean(tmp_path: Path) -> None:
    """
    Bozuk adı U+FFFD'ye çevirip dosyayı o adla aramak, temiz commit'lenmiş
    dosyayı sonsuza dek "değişmiş" gösterirdi (kalıcı sahte OUT_OF_SCOPE /
    SILENT_DRIFT). Baytlar içeride kayıpsız taşınır: temiz dosya temiz kalır,
    gerçekten değişince maskeli adıyla raporlanır.
    """
    approved = tmp_path / "approved"
    approved.mkdir()
    repo = approved / "repo"
    repo.mkdir()
    _git(approved, "init", "-q", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "t@e.invalid")
    _git(repo, "config", "user.name", "t")
    bad_name = os.path.join(os.fsencode(repo), b"bad\xffname.txt")
    with open(bad_name, "wb") as handle:
        handle.write(b"v1\n")
    (repo / "ok.txt").write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    (repo / "ok.txt").write_text("v2\n", encoding="utf-8")

    found = touched_paths(repo, allowed_roots=[approved], base_ref="HEAD")
    assert "ok.txt" in found
    assert not any("�" in p for p in found)  # temiz bozuk-adlı dosya raporlanmaz

    with open(bad_name, "wb") as handle:
        handle.write(b"v2\n")
    found = touched_paths(repo, allowed_roots=[approved], base_ref="HEAD")
    assert any("�" in p for p in found)  # gerçek değişiklik maskeli adla görünür


def test_corrupt_event_log_does_not_abort_observation(tmp_path: Path) -> None:
    """
    `claim_events.jsonl`'a ajanlar da yazar; tek bozuk bayt strict UTF-8'de
    bütün turu düşürürdü — gözlenen tarafın duvarı herkes için karartması.
    Bozuk satır elenir, geçerli satırlar ve tur yaşar.
    """
    log = tmp_path / "claim_events.jsonl"
    log.write_bytes(
        b'{"claim_id": "a", "at": "2026-09-04T10:00:00Z"}\n'
        b'\xff\xfe bozuk \xff\n'
        b'{"claim_id": "b", "at": "2026-09-04T10:05:00Z"}\n'
    )
    times = last_event_times(log)
    assert set(times) == {"a", "b"}

    store = _store(tmp_path)
    claim = _claim(store)
    (store.store_dir / "claim_events.jsonl").write_bytes(b"\xff\xfe bozuk \xff\n")
    run = observe(
        store.store_dir, worktree_paths={claim.claim_id: ["panel/x.py"]}, now=NOW
    )
    assert any(o.claim_id == claim.claim_id for o in run.observations)


def test_failed_git_read_is_a_named_skip_not_a_clean_worktree(tmp_path: Path) -> None:
    """
    Eksik base ref / bozuk depo / timeout "değişiklik yok" demek değildir.
    Boş küme dönmek commit'lenmiş S1/S2 kanıtını iz bırakmadan yutuyordu;
    başarısız okuma artık gerekçeli skip kaydıdır.
    """
    approved = tmp_path / "approved"
    approved.mkdir()
    repo = _repo_with_dirty_file(approved, "repo", "ok.txt")

    with pytest.raises(GitReadError):
        # origin/main bu depoda yok: diff başarısız, sonuç "temiz" olamaz.
        touched_paths(repo, allowed_roots=[approved], base_ref="origin/main")

    store = _store(tmp_path)
    claim = _claim(store, worktree=str(repo))
    run = observe(store.store_dir, allowed_roots=[approved], base_ref="origin/main", now=NOW)
    assert any(
        claim.claim_id in s and "git_read_failed:diff" in s for s in run.skipped
    )
