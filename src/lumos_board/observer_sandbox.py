"""Agent Wall observer — sandboxed git execution (sandbox-v0 MVP).

Primary boundary is a real low-privilege sandbox (bubblewrap on Linux).
In-process cwd/env jails are NOT sufficient.

This module does **not** wire Wall signals, claims, or control paths.
ADR-033 on main is Account Activity Correlation; this file is not that ADR.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

_LOG = logging.getLogger(__name__)

# Env keys that must never enter the sandbox (operator / agent credentials).
_BLOCKED_ENV_PREFIXES = (
    "SSH_",
    "AWS_",
    "GOOGLE_",
    "GH_",
    "GITHUB_",
    "OPENAI_",
    "ANTHROPIC_",
    "CURSOR_",
    "NPM_",
    "DOCKER_",
)
_BLOCKED_ENV_KEYS = frozenset(
    {
        "SSH_AUTH_SOCK",
        "SSH_AGENT_PID",
        "GPG_AGENT_INFO",
        "GNUPGHOME",
        "GIT_ASKPASS",
        "GIT_TERMINAL_PROMPT",
        "GIT_CONFIG_COUNT",
        "GIT_TRACE",
        "CURL_HOME",
        "NETRC",
        "LUMOS_OPERATOR_TOKEN",
        "LUMOS_API_TOKEN",
        "LUMOS_PANEL_TOKEN",
    }
)

_MAX_PROCESSES = 64
_MAX_OUTPUT_BYTES = 1024 * 1024
# Per-process secondary cap. Linux applies RLIMIT_AS per task, so this
# alone does not bound the jail tree (Security Review Medium on 6aef3d3f).
_MAX_ADDRESS_SPACE_BYTES = 1024 * 1024 * 1024
# Tree-wide anonymous+tmpfs+cache budget via cgroup v2 memory.max.
_MAX_TREE_MEMORY_BYTES = 1024 * 1024 * 1024
# Writable tmpfs surfaces (/tmp and /dev, including /dev/shm). `fsize` is
# per-file; `RLIMIT_AS` does not count tmpfs pages. Uncapped tmpfs let a
# filter fill host RAM with many 1MiB files (Security Review Medium on
# 0ed05a33 for /dev; Bugbot Medium on d2afc6c6 for /tmp).
_TMPFS_BYTES = 64 * 1024 * 1024
_DEV_NODES = ("null", "zero", "full", "urandom", "random")
_TIMEOUT_EXIT_CODE = 124
_TIMEOUT_MARKER = b"\n[observer sandbox timed out]\n"
_OUTPUT_LIMIT_EXIT_CODE = 125
_OUTPUT_LIMIT_MARKER = b"\n[observer sandbox output limit reached]\n"
# cgroup.kill delivers SIGKILL but does not wait for the cgroup to empty.
# Immediate rmdir then leaks lumos-obs-* dirs after a wall-clock timeout
# (Bugbot Medium on c8b8c283).
_CGROUP_DESTROY_TIMEOUT = 2.0
_CGROUP_DESTROY_SLICE = 0.05
# Host-side only: move the launcher pid into the sandbox memory cgroup
# before exec. Dash-safe ($1, no multi-digit fd). Must not read stdin —
# fd 0 is the start-sentinel pipe for the inner wrapper.
_CGROUP_ENTER_SCRIPT = 'printf "%s\\n" $$ > "$1/cgroup.procs" && shift && exec "$@"'


class SandboxUnavailableError(RuntimeError):
    """Sandbox cannot be constructed — fail closed (skip observation turn)."""


@dataclass(frozen=True)
class SandboxGitResult:
    returncode: int
    stdout: str
    stderr: str


def sandbox_backend() -> str:
    """Return the concrete motor name, or raise if none usable."""
    _bwrap_path()
    return "bubblewrap"


def _bwrap_path() -> str:
    """Resolve bwrap before the launcher environment drops the host PATH."""
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise SandboxUnavailableError(
            "no sandbox motor available (need bubblewrap/bwrap on PATH)"
        )
    return bwrap


def _is_blocked_env(key: str) -> bool:
    if key in _BLOCKED_ENV_KEYS:
        return True
    return any(key.startswith(p) for p in _BLOCKED_ENV_PREFIXES)


def scrub_env_for_sandbox(src: dict[str, str] | None = None) -> dict[str, str]:
    """Build the minimal env that may enter the sandbox.

    ``src`` is accepted for tests that pretend to be a hostile host env; nothing
    from it is copied except non-secret locale hints.
    """
    raw = src if src is not None else os.environ
    # Never copy host env wholesale — only locale, and only if not blocked.
    lang = raw.get("LANG", "C.UTF-8")
    lc_all = raw.get("LC_ALL", "C.UTF-8")
    if _is_blocked_env("LANG"):
        lang = "C.UTF-8"
    if _is_blocked_env("LC_ALL"):
        lc_all = "C.UTF-8"
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": "/tmp/lumos-observer-home",
        "LANG": lang,
        "LC_ALL": lc_all,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "/bin/false",
    }


def _bind_ro_args(host: Path, guest: str | None = None) -> list[str]:
    target = guest if guest is not None else str(host)
    return ["--ro-bind", str(host), target]


def _size_capped_tmpfs(dest: str) -> list[str]:
    return ["--size", str(_TMPFS_BYTES), "--tmpfs", dest]


def _dev_jail_args() -> list[str]:
    """Capped ``/dev`` plus the device nodes git needs; no host ``/dev/tty``.

    ``--dev /dev`` is a writable tmpfs at kernel default size (~half RAM),
    including ``/dev/shm``. Overlaying only ``/dev/shm`` still leaves
    ``/dev/<other>`` uncapped, so ``--dev`` is replaced with a size-capped
    tmpfs and explicit ``--dev-bind`` of host nodes. ``/dev/tty`` is omitted
    on purpose (Security Review Medium on 2d56ed6 + 0ed05a33).
    """
    args = _size_capped_tmpfs("/dev")
    args += ["--dir", "/dev/shm"]
    # /dev/shm kendi tavanıyla AYRI, yazılabilir bir mount olarak bindirilir;
    # ardından /dev'in kendisi salt-okunur remount edilir (aşağıda, düğümler
    # ve symlink'ler yerleştirildikten sonra). Aygıt düğümüne yazmak fs
    # yazması değildir ve iç mount'lar kendi bayraklarını korur: sonuç,
    # /dev'de dosya oluşturulamaz, shm tavanlı ve yazılabilir kalır.
    for name in _DEV_NODES:
        host = Path("/dev") / name
        if host.exists():
            args += ["--dev-bind", str(host), f"/dev/{name}"]
    args += [
        "--symlink",
        "/proc/self/fd",
        "/dev/fd",
        "--symlink",
        "/proc/self/fd/0",
        "/dev/stdin",
        "--symlink",
        "/proc/self/fd/1",
        "/dev/stdout",
        "--symlink",
        "/proc/self/fd/2",
        "/dev/stderr",
    ]
    args += _size_capped_tmpfs("/dev/shm")
    args += ["--remount-ro", "/dev"]
    return args


def _bwrap_isolation_prefix() -> list[str]:
    """Shared jail flags: no net, new session, no inherited TTY.

    Device nodes git needs (``/dev/null``, urandom) come from ``_dev_jail_args``.
    Combined with ``--new-session`` so a repo-controlled filter cannot steal
    the operator controlling TTY (Security Review Medium on 2d56ed6). The
    child's stdin is never a host TTY either: it is the sentinel pipe's write
    end, which the wrapper swaps for ``/dev/null`` before the payload execs
    (``_with_start_sentinel``), or ``/dev/null`` directly when no sentinel.
    """
    return [
        _bwrap_path(),
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--proc",
        "/proc",
        *_dev_jail_args(),
        *_size_capped_tmpfs("/tmp"),
        "--dir",
        "/tmp/lumos-observer-home",
        "--cap-drop",
        "ALL",
    ]


def _current_uid_task_count() -> int:
    """Count host threads for this real UID before setting RLIMIT_NPROC."""
    uid = os.getuid()
    total = 0
    try:
        statuses = Path("/proc").glob("[0-9]*/status")
        for status in statuses:
            # Yalnız Uid/Threads okunur. Bütün dosyayı sözlüğe açmak kırılgandı:
            # ek grubu olmayan süreçte "Groups:\t " satırı tek parçaya bölünür,
            # unpacking ValueError'ı DOSYANIN TAMAMINI atlatır ve sayaç 0 kalıp
            # sandbox'ı bwrap kuruluyken bile kalıcı fail-closed'a kilitlerdi —
            # konteynerlerde bu satır olağandır.
            try:
                real_uid: int | None = None
                threads = 1
                for line in status.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines():
                    if line.startswith("Uid:"):
                        real_uid = int(line.split()[1])
                    elif line.startswith("Threads:"):
                        threads = int(line.split()[1])
                if real_uid == uid:
                    total += threads
            except (FileNotFoundError, IndexError, PermissionError, ValueError, OSError):
                continue
    except OSError as exc:
        raise SandboxUnavailableError(f"cannot count host tasks: {exc}") from exc
    if total < 1:
        raise SandboxUnavailableError("cannot count host tasks for RLIMIT_NPROC")
    return total


def _current_cgroup_path() -> Path:
    """Return this process's cgroup v2 directory under ``/sys/fs/cgroup``."""
    try:
        raw = Path("/proc/self/cgroup").read_text(encoding="utf-8")
    except OSError as exc:
        raise SandboxUnavailableError(f"cannot read /proc/self/cgroup: {exc}") from exc
    rel = None
    for line in raw.splitlines():
        if line.startswith("0::"):
            rel = line[3:]
            break
    if rel is None:
        lines = [line for line in raw.splitlines() if line.strip()]
        if not lines:
            raise SandboxUnavailableError("empty /proc/self/cgroup")
        rel = lines[-1].split(":")[-1]
    if not rel.startswith("/"):
        rel = "/" + rel
    return Path("/sys/fs/cgroup") / rel.lstrip("/")


