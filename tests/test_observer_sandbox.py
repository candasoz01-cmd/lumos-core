"""Acceptance tests for Agent Wall observer sandbox MVP (sandbox-v0).

Bubblewrap integration tests skip when `bwrap` is absent. Unit checks for env
scrub and launcher construction still run so CI without bwrap is not silent.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from lumos_board.observer_sandbox import (
    SandboxUnavailableError,
    _bwrap_isolation_prefix,
    probe_sandbox_env,
    run_git_sandboxed,
    sandbox_backend,
    scrub_env_for_sandbox,
)

needs_bwrap = pytest.mark.skipif(
    shutil.which("bwrap") is None,
    reason="bubblewrap (bwrap) required for sandbox MVP tests",
)


def _write_start_sentinel(command: Sequence[str], stdin_fd: object) -> None:
    """Simulate the jail wrapper: the nonce goes to the stdin sentinel pipe."""
    assert isinstance(stdin_fd, int), "sentinel pipe write end must be passed as stdin"
    for part in command:
        if isinstance(part, str) and part.startswith("echo lumos-sandbox-start-"):
            nonce = part.split(";", 1)[0].split()[1]
            os.write(stdin_fd, (nonce + "\n").encode("ascii"))
            return
    raise AssertionError("start sentinel missing from sandbox command")


def _stub_launcher(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Unit-test seam: pretend bwrap exists; dummy cgroup (no host cgroup needed)."""
    real_which = shutil.which

    def _which(name: str):
        if name == "bwrap":
            return real_which("bwrap") or "/usr/bin/bwrap"
        return real_which(name)

    monkeypatch.setattr("lumos_board.observer_sandbox.shutil.which", _which)
    cg = tmp_path / "lumos-obs-stub"
    cg.mkdir()
    (cg / "cgroup.procs").touch()

    @contextmanager
    def _fake_cg(**_kwargs):  # type: ignore[no-untyped-def]
        yield cg

    monkeypatch.setattr("lumos_board.observer_sandbox._sandbox_memory_cgroup", _fake_cg)
    return cg


def _cgroup_memory_delegated() -> bool:
    try:
        from lumos_board.observer_sandbox import _memory_cgroup_insert_parent

        _memory_cgroup_insert_parent()
        return True
    except (OSError, SandboxUnavailableError):
        return False


needs_cgroup = pytest.mark.skipif(
    not _cgroup_memory_delegated(),
    reason="delegated cgroup v2 memory controller required",
)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
        },
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "wt"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "a.txt").write_text("hello\n", encoding="utf-8")
    _git(root, "add", "a.txt")
    _git(root, "commit", "-m", "init")
    return root


@needs_bwrap
def test_backend_is_bubblewrap() -> None:
    assert sandbox_backend() == "bubblewrap"


def test_scrub_env_drops_operator_credentials() -> None:
    """§4.2 launcher scrub (unit)."""
    cleaned = scrub_env_for_sandbox(
        {
            "PATH": "/usr/bin",
            "SSH_AUTH_SOCK": "/tmp/agent.sock",
            "AWS_SECRET_ACCESS_KEY": "sekrit",
            "LUMOS_OPERATOR_TOKEN": "tok",
            "GITHUB_TOKEN": "gh",
            "HOME": "/home/op",
        }
    )
    assert "SSH_AUTH_SOCK" not in cleaned
    assert "AWS_SECRET_ACCESS_KEY" not in cleaned
    assert "LUMOS_OPERATOR_TOKEN" not in cleaned
    assert "GITHUB_TOKEN" not in cleaned
    assert cleaned["HOME"] == "/tmp/lumos-observer-home"


@needs_bwrap
def test_probe_env_does_not_leak_host_secrets(repo: Path) -> None:
    """§4.2 negative: secrets do not enter the sandbox env."""
    host = {
        **os.environ,
        "SSH_AUTH_SOCK": "/tmp/should-not-leak.sock",
        "LUMOS_OPERATOR_TOKEN": "leak-me",
        "AWS_SECRET_ACCESS_KEY": "leak-me-too",
    }
    inside = probe_sandbox_env(allowed_roots=[repo], host_env=host)
    assert "SSH_AUTH_SOCK" not in inside
    assert "LUMOS_OPERATOR_TOKEN" not in inside
    assert "AWS_SECRET_ACCESS_KEY" not in inside
    assert inside.get("GIT_ASKPASS") == "/bin/false"


