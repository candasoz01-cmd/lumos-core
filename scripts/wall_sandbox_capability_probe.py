#!/usr/bin/env python3
"""
Agent Wall observer sandbox — yetenek ölçüm dilimi.

Sözleşme: docs/contracts/agent-wall-observer-sandbox-v0.md §3.1 tablosu ve §4
kabul ölçütleri. Bu betik MOTOR SEÇMEZ. Yalnız ölçer: her aday motor, §3.1
tablosunun hangi satırını gerçekten sağlıyor?

Her senaryo iki kez koşar:
  * `direct`  — sandbox yok (bugünkü davranış; taban çizgisi)
  * `<motor>` — aday motor (macOS: sandbox-exec / Linux: bwrap)

Çıktı ham gerçektir: bir motor bir satırı sağlamıyorsa öyle yazılır.
Hiçbir şeyi "geçti" saymaz; her satır tek tek ölçülür.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

GIT = shutil.which("git") or "/usr/bin/git"
IS_MAC = platform.system() == "Darwin"


# --------------------------------------------------------------------------
# Fixture: kök içinde düşman depo + kök dışında sır
# --------------------------------------------------------------------------

def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [GIT, "-c", "user.email=probe@lumos", "-c", "user.name=probe", *args],
        cwd=cwd, capture_output=True, text=True,
    )


@dataclass
class Fixture:
    base: Path
    allowed_root: Path
    repo: Path
    outside: Path
    marker: Path
    journal: Path
    hostile_script: Path = field(init=False)

    @classmethod
    def build(cls, base: Path) -> "Fixture":
        allowed = base / "approved"
        repo = allowed / "worktree"
        outside = base / "outside"
        repo.mkdir(parents=True)
        outside.mkdir(parents=True)

        (outside / "OUTSIDE_SECRET.txt").write_text("kok disi sir\n", encoding="utf-8")

        _git(repo, "init", "-q")
        (repo / "tracked.txt").write_text("AAAAAAAA\n", encoding="utf-8")
        _git(repo, "add", "tracked.txt")
        _git(repo, "commit", "-q", "-m", "base")
        # AYNI BOYUTTA kirlilik: git stat ile karar veremez, içeriği hash'lemek
        # zorunda kalır ve clean filter tetiklenir. Boyut değişirse filter hiç
        # çalışmaz ve ölçüm sahte "temiz" verir.
        (repo / "tracked.txt").write_text("BBBBBBBB\n", encoding="utf-8")
        os.utime(repo / "tracked.txt", (0, 0))

        marker = base / "FILTER_RAN.marker"
        # GERÇEKÇİ KONUM: düşman betik deponun İÇİNDE (kök içi düşman depo
        # varsayımı, sözleşme §3.2/5). Kök dışına konursa motor betiği hiç
        # göremez ve ölçüm motoru olduğundan güvenli gösterir.
        script = repo / ".evil_clean.sh"
        script.write_text(
            # ÇALIŞTIRMA sinyali stderr'e gider: dosya yazımı engellense bile
            # kodun koştuğu görülür. Yalnız marker'a bakmak, yazma yasağını
            # "kod çalışmadı" sanmaya yol açar (ölçülen hata).
            "#!/bin/sh\n"
            "printf 'LUMOS_FILTER_EXECUTED\\n' 1>&2\n"
            f"printf 'filter calisti\\n' > '{marker}' 2>/dev/null\n"
            "cat\n",
            encoding="utf-8",
        )
        script.chmod(0o755)

        # düşman depo kendi config'iyle clean filter tanımlar
        (repo / ".gitattributes").write_text("* filter=evil\n", encoding="utf-8")
        _git(repo, "config", "filter.evil.clean", str(script))

        journal = base / "journal.jsonl"
        journal.write_text("", encoding="utf-8")

        fx = cls(base=base, allowed_root=allowed, repo=repo, outside=outside,
                 marker=marker, journal=journal)
        fx.hostile_script = script
        return fx


# --------------------------------------------------------------------------
# Motorlar: bir komutu sarar, sonucu döndürür
# --------------------------------------------------------------------------

# Ölçülen gerçek: macOS 26'da file-read* dar bir subpath listesine indirilirse
# süreçler dyld aşamasında SIGABRT ile ölüyor (/bin/echo dahil). Bu yüzden iki
# profil ayrı ayrı ölçülür; hangisinin tabloyu sağladığına veri karar verir.
SEATBELT_STRICT = """(version 1)
(deny default)
(allow process-fork)
(allow process-exec*)
(allow sysctl-read)
(allow mach-lookup)
(allow file-read-metadata)
(allow file-read*
  (subpath "/usr") (subpath "/System") (subpath "/bin") (subpath "/opt/homebrew")
  (subpath "/private/var/db") (subpath "/tmp")
  (subpath "{allowed}"))