def _memory_cgroup_insert_parent() -> Path:
    """Writable ancestor whose ``cgroup.subtree_control`` already lists memory.

    Children of that directory receive ``memory.max``. Enabling ``+memory`` on
    a populated cgroup is EBUSY, and a child of our own leaf would not get
    the controller, so we create a *sibling* of the observer cgroup.
    """
    current = _current_cgroup_path()
    node: Path | None = current
    while node is not None:
        subtree = node / "cgroup.subtree_control"
        try:
            writable = node.is_dir() and os.access(node, os.W_OK)
            controllers = (
                subtree.read_text(encoding="utf-8").split() if subtree.exists() else []
            )
        except OSError:
            writable = False
            controllers = []
        if writable and "memory" in controllers:
            return node
        if node == Path("/sys/fs/cgroup"):
            break
        parent = node.parent
        if parent == node:
            break
        node = parent
    raise SandboxUnavailableError(
        "no delegated cgroup memory controller for sandbox tree RAM cap"
    )


def _destroy_memory_cgroup(cg: Path) -> None:
    """Kill the jail tree and remove the cgroup; retry until empty.

    ``cgroup.kill`` is asynchronous: SIGKILL is posted, but tasks can still
    sit in ``cgroup.procs`` for a short window. A one-shot ``rmdir`` then
    fails and the directory leaks. A filter that always sleeps past the
    wall clock would accumulate ``lumos-obs-*`` cgroups until creation
    fails and later turns skip (Bugbot Medium on c8b8c283).
    """
    try:
        present = cg.is_dir()
    except OSError:
        return
    if not present:
        # mkdir never succeeded (degrade cleanup). Do not spin on rmdir
        # until _CGROUP_DESTROY_TIMEOUT.
        return
    kill = cg / "cgroup.kill"
    deadline = time.monotonic() + _CGROUP_DESTROY_TIMEOUT
    while True:
        if kill.exists():
            try:
                kill.write_text("1", encoding="utf-8")
            except OSError:
                pass
        try:
            cg.rmdir()
            return
        except OSError:
            if time.monotonic() >= deadline:
                return
            time.sleep(_CGROUP_DESTROY_SLICE)