@needs_bwrap
def test_non_utf8_git_output_does_not_crash(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bugbot Medium: binary/non-UTF-8 stdout must not UnicodeDecodeError out."""
    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        # Force the production path (text=False) and inject non-UTF-8 bytes into
        # the bounded regular files used instead of unbounded capture pipes.
        if kwargs.get("text") is True:
            raise AssertionError("run_git_sandboxed must not use text=True")
        if not isinstance(kwargs.get("stdin"), int):
            raise AssertionError(
                "run_git_sandboxed must pass the sentinel pipe write end as stdin"
            )
        # Başlamış bir sandbox'ı simüle et: gerçek koşumda nonce'u jail
        # içindeki sarmalayıcı stdin borusuna basar; sahte koşum onu
        # komuttan çıkarıp aynı boruya yazar.
        command = args[0] if args else kwargs["args"]
        _write_start_sentinel(command, kwargs.get("stdin"))
        kwargs["stdout"].write(b"ok-\xff-binary\n")
        kwargs["stderr"].write(b"warn-\xfe\n")
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
        )

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = run_git_sandboxed(
        ["status", "--porcelain"],
        cwd=repo,
        allowed_roots=[repo],
    )
    assert result.returncode == 0
    assert "ok-" in result.stdout
    assert "\ufffd" in result.stdout or "binary" in result.stdout
    assert "warn-" in result.stderr


@needs_bwrap
def test_git_output_is_bounded_and_fails_closed(repo: Path) -> None:
    """§3.2 — a repository cannot make observer capture grow without bound."""
    payload = b"x" * (1024 * 1024 + 4096)
    (repo / "large.bin").write_bytes(payload)
    _git(repo, "add", "large.bin")
    _git(repo, "commit", "-m", "large-output")

    result = run_git_sandboxed(
        ["show", "HEAD:large.bin"],
        cwd=repo,
        allowed_roots=[repo],
    )
    assert result.returncode != 0
    assert len(result.stdout.encode("utf-8", "replace")) <= 1024 * 1024
    assert "output limit reached" in result.stderr


def _probe_interpreter() -> str:
    """Sandbox içinde çalıştırılacak Python: tam çözülmüş gerçek yol.

    `/usr/bin/python3` çoğu Debian/Ubuntu'da `/etc/alternatives` üzerinden
    symlink'tir; sandbox `/etc`'yi bağlamadığı için o yol içeride KÖRDÜR ve
    kontrol probe'u `execvp: No such file or directory` ile düşer — izolasyon
    kanıtı hiç koşamaz. Testi koşturan yorumlayıcının gerçek yolu kullanılır.
    """
    return str(Path(sys.executable).resolve())


def _bwrap_probe(inner: list[str], *, timeout: float):
    from lumos_board.observer_sandbox import _bwrap_isolation_prefix, _run_bwrap_payload

    cmd = _bwrap_isolation_prefix()
    for host in ("/usr", "/bin", "/lib", "/lib64"):
        if Path(host).exists():
            cmd += ["--ro-bind", host, host]
    cmd += ["--clearenv"]
    return _run_bwrap_payload(cmd, inner, timeout=timeout)


def _bwrap_tcp_probe(port: int, *, unshare_net: bool, allowed_root: Path) -> int:
    """Same bind shape as the MVP motor; optional --unshare-net for contrast."""
    interpreter = _probe_interpreter()
    cmd: list[str] = [
        "bwrap",
        "--die-with-parent",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--cap-drop",
        "ALL",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/bin",
        "/bin",
    ]
    if Path("/lib").exists():
        cmd += ["--ro-bind", "/lib", "/lib"]
    if Path("/lib64").exists():
        cmd += ["--ro-bind", "/lib64", "/lib64"]
    cmd += ["--ro-bind", str(allowed_root), str(allowed_root)]
    if not (interpreter.startswith("/usr/") or interpreter.startswith("/bin/")):
        cmd += ["--ro-bind", interpreter, interpreter]
    if unshare_net:
        cmd.append("--unshare-net")
    cmd += [
        "--chdir",
        str(allowed_root),
        "--clearenv",
        "--setenv",
        "PATH",
        "/usr/bin:/bin",
        interpreter,
        "-c",
        (
            "import socket,sys;\n"
            f"s=socket.socket(); s.settimeout(2)\n"
            f"try:\n"
            f"  s.connect(('127.0.0.1', {port}))\n"
            f"  sys.exit(0)\n"
            f"except OSError:\n"
            f"  sys.exit(2)\n"
        ),
    ]
    return subprocess.run(cmd, capture_output=True, check=False, timeout=15).returncode


@needs_bwrap
def test_network_unshared_fail_closed(repo: Path) -> None:
    """§4.3 — prove --unshare-net, not DNS-to-invalid-TLD fake-green.

    Local TCP server is reachable from an otherwise identical bwrap *without*
    --unshare-net, and unreachable with --unshare-net. Production
    ``run_git_sandboxed`` always passes --unshare-net.
    """
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    stop = threading.Event()
    httpd: HTTPServer | None = None

    def _accept() -> None:
        srv.settimeout(0.5)
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
                conn.close()
            except OSError:
                continue

    t = threading.Thread(target=_accept, daemon=True)
    t.start()
    try:
        assert _bwrap_tcp_probe(port, unshare_net=False, allowed_root=repo) == 0, (
            "control bwrap without --unshare-net must reach 127.0.0.1 "
            "(otherwise this host cannot prove network isolation)"
        )
        assert _bwrap_tcp_probe(port, unshare_net=True, allowed_root=repo) != 0, (
            "--unshare-net must block localhost TCP"
        )
        # Production API path includes --unshare-net (git cannot reach loopback HTTP).
        httpd = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
        http_port = httpd.server_address[1]

        def _serve() -> None:
            assert httpd is not None
            httpd.handle_request()

        threading.Thread(target=_serve, daemon=True).start()
        result = run_git_sandboxed(
            ["ls-remote", f"http://127.0.0.1:{http_port}/repo.git"],
            cwd=repo,
            allowed_roots=[repo],
            timeout=20,
        )
        assert result.returncode != 0
    finally:
        stop.set()
        srv.close()
        if httpd is not None:
            httpd.server_close()


@needs_bwrap
def test_worktree_writes_fail_closed(repo: Path) -> None:
    """§4.4 worktree write denied under ro-bind."""
    before = (repo / "a.txt").read_text(encoding="utf-8")
    result = run_git_sandboxed(
        ["commit", "--allow-empty", "-m", "should-fail-ro"],
        cwd=repo,
        allowed_roots=[repo],
    )
    assert result.returncode != 0
    assert (repo / "a.txt").read_text(encoding="utf-8") == before
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert head


@needs_bwrap
def test_clean_filter_capability_denial(repo: Path, tmp_path: Path) -> None:
    """§4.1 — repo-controlled filter may run; capabilities outside sandbox denied.

    Helper lives *inside* allowed_roots (measurement error: helper outside the
    jail is not a sandbox proof).
    Outside marker + journal path must stay untouched.
    """
    marker_outside = tmp_path / "filter-ran.marker"
    journal = tmp_path / "operator-journal" / "obs.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    # Pre-create empty journal on host (operator path).
    journal.write_text("", encoding="utf-8")

    helper = repo / "evil-clean.sh"
    helper.write_text(
        "#!/bin/sh\n"
        f"echo FILTER_RAN >&2\n"
        f"echo ran > '{marker_outside}'\n"
        f"echo sandboxed >> '{journal}'\n"
        "cat\n",
        encoding="utf-8",
    )
    helper.chmod(helper.stat().st_mode | stat.S_IEXEC)

    attrs = repo / ".gitattributes"
    attrs.write_text("a.txt filter=evil\n", encoding="utf-8")
    _git(repo, "config", "filter.evil.clean", str(helper))
    # Touch tracked file so status hashes content and may invoke clean.
    (repo / "a.txt").write_text("hello\nchanged\n", encoding="utf-8")
    _git(repo, "add", ".gitattributes")
    _git(repo, "commit", "-m", "attrs")

    if marker_outside.exists():
        marker_outside.unlink()
    before_journal = journal.read_text(encoding="utf-8")

    # ``diff`` hashes blob content and invokes clean; ``status`` alone can
    # stay dirty from size/mtime without running the filter (Bugbot Medium).
    result = run_git_sandboxed(
        ["diff", "--", "a.txt"],
        cwd=repo,
        allowed_roots=[repo],
    )
    assert "FILTER_RAN" in result.stderr, (
        f"clean filter must run (rc={result.returncode}, err={result.stderr!r})"
    )
    assert not marker_outside.exists(), (
        f"outside write succeeded (rc={result.returncode}, err={result.stderr!r})"
    )
    assert journal.read_text(encoding="utf-8") == before_journal, (
        "sandbox must not append operator journal path"
    )


@needs_bwrap
def test_filter_cannot_read_operator_env_from_sandbox_pid1(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§4.2 — launcher env is scrubbed before bwrap becomes sandbox PID 1."""
    helper = repo / "pid1-env-clean.sh"
    helper.write_text(
        "#!/bin/sh\n"
        "if tr '\\0' '\\n' </proc/1/environ | "
        "grep -q '^LUMOS_OPERATOR_TOKEN='; then\n"
        "  echo PID1_ENV_LEAKED >&2\n"
        "else\n"
        "  echo PID1_ENV_CLEAN >&2\n"
        "fi\n"
        "cat\n",
        encoding="utf-8",
    )
    helper.chmod(helper.stat().st_mode | stat.S_IEXEC)
    (repo / ".gitattributes").write_text("a.txt filter=pid1env\n", encoding="utf-8")
    _git(repo, "config", "filter.pid1env.clean", str(helper))
    (repo / "a.txt").write_text("pid1-env-probe\n", encoding="utf-8")
    _git(repo, "add", ".gitattributes")
    _git(repo, "commit", "-m", "pid1-env-probe")
    monkeypatch.setenv("LUMOS_OPERATOR_TOKEN", "must-not-reach-pid1")

    result = run_git_sandboxed(
        ["diff", "--", "a.txt"],
        cwd=repo,
        allowed_roots=[repo],
    )
    assert "PID1_ENV_CLEAN" in result.stderr
    assert "PID1_ENV_LEAKED" not in result.stderr


@needs_bwrap
def test_filter_cannot_open_controlling_tty(repo: Path) -> None:
    """Security Review Medium: --dev /dev + inherited stdin must not leak TTY.

    Repo-controlled clean filter may run (§4.1). It must not open /dev/tty
    (new session) and must not inherit operator stdin (DEVNULL).
    """
    helper = repo / "tty-clean.sh"
    helper.write_text(
        "#!/bin/sh\n"
        "if (exec 3<>/dev/tty) 2>/dev/null; then\n"
        "  echo TTY_OPENED >&2\n"
        "fi\n"
        "data=$(dd bs=64 count=1 2>/dev/null || true)\n"
        "echo STDIN_LEN=${#data} >&2\n"
        "cat\n",
        encoding="utf-8",
    )
    helper.chmod(helper.stat().st_mode | stat.S_IEXEC)
    (repo / ".gitattributes").write_text("a.txt filter=ttyprobe\n", encoding="utf-8")
    _git(repo, "config", "filter.ttyprobe.clean", str(helper))
    (repo / "a.txt").write_text("hallo\n", encoding="utf-8")
    _git(repo, "add", ".gitattributes")
    _git(repo, "commit", "-m", "ttyprobe")

    result = run_git_sandboxed(
        ["diff", "--", "a.txt"],
        cwd=repo,
        allowed_roots=[repo],
    )
    # Filter must run (git feeds blob bytes on its own pipe — not operator TTY).
    assert "STDIN_LEN=" in result.stderr, result.stderr
    assert "TTY_OPENED" not in result.stderr, result.stderr


@needs_bwrap
def test_sandbox_uses_new_session_and_non_tty_stdin(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Always-on proof for TTY/session Medium (this host may have no /dev/tty).

    stdin artık sentinel borusunun yazma ucudur (TTY değildir); sarmalayıcı
    onu payload exec'inden önce `exec </dev/null` ile değiştirir.
    """
    seen: list[tuple[list[str], object, object, object]] = []
    real_run = subprocess.run

    def _wrap(*args, **kwargs):  # type: ignore[no-untyped-def]
        cmd = list(args[0] if args else kwargs.get("args") or [])
        stdin = kwargs.get("stdin")
        stdin_is_pipe = isinstance(stdin, int) and stdin >= 0 and stat.S_ISFIFO(
            os.fstat(stdin).st_mode
        )
        seen.append((cmd, stdin, stdin_is_pipe, kwargs.get("preexec_fn")))
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _wrap)
    run_git_sandboxed(["status", "--porcelain"], cwd=repo, allowed_roots=[repo])
    probe_sandbox_env(allowed_roots=[repo], host_env=os.environ.copy())
    assert len(seen) >= 2
    from lumos_board.observer_sandbox import _join_fresh_session_keyring

    for cmd, stdin, stdin_is_pipe, preexec in seen:
        assert cmd
        # Launcher ya cgroup sarmalayıcısıyla (sh -> cgroup.procs) ya da cgroup
        # delege değilse doğrudan prlimit ile başlar (graceful degrade). İkisi de
        # geçerli; TTY/stdin invariantı her iki path'te de aynıdır.
        if Path(cmd[0]).name == "sh":
            assert any("cgroup.procs" in part for part in cmd if isinstance(part, str))
        elif Path(cmd[0]).name == "unshare":
            assert "--kill-child" in cmd
            assert "--pid" in cmd
            assert "--mount-proc" in cmd
            assert not any(
                "cgroup.procs" in part for part in cmd if isinstance(part, str)
            )
        else:
            assert Path(cmd[0]).name == "prlimit"
            assert not any(
                "cgroup.procs" in part for part in cmd if isinstance(part, str)
            )
        assert any(Path(part).name == "prlimit" for part in cmd)
        nproc = next(part for part in cmd if part.startswith("--nproc="))
        soft, hard = nproc.removeprefix("--nproc=").split(":")
        assert int(soft) == int(hard)
        assert int(soft) >= 65
        assert "--fsize=1048576:1048576" in cmd
        assert "--as=1073741824:1073741824" in cmd
        assert "bwrap" in [Path(part).name for part in cmd]
        assert "--new-session" in cmd
        assert "--unshare-all" in cmd
        assert "--disable-userns" in cmd
        # stdin bir boru — asla operatör TTY'si veya miras host stdin'i değil;
        # payload tarafında sarmalayıcı /dev/null'a çevirir. Cgroup
        # sarmalayıcısı stdin'i okumaz; exec ile iç sarmalayıcıya taşır.
        assert stdin_is_pipe, f"stdin {stdin!r} is not the sentinel pipe"
        assert preexec is _join_fresh_session_keyring
        wrapper = next(
            part
            for part in cmd
            if isinstance(part, str) and "exec </dev/null" in part
        )
        assert ">&0;" in wrapper


def test_start_sentinel_wrapper_is_dash_safe() -> None:
    """Sarmalayıcı yalnız TEK haneli fd (0) kullanır — dash `Bad fd number`
    riskini taşıyan çok haneli redirection içeremez (6108e84/ac642ca dersleri:
    numaralı sentinel fd, fd tablosu doluyken sandbox'ı kalıcı düşürüyordu)."""
    from lumos_board.observer_sandbox import _with_start_sentinel

    wrapped, needle = _with_start_sentinel(["/bin/true"])
    script = wrapped[2]
    assert ">&0;" in script
    assert "exec </dev/null;" in script
    assert not re.search(r">&\d{2,}", script), script
    assert needle.startswith(b"lumos-sandbox-start-")


def test_cgroup_enter_wrapper_is_dash_safe() -> None:
    """Cgroup enter script must not use multi-digit fd redirects (same dash trap)."""
    from lumos_board.observer_sandbox import (
        _CGROUP_ENTER_SCRIPT,
        _into_cgroup_command,
    )

    cmd = _into_cgroup_command(Path("/sys/fs/cgroup/x"), ["prlimit", "--", "bwrap"])
    assert cmd[0] == "/bin/sh"
    assert cmd[2] == _CGROUP_ENTER_SCRIPT
    assert "cgroup.procs" in _CGROUP_ENTER_SCRIPT
    assert "$1" in _CGROUP_ENTER_SCRIPT
    assert not re.search(r">&\d{2,}", _CGROUP_ENTER_SCRIPT)
    assert not re.search(r"\$\d{2,}", _CGROUP_ENTER_SCRIPT)


def test_pidns_reaper_command_is_dash_safe() -> None:
    from lumos_board.observer_sandbox import _pidns_reaper_command

    cmd = _pidns_reaper_command(["prlimit", "--", "bwrap"])
    if shutil.which("unshare") is None:
        assert cmd[0] == "prlimit"
        return
    assert Path(cmd[0]).name == "unshare"
    assert "--kill-child" in cmd
    assert "--pid" in cmd
    assert "--mount-proc" in cmd
    assert "--" in cmd
    assert not re.search(r">&\d{2,}", " ".join(cmd))


def test_pidns_reaper_procfs_matches_inner_pid() -> None:
    """Bugbot High on 10f0b570: without --mount-proc, /proc/<inner-pid> is
    a different host task (measured: pid 1 → tini). bwrap then writes the
    wrong uid_map and the jail never starts."""
    from lumos_board.observer_sandbox import _pidns_reaper_command

    if shutil.which("unshare") is None:
        pytest.skip("unshare required")
    code = (
        "import os, pathlib, sys\n"
        "pid = os.getpid()\n"
        "self_comm = pathlib.Path('/proc/self/comm').read_text().strip()\n"
        "by_pid = pathlib.Path(f'/proc/{pid}/comm').read_text().strip()\n"
        "print(pid, self_comm, by_pid)\n"
        "sys.exit(0 if self_comm == by_pid else 2)\n"
    )
    cmd = _pidns_reaper_command([sys.executable, "-c", code])
    proc = subprocess.run(cmd, capture_output=True, timeout=5, check=False, text=True)
    if proc.returncode not in (0, 2):
        pytest.skip(f"unshare pid ns unavailable: {proc.stderr[:200]!r}")
    assert proc.returncode == 0, proc.stdout
    parts = proc.stdout.split()
    assert len(parts) >= 3
    assert parts[1] == parts[2]


def test_pidns_reaper_reaps_setsid_daemon() -> None:
    """Bugbot High on 1e792a13: timeout without cgroup left setsid children."""
    from lumos_board.observer_sandbox import _pidns_reaper_command

    if shutil.which("unshare") is None:
        pytest.skip("unshare required")
    probe = _pidns_reaper_command(["/bin/true"])
    probed = subprocess.run(probe, capture_output=True, timeout=5, check=False)
    if probed.returncode != 0:
        pytest.skip(f"unshare pid ns unavailable: {probed.stderr[:200]!r}")

    token = f"lumos-pidns-{os.getpid()}-{os.urandom(4).hex()}"
    inner = (
        "import os,time\n"
        "os.fork()==0 and (os.setsid() or time.sleep(30) or os._exit(0))\n"
        "time.sleep(30)\n"
        f"# {token}\n"
    )
    cmd = _pidns_reaper_command([sys.executable, "-c", inner])
    proc = subprocess.Popen(cmd)
    try:
        time.sleep(0.4)

        def _hits() -> list[int]:
            found: list[int] = []
            needle = token.encode("ascii")
            for entry in Path("/proc").glob("[0-9]*"):
                try:
                    cmdline = (entry / "cmdline").read_bytes()
                except OSError:
                    continue
                if needle in cmdline and entry.name != str(os.getpid()):
                    found.append(int(entry.name))
            return found

        before = _hits()
        assert before, "setsid daemon never appeared"
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=2)
        time.sleep(0.4)
        after = _hits()
        assert after == [], after
    finally:
        if proc.poll() is None:
            try:
                os.kill(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            proc.wait(timeout=2)


def test_fresh_session_keyring_hides_parent_user_key() -> None:
    """Security Review Medium on 4b92706f: @s is not isolated by setsid."""
    import ctypes

    from lumos_board.observer_sandbox import (
        _SYS_KEYCTL,
        _join_fresh_session_keyring,
    )

    nr = _SYS_KEYCTL.get(os.uname().machine)
    if nr is None:
        pytest.skip(f"keyctl unsupported on {os.uname().machine}")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    KEYCTL_SEARCH = 10
    KEY_SPEC_SESSION_KEYRING = -3
    SYS_add_key = {"x86_64": 248, "aarch64": 217}.get(os.uname().machine)
    if SYS_add_key is None:
        pytest.skip("add_key syscall unknown")
    desc = f"lumos-obs-key-{os.urandom(6).hex()}"
    ctypes.set_errno(0)
    added = libc.syscall(
        ctypes.c_long(SYS_add_key),
        b"user",
        desc.encode("ascii"),
        b"sekrit",
        ctypes.c_long(6),
        ctypes.c_long(KEY_SPEC_SESSION_KEYRING),
    )
    if added < 0:
        pytest.skip(f"add_key failed errno={ctypes.get_errno()}")

    def _search() -> int:
        ctypes.set_errno(0)
        return int(
            libc.syscall(
                ctypes.c_long(nr),
                ctypes.c_long(KEYCTL_SEARCH),
                ctypes.c_long(KEY_SPEC_SESSION_KEYRING),
                b"user",
                desc.encode("ascii"),
                ctypes.c_long(0),
            )
        )

    assert _search() > 0
    code = (
        "import ctypes, os, sys\n"
        "from lumos_board.observer_sandbox import _join_fresh_session_keyring\n"
        "os.setsid()\n"
        f"desc = {desc!r}.encode()\n"
        "nr = {'x86_64': 250, 'aarch64': 219}[os.uname().machine]\n"
        "libc = ctypes.CDLL(None, use_errno=True)\n"
        "libc.syscall.restype = ctypes.c_long\n"
        "ctypes.set_errno(0)\n"
        "ret = libc.syscall(nr, 10, ctypes.c_long(-3), b'user', desc, 0)\n"
        "print(int(ret), ctypes.get_errno())\n"
        "sys.exit(0 if int(ret) < 0 else 3)\n"
    )
    visible = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert visible.returncode == 3, visible.stdout
    hidden = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
        preexec_fn=_join_fresh_session_keyring,
    )
    assert hidden.returncode == 0, hidden.stdout
    # After join, SEARCH @s is ENOKEY (126). After seccomp, keyctl is EPERM (1).
    # Either proves the parent user key is not readable; EPERM is the Medium fix.
    assert hidden.stdout.split()[1] in {"1", "126"}


def test_user_keyring_not_searchable_after_preexec() -> None:
    """Security Review Medium on 35d48bf7: JOIN leaves @u live; seccomp EPERMs it.

    Must not KEYCTL_CLEAR @u — that mutates the observer's keys.
    """
    import ctypes

    from lumos_board.observer_sandbox import (
        _SYS_KEYCTL,
        _join_fresh_session_keyring,
        _keyctl_join_raw,
    )

    nr = _SYS_KEYCTL.get(os.uname().machine)
    if nr is None:
        pytest.skip(f"keyctl unsupported on {os.uname().machine}")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    SYS_add_key = {"x86_64": 248, "aarch64": 217}.get(os.uname().machine)
    if SYS_add_key is None:
        pytest.skip("add_key syscall unknown")
    desc = f"lumos-obs-ukey-{os.urandom(6).hex()}"
    ctypes.set_errno(0)
    added = libc.syscall(
        ctypes.c_long(SYS_add_key),
        b"user",
        desc.encode("ascii"),
        b"sekrit",
        ctypes.c_long(6),
        ctypes.c_long(-4),  # KEY_SPEC_USER_KEYRING
    )
    if added < 0:
        pytest.skip(f"add_key @u failed errno={ctypes.get_errno()}")

    code = (
        "import ctypes, os, sys\n"
        f"desc = {desc!r}.encode()\n"
        "nr = {'x86_64': 250, 'aarch64': 219}[os.uname().machine]\n"
        "libc = ctypes.CDLL(None, use_errno=True)\n"
        "libc.syscall.restype = ctypes.c_long\n"
        "def search(spec):\n"
        "    ctypes.set_errno(0)\n"
        "    ret = int(libc.syscall(nr, 10, ctypes.c_long(spec), b'user', desc, 0))\n"
        "    return ret, ctypes.get_errno()\n"
        "u, s = search(-4), search(-3)\n"
        "print(u[0], u[1], s[0], s[1])\n"
        "sys.exit(0 if u[0] < 0 and s[0] < 0 else 3)\n"
    )
    visible = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert visible.returncode == 3, visible.stdout

    join_only = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
        preexec_fn=_keyctl_join_raw,
    )
    assert join_only.returncode == 3, join_only.stdout  # Medium: @u still live

    hidden = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
        preexec_fn=_join_fresh_session_keyring,
    )
    assert hidden.returncode == 0, hidden.stdout
    parts = hidden.stdout.split()
    assert parts[1] == "1"  # EPERM on @u
    assert parts[3] == "1"  # EPERM on @s