(allow file-write-data (literal "/dev/null"))
(allow file-ioctl (literal "/dev/null") (literal "/dev/dtracehelper"))
(allow file-read* (subpath "/dev"))
"""

# Yazma ve ağ kapalı; okuma geniş ama credential konumları açıkça reddedilir.
SEATBELT_DENYLIST = """(version 1)
(deny default)
(allow process-fork)
(allow process-exec*)
(allow sysctl-read)
(allow mach-lookup)
(allow file-read*)
(deny file-read* (subpath "{home}/.ssh") (subpath "{home}/Library/Keychains")
                 (subpath "{home}/.aws") (subpath "{home}/.config/gh")
                 (subpath "{outside}"))
(allow file-write-data (literal "/dev/null"))
(allow file-ioctl (literal "/dev/null") (literal "/dev/dtracehelper"))
(allow file-read* (subpath "/dev"))
"""


def run_direct(cmd: list[str], cwd: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)


def _seatbelt(profile: str, cmd: list[str], cwd: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["/usr/bin/sandbox-exec", "-p", profile, *cmd],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=60,
    )


def run_seatbelt_strict(cmd, cwd, env, fx):
    return _seatbelt(SEATBELT_STRICT.format(allowed=fx.allowed_root.resolve()), cmd, cwd, env)


def run_seatbelt_denylist(cmd, cwd, env, fx):
    prof = SEATBELT_DENYLIST.format(home=Path.home(), outside=fx.outside.resolve())
    return _seatbelt(prof, cmd, cwd, env)


def run_bwrap(cmd: list[str], cwd: Path, env: dict, fx: Fixture) -> subprocess.CompletedProcess:
    root = str(fx.allowed_root.resolve())
    wrapped = [
        "bwrap",
        "--unshare-all",                 # ağ dahil tüm namespace'ler
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/lib", "/lib",
        "--ro-bind-try", "/lib64", "/lib64",
        "--ro-bind-try", "/bin", "/bin",
        "--ro-bind-try", "/etc/ssl", "/etc/ssl",
        "--ro-bind", root, root,         # allowed_root SALT-OKUNUR
        "--proc", "/proc",
        "--dev", "/dev",
        "--die-with-parent",
        "--chdir", str(cwd),
        "--",
        *cmd,
    ]
    return subprocess.run(wrapped, env=env, capture_output=True, text=True, timeout=60)


def engines() -> dict:
    eng = {"direct": lambda c, cwd, e, fx: run_direct(c, cwd, e)}
    if IS_MAC and Path("/usr/bin/sandbox-exec").exists():
        eng["seatbelt-strict"] = run_seatbelt_strict
        eng["seatbelt-denylist"] = run_seatbelt_denylist
    if shutil.which("bwrap"):
        eng["bwrap"] = run_bwrap
    return eng


# --------------------------------------------------------------------------
# Senaryolar — §4 kabul ölçütleri
# --------------------------------------------------------------------------

def _env_with_fake_creds() -> dict:
    env = dict(os.environ)
    env["LUMOS_FAKE_OPERATOR_TOKEN"] = "SECRET-OPERATOR-TOKEN"
    env["GIT_ASKPASS"] = "/bin/false"
    return env


def s0_tool_actually_runs(run, fx) -> dict:
    """Geçerlilik kapısı: motor git'i ÇALIŞTIRABİLİYOR mu?

    Bir motor aracı hiç başlatamıyorsa "kötü şey olmadı" güvenlik değil,
    ölçüm çöküşüdür. #832'de tam bu hataya düşülmüştü; burada kapı olarak duruyor.
    """
    r = run([GIT, "--version"], fx.repo, _env_with_fake_creds(), fx)
    ok = r.returncode == 0 and "git version" in r.stdout
    return {
        "beklenen": "git ÇALIŞMALI (yoksa diğer satırlar geçersiz)",
        "olan": (r.stdout.strip() or f"rc={r.returncode} (calismadi)")[:60],
        "saglandi": ok,
    }


def s1_filter_executes(run, fx) -> dict:
    """§4.1 — düşman deponun filter.*.clean'i çalışıyor mu?"""
    if fx.marker.exists():
        fx.marker.unlink()
    r = run([GIT, "status", "--porcelain", "-z"], fx.repo, _env_with_fake_creds(), fx)
    executed = "LUMOS_FILTER_EXECUTED" in r.stderr
    wrote = fx.marker.exists()
    ran = executed or wrote
    return {
        "beklenen": "filter KOŞMAMALI",
        "olan": ("filter koştu"
                 + (" ve yazdı" if wrote else " ama yazamadı")) if ran else "filter koşmadı",
        "kod_calisti": executed,
        "yan_etki_yazdi": wrote,
        "saglandi": not ran,
        "git_rc": r.returncode,
        "git_stdout_bos_mu": not r.stdout.strip(),
        "not": (r.stderr.strip().splitlines() or [""])[-1][:120],
    }