@contextmanager
def _sandbox_memory_cgroup(
    *, limit_bytes: int | None = None
) -> Iterator[Path | None]:
    """Gerçek tree ``memory.max`` (cgroup v2 delege memory controller varsa),
    yoksa ``None`` — graceful degrade, per-process rlimit'lerle devam.

    Fail-closed DEĞİLDİR. cgroup v2/delegation olmayan bir hostta (ör. cgroup
    v1, ölçüldü) toplam-RAM tavanı kurulamıyor diye observer'ı komple
    susturmak, düşman hiçbir şey yapmadan HER gözlem turunu atlatırdı —
    timeout bulgusunun (6aef3d3) çözdüğü observation-skip sınıfının koşulsuz
    ve daha kötü hali. Bu yüzden cap uygulanamadığında ``None`` döner,
    ``_resource_limited_command``'ın per-process ``--as``/``nproc`` sınırları
    yürür ve residual risk WARNING olarak kaydedilir. Sahte bir "toplam limit"
    İDDİA edilmez; yalnızca o turda tree-RAM tavanı yoktur (Security Review
    Medium on 6aef3d3f; option (a): gerçek cgroup varsa uygula, yoksa degrade).
    """
    cg = _try_create_memory_cgroup(limit_bytes)
    try:
        yield cg
    finally:
        if cg is not None:
            _destroy_memory_cgroup(cg)