def test_key_seccomp_filter_denies_x32_syscall_bit() -> None:
    """Bugbot Medium on 5989489a: x32 keeps AUDIT_ARCH_X86_64, sets bit 30."""
    from lumos_board.observer_sandbox import (
        _BPF_JMP_JSET_K,
        _SECCOMP_KEEP,
        _X32_SYSCALL_BIT,
    )

    keep = _SECCOMP_KEEP
    assert keep is not None
    arr, _prog = keep
    assert any(
        ins.code == _BPF_JMP_JSET_K and ins.k == _X32_SYSCALL_BIT for ins in arr
    )


def test_x32_keyctl_not_readable_after_preexec() -> None:
    """x32 keyctl must not SEARCH @u after join+seccomp."""
    import ctypes

    from lumos_board.observer_sandbox import (
        _SYS_KEYCTL,
        _X32_SYSCALL_BIT,
        _join_fresh_session_keyring,
    )

    nr = _SYS_KEYCTL.get(os.uname().machine)
    if nr is None:
        pytest.skip(f"keyctl unsupported on {os.uname().machine}")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    SYS_add_key = {"x86_64": 248, "aarch64": 217}.get(os.uname().machine)
    if SYS_add_key is None:
        pytest.skip("add_key syscall unknown")
    desc = f"lumos-obs-x32-{os.urandom(6).hex()}"
    ctypes.set_errno(0)
    added = libc.syscall(
        ctypes.c_long(SYS_add_key),
        b"user",
        desc.encode("ascii"),
        b"sekrit",
        ctypes.c_long(6),
        ctypes.c_long(-4),
    )
    if added < 0:
        pytest.skip(f"add_key @u failed errno={ctypes.get_errno()}")

    code = (
        "import ctypes, os, sys\n"
        f"desc = {desc!r}.encode()\n"
        f"nr = {nr}\n"
        f"x32 = {nr | _X32_SYSCALL_BIT}\n"
        "libc = ctypes.CDLL(None, use_errno=True)\n"
        "libc.syscall.restype = ctypes.c_long\n"
        "def search(n):\n"
        "    ctypes.set_errno(0)\n"
        "    ret = int(libc.syscall(ctypes.c_long(n), 10, ctypes.c_long(-4), b'user', desc, 0))\n"
        "    return ret, ctypes.get_errno()\n"
        "native, x32r = search(nr), search(x32)\n"
        "print(native[0], native[1], x32r[0], x32r[1])\n"
        "sys.exit(0 if native[0] < 0 and x32r[0] < 0 else 3)\n"
    )
    hidden = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
        preexec_fn=_join_fresh_session_keyring,
    )
    assert hidden.returncode == 0, hidden.stdout
    parts = hidden.stdout.split()
    assert parts[1] == "1"  # native keyctl EPERM
    assert parts[3] == "1"  # x32 bit caught by JSET, not kernel ENOSYS