def s2_outside_read(run, fx) -> dict:
    """§3.1 Okuma — kök dışı dosya okunabiliyor mu?"""
    target = fx.outside / "OUTSIDE_SECRET.txt"
    r = run(["/bin/cat", str(target)], fx.repo, _env_with_fake_creds(), fx)
    leaked = "kok disi sir" in r.stdout
    return {
        "beklenen": "kök dışı okuma ENGELLENMELİ",
        "olan": "okundu" if leaked else "engellendi",
        "saglandi": not leaked,
        "rc": r.returncode,
    }


def s3_credentials(run, fx) -> dict:
    """§4.2 — operatör credential'ı sandbox'a giriyor mu?"""
    r = run(["/bin/sh", "-c", 'printf "%s" "${LUMOS_FAKE_OPERATOR_TOKEN:-YOK}"'],
            fx.repo, _env_with_fake_creds(), fx)
    leaked_env = "SECRET-OPERATOR-TOKEN" in r.stdout
    home_ssh = Path.home() / ".ssh"
    r2 = run(["/bin/sh", "-c", f'ls "{home_ssh}" >/dev/null 2>&1 && echo READABLE || echo BLOCKED'],
             fx.repo, _env_with_fake_creds(), fx)
    ssh_readable = "READABLE" in r2.stdout
    return {
        "beklenen": "env sırrı ve ~/.ssh ERİŞİLEMEMELİ",
        "olan": f"env_sir={'sizdi' if leaked_env else 'yok'}, ssh={'okunabilir' if ssh_readable else 'kapalı'}",
        "saglandi": (not leaked_env) and (not ssh_readable),
    }


def s4_network(run, fx) -> dict:
    """§4.3 — ağ fail-closed mı?"""
    curl = shutil.which("curl") or "/usr/bin/curl"
    r = run([curl, "-sS", "--max-time", "6", "-o", "/dev/null",
             "-w", "HTTP_%{http_code}", "https://1.1.1.1/"],
            fx.repo, _env_with_fake_creds(), fx)
    open_net = "HTTP_2" in r.stdout or "HTTP_3" in r.stdout
    return {
        "beklenen": "ağ KAPALI",
        "olan": (r.stdout.strip() or (r.stderr.strip().splitlines() or ["cikti yok"])[-1]
                 or f"rc={r.returncode}")[:70],
        "saglandi": not open_net,
        "prob_calisti": r.returncode is not None and r.returncode >= 0,
    }