def _try_create_memory_cgroup(limit_bytes: int | None) -> Path | None:
    """Sibling cgroup + ``memory.max``; kurulamıyorsa None (degrade), asla raise."""
    try:
        parent = _memory_cgroup_insert_parent()
    except SandboxUnavailableError as exc:
        _LOG.warning(
            "observer sandbox tree-RAM cgroup unavailable (%s); degrading to "
            "per-process rlimits only — no total-RAM cap this run",
            exc,
        )
        return None
    name = f"lumos-obs-{os.getpid()}-{os.urandom(6).hex()}"
    cg = parent / name
    try:
        cg.mkdir(mode=0o700)
        budget = _MAX_TREE_MEMORY_BYTES if limit_bytes is None else limit_bytes
        (cg / "memory.max").write_text(str(budget), encoding="utf-8")
        swap = cg / "memory.swap.max"
        if swap.exists():
            swap.write_text("0", encoding="utf-8")
        oom = cg / "memory.oom.group"
        if oom.exists():
            try:
                oom.write_text("1", encoding="utf-8")
            except OSError:
                pass
        return cg
    except OSError as exc:
        _LOG.warning(
            "observer sandbox cgroup memory.max not applied (%s); degrading to "
            "per-process rlimits only — no total-RAM cap this run",
            exc,
        )
        _destroy_memory_cgroup(cg)
        return None


def _into_cgroup_command(cgroup: Path, command: Sequence[str]) -> list[str]:
    """Host wrapper: move this pid into ``cgroup`` then exec ``command``."""
    return [
        "/bin/sh",
        "-c",
        _CGROUP_ENTER_SCRIPT,
        "lumos-cgroup",
        str(cgroup),
        *command,
    ]


def _resource_limited_command(command: Sequence[str], *, timeout: float) -> list[str]:
    """Wrap the sandbox launcher in host-enforced *per-process* rlimits.

    Tree-wide RAM is ``cgroup memory.max`` (``_sandbox_memory_cgroup``), not
    ``RLIMIT_AS``: the latter is per task and ``nproc`` extra forks can still
    sum to tens of GiB (Security Review Medium on 6aef3d3f).
    """
    prlimit = shutil.which("prlimit")
    if not prlimit:
        raise SandboxUnavailableError("prlimit not found on host PATH")
    cpu_soft = max(1, int(timeout) + 1)
    nproc_limit = _current_uid_task_count() + _MAX_PROCESSES
    return [
        prlimit,
        f"--nproc={nproc_limit}:{nproc_limit}",
        f"--fsize={_MAX_OUTPUT_BYTES}:{_MAX_OUTPUT_BYTES}",
        f"--as={_MAX_ADDRESS_SPACE_BYTES}:{_MAX_ADDRESS_SPACE_BYTES}",
        f"--cpu={cpu_soft}:{cpu_soft + 1}",
        "--",
        *command,
    ]


def _bounded_file_bytes(handle) -> tuple[bytes, bool]:  # type: ignore[no-untyped-def]
    size = handle.tell()
    handle.seek(0)
    return handle.read(_MAX_OUTPUT_BYTES), size >= _MAX_OUTPUT_BYTES