def test_join_keyring_preexec_does_not_cdll_or_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bugbot Medium on b8302b77: CDLL after fork deadlocks; raise skips the turn."""
    import ast
    import inspect

    from lumos_board.observer_sandbox import (
        _block_key_syscalls,
        _join_fresh_session_keyring,
    )

    for fn in (_join_fresh_session_keyring, _block_key_syscalls):
        tree = ast.parse(inspect.getsource(fn))
        calls = [
            getattr(n.func, "attr", getattr(n.func, "id", None))
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
        ]
        assert "CDLL" not in calls, fn.__name__
        assert "uname" not in calls, fn.__name__
        assert not any(isinstance(n, ast.Raise) for n in ast.walk(tree)), fn.__name__

    def _boom(*_a: object, **_k: object) -> object:
        raise RuntimeError("CDLL after fork")

    monkeypatch.setattr("ctypes.CDLL", _boom)
    proc = subprocess.run(
        ["/bin/true"],
        preexec_fn=_join_fresh_session_keyring,
        timeout=5,
        check=False,
    )
    assert proc.returncode == 0


def test_join_keyring_eperm_is_noop_and_child_execs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bugbot Medium on b8302b77: keyctl EPERM must not become unavailable."""
    import errno

    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_keyctl_join_raw", lambda: (-1, errno.EPERM))
    monkeypatch.setattr(sandbox, "_keyctl_search_is_live", lambda: False)
    proc = subprocess.run(
        ["/bin/true"],
        preexec_fn=sandbox._join_fresh_session_keyring,
        timeout=5,
        check=False,
    )
    assert proc.returncode == 0