def s5_write(run, fx) -> dict:
    """§4.4/§4.5 — worktree'ye ve günceye yazma fail-closed mı?"""
    probe = fx.repo / "SANDBOX_WROTE_HERE.txt"
    if probe.exists():
        probe.unlink()
    run(["/bin/sh", "-c", f'echo x > "{probe}"'], fx.repo, _env_with_fake_creds(), fx)
    wrote_worktree = probe.exists()

    before = fx.journal.read_text(encoding="utf-8")
    run(["/bin/sh", "-c", f'echo tampered >> "{fx.journal}"'], fx.repo, _env_with_fake_creds(), fx)
    wrote_journal = fx.journal.read_text(encoding="utf-8") != before

    return {
        "beklenen": "worktree ve günce yazımı ENGELLENMELİ",
        "olan": f"worktree={'yazdı' if wrote_worktree else 'engellendi'}, "
                f"gunce={'yazdı' if wrote_journal else 'engellendi'}",
        "saglandi": (not wrote_worktree) and (not wrote_journal),
    }


SCENARIOS = [
    ("S0 git gerçekten koşuyor mu", s0_tool_actually_runs),
    ("S1 filter.*.clean çalıştırma", s1_filter_executes),
    ("S2 kök dışı okuma", s2_outside_read),
    ("S3 credential sızıntısı", s3_credentials),
    ("S4 ağ", s4_network),
    ("S5 yazma (worktree + günce)", s5_write),
]


# --------------------------------------------------------------------------
# Koşum
# --------------------------------------------------------------------------

def main() -> int:
    eng = engines()
    results: dict[str, dict] = {}

    print(f"platform : {platform.system()} {platform.release()}")
    print(f"git      : {GIT} ({subprocess.run([GIT, '--version'], capture_output=True, text=True).stdout.strip()})")
    print(f"motorlar : {', '.join(eng)}")
    print()

    for engine_name, runner in eng.items():
        results[engine_name] = {}
        for label, fn in SCENARIOS:
            with tempfile.TemporaryDirectory(prefix="wallsbx_") as td:
                fx = Fixture.build(Path(td).resolve())
                try:
                    res = fn(lambda c, cwd, e, f=fx: runner(c, cwd, e, f), fx)
                except Exception as exc:  # ölçüm çökerse gizleme
                    res = {"beklenen": "-", "olan": f"ÖLÇÜM HATASI: {type(exc).__name__}: {exc}",
                           "saglandi": False}
            results[engine_name][label] = res

    width = max(len(name) for name, _ in SCENARIOS) + 2
    for engine_name in results:
        print(f"### motor: {engine_name}")
        gate_ok = results[engine_name]["S0 git gerçekten koşuyor mu"]["saglandi"]
        for label, _ in SCENARIOS:
            r = results[engine_name][label]
            if label.startswith("S0"):
                mark = "SAĞLIYOR " if r["saglandi"] else "SAĞLAMIYOR"
            elif not gate_ok:
                mark = "GEÇERSİZ "
            else:
                mark = "SAĞLIYOR " if r["saglandi"] else "SAĞLAMIYOR"
            print(f"  {label:<{width}} {mark}  {r['olan']}")
        if not gate_ok:
            print("  ^ S0 düştü: bu motorda araç başlamıyor, güvenlik iddiası kurulamaz.")
        print()

    # Çıktı repoya yazılmaz: ölçüm kanıtı geçici dizine düşer, yolu basılır.
    # (Repo içine yazmak, gözlemcinin kendi sözleşmesindeki "yan etki yok"
    #  ilkesine ters düşerdi.)
    out_dir = Path(os.environ.get("WALL_SANDBOX_PROBE_OUT", tempfile.gettempdir()))
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"sandbox_probe_{platform.system().lower()}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ham sonuç: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