def _with_start_sentinel(payload: Sequence[str]) -> tuple[list[str], bytes]:
    """Payload'ı, jail kurulunca nonce'u sentinel kanalına basan sarmalayıcıya al.

    Kurulum hatası git hatası DEĞİLDİR: bwrap exec olup jail'i kuramadan
    çökerse (bind hatası, userns reddi) sıfır-dışı çıkış normal bir git
    sonucu gibi dönüyordu ve sözleşmenin "sandbox kurulamadı → tur atlanır"
    semantiği kayboluyordu. bwrap'ın `--info-fd`'si bu ayrımı VEREMEZ —
    ölçüldü: bind hatasında bile info verisi yazılıyor. Tek güvenilir işaret
    payload'ın kendisinin başlamasıdır: jail içinde, komuttan hemen önce,
    çağrı başına rastgele bir nonce basılır. Nonce görülmediyse sandbox hiç
    başlamamıştır; kurulum başarısızsa düşman kod hiç çalışmaz, taklit edemez.

    Kanal seçimi de düşmanca doğrulandı; üç tasarım ELENDİ:

    - stderr temp dosyası: payload aynı dosyayı fd 2'den miras alır ve
      `ftruncate` ile nonce'u SİLEBİLİR — canlı sandbox "kurulamadı" sanılır
      ve gözlem turu atlanır (Bugbot Medium, b56d6c9; repro'landı).
    - `pass_fds` ile geçirilen numaralı fd (temp dosyası veya boru):
      dash yalnız TEK haneli fd redirection'ı kabul eder; fd ≥ 10'da
      (dolu fd tablosu olan her gerçek süreçte olağan) `Bad fd number`
      sözdizimi hatası payload'ı hiç koşturmaz ve sandbox kalıcı
      "unavailable" olur — fd 13 ile ölçüldü. `preexec_fn` + `dup2` ile
      fd'yi 3'e sabitlemek de kurtarmaz: CPython `preexec_fn`'i
      `close_fds`'ten ÖNCE çağırır ve `pass_fds`'te olmayan fd 3 sonra
      kapatılır — `sh: 3: Bad file descriptor` ölçüldü; yalnız temp
      dosyası şans eseri fd 3'e düşerse çalışır.
    - fd'yi exec'ten önce KAPATMAYAN her sürüm: boru truncate edilemez ama
      payload `/proc/self/fd/<N>`'i OKUMA modunda yeniden açıp nonce'u
      boşaltabilir (repro'landı).

    Kalan tek sızdırmaz kanal: borunun yazma ucu çocuğa STDIN (fd 0) olarak
    verilir; sarmalayıcı nonce'u fd 0'a yazar ve `exec </dev/null` ile ucu
    payload exec'inden ÖNCE kapatır. Payload'da boruya açık hiçbir fd kalmaz
    (`/proc/self/fd` üzerinden yeniden açılamaz), stdin yine /dev/null olur —
    fd 0 tek hanelidir, dash kısıtına takılmaz. `/dev/null` jail'de
    `_dev_jail_args` ile garantidir.
    """
    nonce = f"lumos-sandbox-start-{os.urandom(12).hex()}"
    wrapped = [
        "/bin/sh",
        "-c",
        f'echo {nonce} >&0; exec </dev/null; exec "$@"',
        "sh",
        *payload,
    ]
    return wrapped, (nonce + "\n").encode("ascii")