def test_join_keyring_edquot_aborts_when_seccomp_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bugbot Medium on 90acc2ec: join -1 with live SEARCH must not exec."""
    import errno

    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_keyctl_join_raw", lambda: (-1, errno.EDQUOT))
    monkeypatch.setattr(sandbox, "_keyctl_search_is_live", lambda: True)
    monkeypatch.setattr(sandbox, "_block_key_syscalls", lambda: errno.ENOSYS)
    proc = subprocess.run(
        ["/bin/true"],
        preexec_fn=sandbox._join_fresh_session_keyring,
        timeout=5,
        check=False,
    )
    assert proc.returncode != 0


def test_join_keyring_edquot_execs_when_seccomp_blocks_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failed join is OK once key syscalls cannot SEARCH inherited rings."""
    import errno

    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_keyctl_join_raw", lambda: (-1, errno.EDQUOT))
    monkeypatch.setattr(sandbox, "_block_key_syscalls", lambda: 0)
    proc = subprocess.run(
        ["/bin/true"],
        preexec_fn=sandbox._join_fresh_session_keyring,
        timeout=5,
        check=False,
    )
    assert proc.returncode == 0


def test_join_keyring_eacces_aborts_when_search_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bugbot Medium on 73928f52: EACCES is not a dead keyctl."""
    import errno

    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_keyctl_join_raw", lambda: (-1, errno.EACCES))
    monkeypatch.setattr(sandbox, "_keyctl_search_is_live", lambda: True)
    monkeypatch.setattr(sandbox, "_block_key_syscalls", lambda: errno.ENOSYS)
    proc = subprocess.run(
        ["/bin/true"],
        preexec_fn=sandbox._join_fresh_session_keyring,
        timeout=5,
        check=False,
    )
    assert proc.returncode != 0


def test_join_keyring_eacces_execs_when_search_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import errno

    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_keyctl_join_raw", lambda: (-1, errno.EACCES))
    monkeypatch.setattr(sandbox, "_keyctl_search_is_live", lambda: False)
    proc = subprocess.run(
        ["/bin/true"],
        preexec_fn=sandbox._join_fresh_session_keyring,
        timeout=5,
        check=False,
    )
    assert proc.returncode == 0


def test_keyctl_blocked_errnos_are_syscall_dead_only() -> None:
    import errno

    from lumos_board.observer_sandbox import _KEYCTL_BLOCKED

    assert _KEYCTL_BLOCKED == frozenset({errno.EPERM, errno.ENOSYS})
    assert errno.EACCES not in _KEYCTL_BLOCKED
    assert errno.ENOTSUP not in _KEYCTL_BLOCKED


def test_join_keyring_enomem_search_aborts_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bugbot Medium on f540ce92: SEARCH ENOMEM is not a dead keyctl."""
    import errno

    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_keyctl_join_raw", lambda: (-1, errno.ENOMEM))
    monkeypatch.setattr(sandbox, "_keyctl_raw", lambda *_a, **_k: (-1, errno.ENOMEM))
    monkeypatch.setattr(sandbox, "_block_key_syscalls", lambda: errno.ENOSYS)
    assert sandbox._keyctl_search_is_live() is True
    proc = subprocess.run(
        ["/bin/true"],
        preexec_fn=sandbox._join_fresh_session_keyring,
        timeout=5,
        check=False,
    )
    assert proc.returncode != 0


def test_keyctl_denial_does_not_skip_started_sandbox(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Blocked keyctl degrades (no preexec) instead of skip-closing the turn."""
    _stub_launcher(monkeypatch, tmp_path)
    import errno

    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_probe_join_errno", lambda: errno.EPERM)

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        command = list(args[0] if args else kwargs["args"])
        _write_start_sentinel(command, kwargs.get("stdin"))
        assert kwargs.get("preexec_fn") is None
        kwargs["stdout"].write(b"")
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])
    assert result.returncode == 0


def test_probe_seccomp_enosys_live_search_is_unavailable(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Seccomp ENOSYS with SEARCH live must fail-closed, not degrade."""
    _stub_launcher(monkeypatch, tmp_path)
    import errno

    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_block_key_syscalls", lambda: errno.ENOSYS)
    monkeypatch.setattr(sandbox, "_keyctl_search_is_live", lambda: True)
    with pytest.raises(SandboxUnavailableError, match="inherited @s"):
        run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])


def test_keyctl_join_edquot_is_unavailable(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Join failed with SEARCH still live → skip-closed, not inherited @s."""
    _stub_launcher(monkeypatch, tmp_path)
    import errno

    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_probe_join_errno", lambda: errno.EDQUOT)
    with pytest.raises(SandboxUnavailableError, match="inherited @s"):
        run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])


def test_probe_sigsys_degrades_not_skip(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bugbot Medium on 73928f52: probe SIGSYS is blocked keyctl, not EINVAL skip."""
    _stub_launcher(monkeypatch, tmp_path)
    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox.os, "fork", lambda: 4242)

    def _waitpid(pid: int, flags: int) -> tuple[int, int]:
        assert pid == 4242
        return pid, int(signal.SIGSYS)

    monkeypatch.setattr(sandbox.os, "waitpid", _waitpid)

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        command = list(args[0] if args else kwargs["args"])
        _write_start_sentinel(command, kwargs.get("stdin"))
        assert kwargs.get("preexec_fn") is None
        kwargs["stdout"].write(b"")
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])
    assert result.returncode == 0


def test_probe_hang_degrades_not_block(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bugbot Medium on 73928f52: waitpid is bounded and does not skip."""
    _stub_launcher(monkeypatch, tmp_path)
    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_PROBE_WAIT_S", 0.04)
    monkeypatch.setattr(sandbox, "_PROBE_SLICE_S", 0.01)
    monkeypatch.setattr(sandbox.os, "fork", lambda: 4242)
    killed: list[tuple[int, int]] = []

    def _waitpid(pid: int, flags: int) -> tuple[int, int]:
        if flags == os.WNOHANG:
            return 0, 0
        return pid, int(signal.SIGKILL)

    monkeypatch.setattr(sandbox.os, "waitpid", _waitpid)
    monkeypatch.setattr(
        sandbox.os, "kill", lambda pid, sig: killed.append((pid, sig))
    )

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        command = list(args[0] if args else kwargs["args"])
        _write_start_sentinel(command, kwargs.get("stdin"))
        assert kwargs.get("preexec_fn") is None
        kwargs["stdout"].write(b"")
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])
    assert result.returncode == 0
    assert killed == [(4242, signal.SIGKILL)]


def test_probe_timeout_honours_late_success_status(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bugbot Medium on f540ce92: timeout must not discard an already-exited child."""
    _stub_launcher(monkeypatch, tmp_path)
    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_PROBE_WAIT_S", 0.04)
    monkeypatch.setattr(sandbox, "_PROBE_SLICE_S", 0.01)
    monkeypatch.setattr(sandbox.os, "fork", lambda: 4242)

    def _waitpid(pid: int, flags: int) -> tuple[int, int]:
        if flags == os.WNOHANG:
            return 0, 0
        return pid, 0  # WIFEXITED 0 — join succeeded before SIGKILL landed

    monkeypatch.setattr(sandbox.os, "waitpid", _waitpid)
    monkeypatch.setattr(sandbox.os, "kill", lambda *_a: None)

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        command = list(args[0] if args else kwargs["args"])
        _write_start_sentinel(command, kwargs.get("stdin"))
        assert kwargs.get("preexec_fn") is sandbox._join_fresh_session_keyring
        kwargs["stdout"].write(b"")
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])
    assert result.returncode == 0


