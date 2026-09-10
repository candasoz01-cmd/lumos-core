"""§4 acceptance tests for Agent Wall observer sandbox MVP (ADR-033 / sandbox-v0).

Maps to `agent-wall-observer-sandbox-v0` §4 kabul ölçütleri — each criterion
needs a real (non-fake-green) proof below.
"""

from __future__ import annotations

import os
import socket
import stat
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from lumos_board.observer_sandbox import (
    SandboxUnavailableError,
    probe_sandbox_env,
    run_git_sandboxed,
    sandbox_backend,
    scrub_env_for_sandbox,
)

pytestmark = pytest.mark.skipif(
    __import__("shutil").which("bwrap") is None,
    reason="bubblewrap (bwrap) required for sandbox MVP tests",
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


def test_non_utf8_git_output_does_not_crash(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bugbot Medium: binary/non-UTF-8 stdout must not UnicodeDecodeError out."""
    real_run = subprocess.run

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs = dict(kwargs)
        # Force the production path (text=False) and inject non-UTF-8 bytes.
        result = real_run(*args, **kwargs)
        if kwargs.get("text") is True:
            raise AssertionError("run_git_sandboxed must not use text=True")
        if kwargs.get("stdin") is not subprocess.DEVNULL:
            raise AssertionError("run_git_sandboxed must pass stdin=DEVNULL")
        # Rebuild a CompletedProcess-like result with latin-1 bytes
        return subprocess.CompletedProcess(
            args=result.args,
            returncode=0,
            stdout=b"ok-\xff-binary\n",
            stderr=b"warn-\xfe\n",
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


def _bwrap_tcp_probe(port: int, *, unshare_net: bool, allowed_root: Path) -> int:
    """Same bind shape as the MVP motor; optional --unshare-net for contrast."""
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
    if unshare_net:
        cmd.append("--unshare-net")
    cmd += [
        "--chdir",
        str(allowed_root),
        "--clearenv",
        "--setenv",
        "PATH",
        "/usr/bin:/bin",
        "/usr/bin/python3",
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


def test_clean_filter_capability_denial(repo: Path, tmp_path: Path) -> None:
    """§4.1 — repo-controlled filter may run; capabilities outside sandbox denied.

    Helper lives *inside* allowed_roots (see sandbox-v0 §8.2 measurement error #2).
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


def test_sandbox_uses_new_session_and_devnull_stdin(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Always-on proof for TTY/session Medium (this host may have no /dev/tty)."""
    seen: list[tuple[list[str], object]] = []
    real_run = subprocess.run

    def _wrap(*args, **kwargs):  # type: ignore[no-untyped-def]
        cmd = list(args[0] if args else kwargs.get("args") or [])
        seen.append((cmd, kwargs.get("stdin")))
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _wrap)
    run_git_sandboxed(["status", "--porcelain"], cwd=repo, allowed_roots=[repo])
    probe_sandbox_env(allowed_roots=[repo], host_env=os.environ.copy())
    assert len(seen) >= 2
    for cmd, stdin in seen:
        assert cmd and cmd[0] == "bwrap"
        assert "--new-session" in cmd
        assert stdin is subprocess.DEVNULL


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


def test_read_status_works_for_in_root_repo(repo: Path) -> None:
    result = run_git_sandboxed(
        ["status", "--porcelain"],
        cwd=repo,
        allowed_roots=[repo],
    )
    assert result.returncode == 0