def _run_bwrap_limited(
    command: Sequence[str],
    *,
    timeout: float,
    start_sentinel: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run bwrap without pipe-backed, unbounded capture buffers.

    Wall-clock timeout after the start nonce is a *git-side* hang, not a
    setup failure: ``SandboxUnavailableError`` skips the observation turn,
    which a hostile ``sleep`` would use to suppress every run (Security
    Review Medium on 6aef3d3f). Missing nonce + timeout still means the
    jail never started.
    """
    # Sentinel kanalı: yazma ucu çocuğa stdin olarak gider, sarmalayıcı onu
    # payload'dan önce kapatır (_with_start_sentinel). Payload'a hiçbir zaman
    # boru fd'si ulaşmaz; boruya yazılmış nonce ise silinemez. Cgroup
    # sarmalayıcısı stdout/stderr/stdin'i exec ile korur; stdin'i okumaz.
    sentinel_read = sentinel_write = -1
    if start_sentinel is not None:
        sentinel_read, sentinel_write = os.pipe()
    try:
        limited_command = _resource_limited_command(command, timeout=timeout)
        with _sandbox_memory_cgroup() as cgroup:
            # cgroup None ise (v1/delegation yok) graceful degrade: launcher'ı
            # cgroup'a taşımadan, yalnız per-process rlimit'lerle koş.
            if cgroup is not None:
                limited_command = _into_cgroup_command(cgroup, limited_command)
            timed_out = False
            try:
                with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
                    try:
                        proc = subprocess.run(
                            limited_command,
                            stdin=(
                                sentinel_write
                                if start_sentinel is not None
                                else subprocess.DEVNULL
                            ),
                            stdout=stdout_file,
                            stderr=stderr_file,
                            text=False,
                            timeout=timeout,
                            check=False,
                            close_fds=True,
                            env=scrub_env_for_sandbox(),
                        )
                    except OSError as exc:
                        raise SandboxUnavailableError(
                            f"sandbox failed to exec: {exc}"
                        ) from exc
                    except subprocess.TimeoutExpired:
                        timed_out = True
                        proc = subprocess.CompletedProcess(
                            args=limited_command,
                            returncode=_TIMEOUT_EXIT_CODE,
                            stdout=b"",
                            stderr=b"",
                        )
                    stdout, stdout_limited = _bounded_file_bytes(stdout_file)
                    stderr, stderr_limited = _bounded_file_bytes(stderr_file)
            finally:
                if sentinel_write != -1:
                    os.close(sentinel_write)
                    sentinel_write = -1

            if start_sentinel is not None:
                os.set_blocking(sentinel_read, False)
                try:
                    # Nonce sarmalayıcının İLK yazmasıdır; başka meşru yazar yok.
                    seen = os.read(sentinel_read, 4096)
                except BlockingIOError:
                    seen = b""
                if not seen.startswith(start_sentinel):
                    detail = stderr.decode("utf-8", "replace").strip()[:300]
                    if timed_out:
                        raise SandboxUnavailableError(
                            "sandbox failed to start: timed out before start sentinel"
                            + (f": {detail}" if detail else "")
                        )
                    raise SandboxUnavailableError(
                        f"sandbox failed to start: {detail or proc.returncode}"
                    )
            elif timed_out:
                raise SandboxUnavailableError(
                    "sandbox process timed out before start sentinel"
                )

            if timed_out:
                stderr = (
                    stderr[: max(0, _MAX_OUTPUT_BYTES - len(_TIMEOUT_MARKER))]
                    + _TIMEOUT_MARKER
                )
                return subprocess.CompletedProcess(
                    args=proc.args,
                    returncode=_TIMEOUT_EXIT_CODE,
                    stdout=stdout,
                    stderr=stderr,
                )

            if stdout_limited or stderr_limited:
                stderr = (
                    stderr[: _MAX_OUTPUT_BYTES - len(_OUTPUT_LIMIT_MARKER)]
                    + _OUTPUT_LIMIT_MARKER
                )
                return subprocess.CompletedProcess(
                    args=proc.args,
                    returncode=proc.returncode or _OUTPUT_LIMIT_EXIT_CODE,
                    stdout=stdout,
                    stderr=stderr,
                )
            return subprocess.CompletedProcess(
                args=proc.args,
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr,
            )
    finally:
        if sentinel_write != -1:
            os.close(sentinel_write)
        if sentinel_read != -1:
            os.close(sentinel_read)


def _run_bwrap_payload(
    bwrap_prefix: Sequence[str],
    payload: Sequence[str],
    *,
    timeout: float,
) -> subprocess.CompletedProcess[bytes]:
    """Run ``payload`` inside ``bwrap_prefix`` with the start-sentinel wrapper."""
    wrapped, sentinel = _with_start_sentinel(payload)
    return _run_bwrap_limited(
        [*bwrap_prefix, *wrapped],
        timeout=timeout,
        start_sentinel=sentinel,
    )


def _host_bind_roots(allowed_roots: Sequence[Path]) -> list[str]:
    args: list[str] = []
    # Minimal host toolchain for git
    for p in ("/usr", "/bin", "/lib"):
        path = Path(p)
        if path.exists():
            args += _bind_ro_args(path)
    lib64 = Path("/lib64")
    if lib64.exists():
        args += _bind_ro_args(lib64)
    # dynamic linker path on some distros
    for p in ("/lib/x86_64-linux-gnu", "/lib64/ld-linux-x86-64.so.2"):
        path = Path(p)
        if path.exists() and path.is_file():
            args += _bind_ro_args(path)
    for root in allowed_roots:
        resolved = root.resolve()
        if not resolved.exists():
            raise SandboxUnavailableError(f"allowed_root missing: {resolved}")
        args += _bind_ro_args(resolved)
    return args


def run_git_sandboxed(
    args: Sequence[str],
    *,
    cwd: Path,
    allowed_roots: Sequence[Path],
    timeout: float = 30.0,
) -> SandboxGitResult:
    """Run ``git <args>`` inside the observer sandbox.

    Fail-closed: if the sandbox motor cannot start, raises
    :class:`SandboxUnavailableError` (caller must skip the observation turn).
    """
    backend = sandbox_backend()
    if backend != "bubblewrap":
        raise SandboxUnavailableError(f"unsupported sandbox backend: {backend}")

    cwd_r = cwd.resolve()
    roots = [Path(r).resolve() for r in allowed_roots]
    if not any(cwd_r == r or cwd_r.is_relative_to(r) for r in roots):
        raise SandboxUnavailableError(f"cwd {cwd_r} is outside allowed_roots")

    git = shutil.which("git")
    if not git:
        raise SandboxUnavailableError("git not found on host PATH")

    bwrap_cmd: list[str] = _bwrap_isolation_prefix()
    bwrap_cmd += _host_bind_roots(roots)
    # git binary if outside /usr/bin
    git_path = Path(git).resolve()
    if not str(git_path).startswith("/usr/") and not str(git_path).startswith("/bin/"):
        bwrap_cmd += _bind_ro_args(git_path)

    bwrap_cmd += [
        "--chdir",
        str(cwd_r),
        "--clearenv",
    ]
    env = scrub_env_for_sandbox()
    for k, v in env.items():
        bwrap_cmd += ["--setenv", k, v]

    # Bytes + replace: non-UTF-8 git output must not UnicodeDecodeError out
    # of the observation turn (Bugbot Medium on cde9103).
    proc = _run_bwrap_payload(bwrap_cmd, [str(git_path), *args], timeout=timeout)

    return SandboxGitResult(
        returncode=proc.returncode,
        stdout=(proc.stdout or b"").decode("utf-8", "replace"),
        stderr=(proc.stderr or b"").decode("utf-8", "replace"),
    )


def probe_sandbox_env(
    *,
    allowed_roots: Sequence[Path],
    host_env: dict[str, str],
) -> dict[str, str]:
    """Run ``/usr/bin/env`` inside the sandbox; used by credential leak tests."""
    sandbox_backend()
    roots = [Path(r).resolve() for r in allowed_roots]
    if not roots:
        raise SandboxUnavailableError("allowed_roots empty")
    cwd_r = roots[0]
    bwrap_cmd: list[str] = _bwrap_isolation_prefix()
    bwrap_cmd += _host_bind_roots(roots)
    bwrap_cmd += ["--chdir", str(cwd_r), "--clearenv"]
    # Intentionally scrub — do not forward host_env secrets
    env = scrub_env_for_sandbox(host_env)
    for k, v in env.items():
        bwrap_cmd += ["--setenv", k, v]
    proc = _run_bwrap_payload(bwrap_cmd, ["/usr/bin/env", "-0"], timeout=15)
    if proc.returncode != 0:
        raise SandboxUnavailableError(
            f"env probe failed: {proc.stderr!r}"
        )
    out: dict[str, str] = {}
    for item in (proc.stdout or b"").split(b"\0"):
        if not item or b"=" not in item:
            continue
        k, v = item.split(b"=", 1)
        out[k.decode("utf-8", "replace")] = v.decode("utf-8", "replace")
    return out