def test_probe_timeout_honours_late_fail_closed_status(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_launcher(monkeypatch, tmp_path)
    import errno

    import lumos_board.observer_sandbox as sandbox

    monkeypatch.setattr(sandbox, "_PROBE_WAIT_S", 0.04)
    monkeypatch.setattr(sandbox, "_PROBE_SLICE_S", 0.01)
    monkeypatch.setattr(sandbox.os, "fork", lambda: 4242)

    def _waitpid(pid: int, flags: int) -> tuple[int, int]:
        if flags == os.WNOHANG:
            return 0, 0
        return pid, errno.EDQUOT << 8

    monkeypatch.setattr(sandbox.os, "waitpid", _waitpid)
    monkeypatch.setattr(sandbox.os, "kill", lambda *_a: None)
    with pytest.raises(SandboxUnavailableError, match="inherited @s"):
        run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])


def test_nproc_limit_adds_private_headroom_to_current_uid_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lumos_board.observer_sandbox._current_uid_task_count", lambda: 100
    )
    from lumos_board.observer_sandbox import _resource_limited_command

    command = _resource_limited_command(["bwrap", "--help"], timeout=30)
    assert "--nproc=164:164" in command


def test_bwrap_launcher_uses_resolved_absolute_host_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_which = __import__("shutil").which

    def _which(name: str):
        if name == "bwrap":
            return "/opt/bubblewrap/bin/bwrap"
        return real_which(name)

    monkeypatch.setattr("lumos_board.observer_sandbox.shutil.which", _which)
    from lumos_board.observer_sandbox import _TMPFS_BYTES

    prefix = _bwrap_isolation_prefix()
    assert prefix[0] == "/opt/bubblewrap/bin/bwrap"
    assert "--dev" not in prefix
    assert "--disable-userns" in prefix
    assert prefix.index("--unshare-all") < prefix.index("--disable-userns")
    tmpfs_targets: list[str] = []
    for i, part in enumerate(prefix):
        if part == "--size":
            assert prefix[i + 1] == str(_TMPFS_BYTES)
            assert prefix[i + 2] == "--tmpfs"
            tmpfs_targets.append(prefix[i + 3])
    # Her yazılabilir tmpfs tavanlıdır; shm kendi mount'udur, /dev ro kalır.
    assert tmpfs_targets == ["/dev", "/dev/shm", "/tmp"]
    assert "--dev-bind" in prefix
    bind_at = prefix.index("--dev-bind")
    assert prefix[bind_at + 1].startswith("/dev/")
    assert "/dev/tty" not in prefix
    assert prefix[prefix.index("--remount-ro") + 1] == "/dev"


def test_setup_failure_without_sentinel_is_unavailable(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Launcher setup fail (no start nonce) is SandboxUnavailableError, not git."""
    _stub_launcher(monkeypatch, tmp_path)

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["stderr"].write(b"bwrap: Can't bind mount /nonexistent\n")
        return subprocess.CompletedProcess(args=args[0], returncode=1)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    with pytest.raises(SandboxUnavailableError, match="failed to start"):
        run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])


def test_git_child_failure_with_sentinel_is_result(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Git nonzero after the start nonce remains SandboxGitResult; nonce never
    reaches the caller-visible stderr (it travels on the stdin pipe)."""
    cg = _stub_launcher(monkeypatch, tmp_path)
    seen_cmd: list[list[str]] = []

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        command = list(args[0] if args else kwargs["args"])
        seen_cmd.append(command)
        _write_start_sentinel(command, kwargs.get("stdin"))
        from lumos_board.observer_sandbox import _join_fresh_session_keyring

        assert kwargs.get("preexec_fn") is _join_fresh_session_keyring
        kwargs["stderr"].write(b"fatal: not a git repository\n")
        return subprocess.CompletedProcess(args=command, returncode=128)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])
    assert result.returncode == 128
    assert "not a git repository" in result.stderr
    assert "lumos-sandbox-start" not in result.stderr
    assert seen_cmd
    assert any("cgroup.procs" in part for part in seen_cmd[0] if isinstance(part, str))
    assert str(cg) in seen_cmd[0]


def test_stderr_truncate_does_not_skip_started_sandbox(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bugbot Medium on b56d6c90: wiping stderr must not look like setup fail."""
    _stub_launcher(monkeypatch, tmp_path)

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        command = args[0] if args else kwargs["args"]
        _write_start_sentinel(command, kwargs.get("stdin"))
        # Hostile filter ftruncate()'d the inherited stderr file.
        kwargs["stderr"].write(b"")
        kwargs["stdout"].write(b"")
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])
    assert result.returncode == 0


def test_timeout_after_start_sentinel_is_result(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Security Review Medium on 6aef3d3f: sleep after nonce must not skip."""
    _stub_launcher(monkeypatch, tmp_path)

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        command = args[0] if args else kwargs["args"]
        _write_start_sentinel(command, kwargs.get("stdin"))
        kwargs["stderr"].write(b"filter still running\n")
        raise subprocess.TimeoutExpired(command, 0.05)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])
    assert result.returncode == 124
    assert "timed out" in result.stderr
    assert "lumos-sandbox-start" not in result.stderr


