"""Acceptance tests for Agent Wall observer sandbox MVP (sandbox-v0).

Bubblewrap integration tests skip when `bwrap` is absent. Unit checks for env
scrub and launcher construction still run so CI without bwrap is not silent.
"""

from __future__ import annotations

import os
import re
import shutil
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
    seen: list[tuple[list[str], object]] = []
    real_run = subprocess.run

    def _wrap(*args, **kwargs):  # type: ignore[no-untyped-def]
        cmd = list(args[0] if args else kwargs.get("args") or [])
        stdin = kwargs.get("stdin")
        stdin_is_pipe = isinstance(stdin, int) and stdin >= 0 and stat.S_ISFIFO(
            os.fstat(stdin).st_mode
        )
        seen.append((cmd, stdin, stdin_is_pipe))
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _wrap)
    run_git_sandboxed(["status", "--porcelain"], cwd=repo, allowed_roots=[repo])
    probe_sandbox_env(allowed_roots=[repo], host_env=os.environ.copy())
    assert len(seen) >= 2
    for cmd, stdin, stdin_is_pipe in seen:
        assert cmd and Path(cmd[0]).name == "sh"
        assert any("cgroup.procs" in part for part in cmd if isinstance(part, str))
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
        # stdin bir boru — asla operatör TTY'si veya miras host stdin'i değil;
        # payload tarafında sarmalayıcı /dev/null'a çevirir. Cgroup
        # sarmalayıcısı stdin'i okumaz; exec ile iç sarmalayıcıya taşır.
        assert stdin_is_pipe, f"stdin {stdin!r} is not the sentinel pipe"
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