def test_timeout_before_start_sentinel_is_unavailable(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Timeout with no nonce is still a setup failure (jail never started)."""
    _stub_launcher(monkeypatch, tmp_path)

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        command = args[0] if args else kwargs["args"]
        kwargs["stderr"].write(b"bwrap: unshare failed\n")
        raise subprocess.TimeoutExpired(command, 0.05)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    with pytest.raises(
        SandboxUnavailableError, match="timed out before start sentinel"
    ):
        run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])


@needs_bwrap
def test_missing_prlimit_fails_closed(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_which = __import__("shutil").which

    def _which(name: str):
        if name == "prlimit":
            return None
        return real_which(name)

    monkeypatch.setattr("lumos_board.observer_sandbox.shutil.which", _which)
    with pytest.raises(SandboxUnavailableError, match="prlimit"):
        run_git_sandboxed(["status"], cwd=repo, allowed_roots=[repo])


@needs_bwrap
def test_nested_alternates_outside_root_not_readable(
    repo: Path, tmp_path: Path
) -> None:
    """§4.1 / §8.1 — real object in outside store; host sees it, sandbox must not.

    Previous test used a non-existent OID (always fails) → fake-green.
    """
    secret_repo = tmp_path / "secret-store"
    secret_repo.mkdir()
    _git(secret_repo, "init")
    _git(secret_repo, "config", "user.email", "t@example.com")
    _git(secret_repo, "config", "user.name", "t")
    (secret_repo / "secret.txt").write_text("SECRET_PAYLOAD\n", encoding="utf-8")
    _git(secret_repo, "add", "secret.txt")
    _git(secret_repo, "commit", "-m", "secret")
    blob = subprocess.run(
        ["git", "rev-parse", "HEAD:secret.txt"],
        cwd=secret_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    objects = (secret_repo / ".git" / "objects").resolve()

    alt = repo / ".git" / "objects" / "info"
    alt.mkdir(parents=True, exist_ok=True)
    (alt / "alternates").write_text(str(objects) + "\n", encoding="utf-8")

    # Host proves the escape hatch works when the store is visible.
    host = subprocess.run(
        ["git", "cat-file", "-p", blob],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert host.returncode == 0, host.stderr
    assert "SECRET_PAYLOAD" in host.stdout

    result = run_git_sandboxed(
        ["cat-file", "-p", blob],
        cwd=repo,
        allowed_roots=[repo],
    )
    assert result.returncode != 0
    assert "SECRET_PAYLOAD" not in result.stdout

    with pytest.raises(SandboxUnavailableError):
        run_git_sandboxed(
            ["status"],
            cwd=objects,
            allowed_roots=[repo],
        )


@needs_bwrap
def test_host_journal_path_not_writable_from_sandbox(
    repo: Path, tmp_path: Path
) -> None:
    """§4.5 — observation journal is host-side; sandbox cannot write it."""
    journal_dir = tmp_path / "operator-journal"
    journal_dir.mkdir()
    journal = journal_dir / "obs.jsonl"
    journal.write_text('{"host":true}\n', encoding="utf-8")
    before = journal.read_text(encoding="utf-8")

    # Attempt write via git commit is already covered; also ensure cwd jail
    # rejects using the journal dir as a root.
    with pytest.raises(SandboxUnavailableError):
        run_git_sandboxed(
            ["status"],
            cwd=journal_dir,
            allowed_roots=[repo],
        )
    assert journal.read_text(encoding="utf-8") == before


@needs_bwrap
def test_read_status_works_for_in_root_repo(repo: Path) -> None:
    result = run_git_sandboxed(
        ["status", "--porcelain"],
        cwd=repo,
        allowed_roots=[repo],
    )
    assert result.returncode == 0


@needs_bwrap
def test_tmpfs_is_size_capped(tmp_path: Path) -> None:
    """
    §3.2 — tmpfs sandbox'ın tek yazılabilir yüzeyidir ve TOPLAMI sınırlıdır.
    `fsize` dosya başınadır, `RLIMIT_AS` tmpfs sayfalarını saymaz; sınırsız
    tmpfs 1MiB'lik çok dosyayla host RAM'ini şişirmeye açıktı.
    """
    from lumos_board.observer_sandbox import _TMPFS_BYTES

    attempts = (_TMPFS_BYTES // (1024 * 1024)) + 6
    code = (
        "import sys\n"
        "n = 0\n"
        "try:\n"
        f"  for i in range({attempts}):\n"
        "    open(f'/tmp/f{i}', 'wb').write(b'x' * (1024 * 1024 - 4096)); n += 1\n"
        "except OSError:\n"
        "  pass\n"
        "print(n)\n"
    )
    proc = _bwrap_probe([_probe_interpreter(), "-c", code], timeout=60)
    written = int(proc.stdout.decode().strip() or "0")
    assert 0 < written < attempts, f"tmpfs sınırsız görünüyor: {written}/{attempts}"


@needs_bwrap
def test_dev_shm_is_size_capped(tmp_path: Path) -> None:
    """Security Review Medium on 0ed05a33 — /dev/shm is not an uncapped tmpfs."""
    from lumos_board.observer_sandbox import _TMPFS_BYTES

    attempts = (_TMPFS_BYTES // (1024 * 1024)) + 6
    code = (
        "n = 0\n"
        "try:\n"
        f"  for i in range({attempts}):\n"
        "    open(f'/dev/shm/f{i}', 'wb').write(b'x' * (1024 * 1024 - 4096)); n += 1\n"
        "except OSError:\n"
        "  pass\n"
        "print(n)\n"
    )
    proc = _bwrap_probe([_probe_interpreter(), "-c", code], timeout=60)
    written = int(proc.stdout.decode().strip() or "0")
    assert 0 < written < attempts, f"/dev/shm sınırsız görünüyor: {written}/{attempts}"


@needs_bwrap
def test_setup_failure_is_unavailable_but_git_error_is_a_result(repo: Path) -> None:
    """
    Kurulum hatası git hatası DEĞİLDİR: bwrap jail'i kuramazsa (bozuk bind,
    userns reddi) sonuç `SandboxUnavailableError` olmalı — sıfır-dışı çıkışlı
    sahte bir git sonucu değil. Gerçek git hatası ise normal sonuç kalır.
    `--info-fd` bu ayrımı veremiyor (bind hatasında bile info yazılıyor);
    ayrım başlangıç sentineliyle yapılır ve sentinel çağırana sızmaz.
    """
    from lumos_board.observer_sandbox import _bwrap_isolation_prefix, _run_bwrap_payload

    prefix = _bwrap_isolation_prefix() + [
        "--ro-bind", "/nonexistent-lumos-test-path", "/x",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/bin", "/bin",
    ]
    with pytest.raises(SandboxUnavailableError, match="failed to start"):
        _run_bwrap_payload(prefix, ["/bin/true"], timeout=15)

    result = run_git_sandboxed(
        ["rev-parse", "no-such-ref-xyz"], cwd=repo, allowed_roots=[repo]
    )
    assert result.returncode != 0  # git hatası: istisna değil, sonuç
    assert "lumos-sandbox-start" not in result.stderr
    ok = run_git_sandboxed(["status", "--porcelain"], cwd=repo, allowed_roots=[repo])
    assert ok.returncode == 0
    assert "lumos-sandbox-start" not in ok.stderr


@needs_bwrap
def test_start_sentinel_survives_hostile_payload(tmp_path: Path) -> None:
    """
    Bugbot Medium (b56d6c9): stderr temp dosyasındaki start nonce'u payload
    `ftruncate(2, 0)` ile silebiliyordu — CANLI sandbox "kurulamadı" sanılıp
    tur atlanıyordu; düşman repo kendi gözlemini bastırabilirdi. Nonce artık
    stdin olarak verilen boruya yazılır ve sarmalayıcı ucu payload exec'inden
    önce kapatır: boru truncate edilemez, payload'da yeniden açılacak fd
    kalmaz. Bu test iki saldırıyı birden dener (stderr truncate + fd tarayıp
    okuma) ve sonucun normal bir git-benzeri sonuç kaldığını doğrular.
    """
    hostile = [
        "/bin/sh",
        "-c",
        # 1) eski saldırı: paylaşılan stderr yakalama dosyasını sıfırla
        ": > /proc/self/fd/2; "
        # 2) yeni yüzey: miras kalan her fd'yi okuma modunda açıp boşaltmayı
        #    dene (boru drenajı) — sentinel borusu görünür olmamalı
        'for f in /proc/self/fd/*; do cat "$f" >/dev/null 2>&1; done; '
        "readlink /proc/self/fd/0; echo PAYLOAD-RAN",
    ]
    proc = _bwrap_probe(hostile, timeout=30)
    # Sandbox başladı ve saldırıya rağmen SONUÇ döndü — Unavailable değil.
    assert proc.returncode == 0
    out = proc.stdout.decode()
    assert "PAYLOAD-RAN" in out
    assert "/dev/null" in out  # payload stdin'i boru değil /dev/null


@needs_bwrap
def test_dev_root_is_readonly_but_device_nodes_still_write(tmp_path: Path) -> None:
    """
    /dev tavanlı OLMASI yetmez: dosya oluşturmaya da kapalıdır (remount-ro).
    Aygıt düğümüne yazmak fs yazması değildir; /dev/null çalışmayı sürdürür,
    ayrı mount olan /dev/shm yazılabilir kalır.
    """
    code = (
        "try:\n"
        "  open('/dev/evil', 'wb').write(b'x'); dev_write = True\n"
        "except OSError:\n"
        "  dev_write = False\n"
        "try:\n"
        "  open('/dev/null', 'wb').write(b'x'); devnull = True\n"
        "except OSError:\n"
        "  devnull = False\n"
        "try:\n"
        "  open('/dev/shm/ok', 'wb').write(b'x'); shm = True\n"
        "except OSError:\n"
        "  shm = False\n"
        "print(dev_write, devnull, shm)\n"
    )
    proc = _bwrap_probe([_probe_interpreter(), "-c", code], timeout=30)
    assert proc.stdout.decode().split() == ["False", "True", "True"]


@needs_cgroup
def test_memory_cgroup_sets_tree_budget() -> None:
    """Sibling cgroup receives memory.max = tree budget and swap.max = 0."""
    from lumos_board.observer_sandbox import (
        _MAX_TREE_MEMORY_BYTES,
        _sandbox_memory_cgroup,
    )

    with _sandbox_memory_cgroup() as cg:
        assert (cg / "memory.max").read_text(encoding="utf-8").strip() == str(
            _MAX_TREE_MEMORY_BYTES
        )
        swap = cg / "memory.swap.max"
        if swap.exists():
            assert swap.read_text(encoding="utf-8").strip() == "0"
        assert cg.is_dir()
    assert not cg.exists()


@needs_cgroup
def test_memory_cgroup_bounds_forked_anonymous_pages() -> None:
    """Security Review Medium on 6aef3d3f: RLIMIT_AS is per-process; tree RAM
    is cgroup memory.max. Eight children touching 20MiB each must not all
    survive a 32MiB tree cap (they would under a 1GiB per-task RLIMIT_AS)."""
    from lumos_board.observer_sandbox import (
        _into_cgroup_command,
        _sandbox_memory_cgroup,
    )

    alloc = (
        "import os, sys\n"
        "def hog():\n"
        "    buf = bytearray(20 * 1024 * 1024)\n"
        "    for i in range(0, len(buf), 4096):\n"
        "        buf[i] = 1\n"
        "    __import__('time').sleep(2)\n"
        "    os._exit(0)\n"
        "kids = []\n"
        "for _ in range(8):\n"
        "    pid = os.fork()\n"
        "    if pid == 0:\n"
        "        hog()\n"
        "    kids.append(pid)\n"
        "alive = 0\n"
        "for pid in kids:\n"
        "    w = os.waitpid(pid, 0)[1]\n"
        "    if os.WIFEXITED(w) and os.WEXITSTATUS(w) == 0:\n"
        "        alive += 1\n"
        "print(alive)\n"
        "sys.exit(0 if alive == 0 else 1)\n"
    )
    with _sandbox_memory_cgroup(limit_bytes=32 * 1024 * 1024) as cg:
        cmd = _into_cgroup_command(cg, [sys.executable, "-c", alloc])
        proc = subprocess.run(cmd, capture_output=True, timeout=10, check=False)
    # Tree is OOM-killed (SIGKILL / nonzero) rather than all eight hogs exiting 0.
    assert proc.returncode != 0
    if proc.stdout:
        alive = proc.stdout.decode().strip().splitlines()[-1]
        assert alive != "8"


@needs_bwrap
def test_observer_runs_when_cgroup_unavailable(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Option (a) graceful degrade: cgroup v2/delegation yoksa observer SUSMAZ.

    cgroup v1 hostta (ölçüldü) fail-closed, düşman hiçbir şey yapmadan her
    gözlem turunu atlatırdı. Delege memory controller yokken run_git_sandboxed
    per-process rlimit'lerle koşmaya devam etmeli — SandboxUnavailableError
    DEĞİL — ve launcher cgroup'a taşınmamalı (cgroup.procs komutta yok).
    """
    def _no_cgroup() -> Path:
        raise SandboxUnavailableError("forced: no delegated cgroup for test")

    monkeypatch.setattr(
        "lumos_board.observer_sandbox._memory_cgroup_insert_parent", _no_cgroup
    )

    real_run = subprocess.run
    seen: list[list[str]] = []

    def _wrap(*args, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(list(args[0] if args else kwargs.get("args") or []))
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _wrap)
    result = run_git_sandboxed(["status", "--porcelain"], cwd=repo, allowed_roots=[repo])
    assert result.returncode == 0  # observer çalıştı, tur atlanmadı
    launcher = next((c for c in seen if any("bwrap" in Path(p).name for p in c)), None)
    assert launcher is not None
    assert not any("cgroup.procs" in p for p in launcher), (
        "degrade modunda launcher cgroup'a taşınmamalı"
    )


@needs_bwrap
def test_timeout_after_start_is_result_real_bwrap(repo: Path) -> None:
    """Security Review Medium on 6aef3d3f (gerçek bwrap): repo-kontrollü bir
    clean filter wall-clock timeout'a kadar uyusa bile canlı jail'in sonucu
    setup-failure DEĞİL — SandboxGitResult (rc 124), tur atlanmaz. Böylece
    düşman filter timeout üzerinden her gözlem turunu bastıramaz."""
    (repo / ".gitattributes").write_text("hangme filter=sleeper\n", encoding="utf-8")
    (repo / "hangme").write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "hang")
    _git(repo, "config", "filter.sleeper.clean", "sleep 30")
    (repo / "hangme").write_text("v2\n", encoding="utf-8")  # unstaged: clean filter koşar

    result = run_git_sandboxed(
        ["diff", "--", "hangme"], cwd=repo, allowed_roots=[repo], timeout=3
    )
    assert result.returncode == 124  # SandboxUnavailableError DEĞİL: bir sonuç
    assert "timed out" in result.stderr
    assert "lumos-sandbox-start" not in result.stderr


def test_destroy_memory_cgroup_retries_until_rmdir_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bugbot Medium on c8b8c283: one-shot rmdir after cgroup.kill leaks."""
    from lumos_board.observer_sandbox import _destroy_memory_cgroup

    class _KillFile:
        def exists(self) -> bool:
            return True

        def write_text(self, *_args: object, **_kwargs: object) -> None:
            return None

    class _Cg:
        def __init__(self) -> None:
            self.rmdir_calls = 0

        def __truediv__(self, _name: str) -> _KillFile:
            return _KillFile()

        def is_dir(self) -> bool:
            return True

        def rmdir(self) -> None:
            self.rmdir_calls += 1
            if self.rmdir_calls < 3:
                raise OSError(16, "Device or resource busy")

    cg = _Cg()
    sleeps: list[float] = []
    monkeypatch.setattr("lumos_board.observer_sandbox.time.sleep", sleeps.append)
    _destroy_memory_cgroup(cg)  # type: ignore[arg-type]
    assert cg.rmdir_calls == 3
    assert sleeps == [0.05, 0.05]


def test_destroy_memory_cgroup_missing_dir_does_not_spin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """mkdir-failed degrade path must not wait the 2s destroy deadline."""
    from lumos_board.observer_sandbox import _destroy_memory_cgroup

    sleeps: list[float] = []
    monkeypatch.setattr("lumos_board.observer_sandbox.time.sleep", sleeps.append)
    _destroy_memory_cgroup(tmp_path / "lumos-obs-absent")
    assert sleeps == []


def test_try_create_memory_cgroup_degrades_when_undelegated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """cgroup v1 / no delegation: None, not SandboxUnavailableError."""
    from lumos_board.observer_sandbox import _try_create_memory_cgroup

    def _nope() -> Path:
        raise SandboxUnavailableError("no delegated cgroup memory controller")

    monkeypatch.setattr(
        "lumos_board.observer_sandbox._memory_cgroup_insert_parent", _nope
    )
    assert _try_create_memory_cgroup(None) is None


@needs_cgroup
def test_destroy_memory_cgroup_reaps_live_sleeper() -> None:
    """Live sleeper must not leave lumos-obs-* behind after destroy."""
    from lumos_board.observer_sandbox import (
        _MAX_TREE_MEMORY_BYTES,
        _destroy_memory_cgroup,
        _into_cgroup_command,
        _memory_cgroup_insert_parent,
    )

    parent = _memory_cgroup_insert_parent()
    cg = parent / f"lumos-reap-{os.getpid()}-{os.urandom(4).hex()}"
    cg.mkdir(mode=0o700)
    (cg / "memory.max").write_text(str(_MAX_TREE_MEMORY_BYTES), encoding="utf-8")
    proc = subprocess.Popen(_into_cgroup_command(cg, ["/bin/sleep", "30"]))
    try:
        for _ in range(40):
            try:
                if proc.pid in {
                    int(p)
                    for p in (cg / "cgroup.procs").read_text(encoding="utf-8").split()
                }:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.01)
        else:
            proc.kill()
            proc.wait(timeout=2)
            _destroy_memory_cgroup(cg)
            raise AssertionError("sleeper never entered the cgroup")
        _destroy_memory_cgroup(cg)
        assert not cg.exists(), "cgroup leaked after destroy"
    finally:
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
        if cg.exists():
            _destroy_memory_cgroup(cg)
            assert not cg.exists()
