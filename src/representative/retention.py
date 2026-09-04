"""Prova kaydının METİN KATMANINA saklama süresi uygular (kurucu kararları).

Karar zinciri:
- 2026-08-24 (kalem 1-3): sebep/durum alanları SÜREKLİ işletimsel kayıttır;
  kaynak/çeviri metni DIAGNOSTIC katmandır ve sınırlı süre yaşar. Fail-closed
  susturmanın sakladığı metinler (`fallback_unknown`, `held_partial_*`,
  `suppressed_duplicate`) de aynı süreye tabidir — ayrı bir yol yoktur.
- 2026-08-25 (kapanış şartları): (1) temizlik "bir sonraki rig koşusunda"
  olmamalı — rig bir daha hiç koşmayabilir; (2) `zero` saklama YEREL metni de
  kapsamalı: sıfır saklamada metin ne jsonl'e ne de konsol/nohup loguna düşer.

BU MEKANİZMANIN NE OLDUĞU — ve ne OLMADIĞI (dürüstlük notu 2026-08-25):
Bu, **makine açıkken periyodik koşan bir temizliktir**. Duvar-saati uyum
garantisi DEĞİLDİR ve öyle sunulmamalıdır. İki kanıtlanabilir boşluk vardır:
  1. Mac uykuda/kapalıyken hiçbir yerel zamanlayıcı koşmaz; temizlik ancak
     açılıştan sonraki ilk turda yapılır.
  2. Süre DOSYA damgasından ölçülür. Mevcut bir prova dosyasına yeni satır
     eklenince damga tazelenir; o dosyadaki ESKİ satırlar 24 saati aşabilir.
Satır-başına süre semantiği (kayda duvar-saati damgası) uygulanmadıkça
"24 saati aşan metin yoktur" denemez.

İki ayrı yürütme noktası vardır ve ikisi de aynı politikayı kullanır:
- **Yazma anı** (`pipeline.TextLayer`): sıfır saklamada metin kalıcı hâle
  getirilmez ve çıktıya basılmaz (bellekteki geçici düz metin kapsam dışı).
- **Süre dolumu** (bu modül): işletim sistemi zamanlayıcısına bağlı süpürme.

Depoda yeniden kullanılabilir bir zamanlayıcı YOK (denetim 2026-08-25):
`core/log_rotation` boyut tetiklidir ve yalnız yazma anında çalışır; GitHub
Actions cron'u bulutta koşar, kurucunun Mac'indeki dosyalara erişemez;
`security/presence_lock` yalnız Lumos oturumu açıkken yaşayan bir iş
parçacığıdır. Bu yüzden süpürme işletim sisteminin kendi zamanlayıcısına
(launchd LaunchAgent, `StartInterval`) verilir — yeni bir daemon yazılmaz.
Rig, ajan yüklü ve doğru yapılandırılmış değilse BAŞLAMAZ (fail-closed).

Kullanım:
    python -m representative.retention prova_bot.jsonl      # tek dosya
    python -m representative.retention --sweep --dir .      # zamanlayıcı işi
    python -m representative.retention --sweep --dir . --dry-run
    python -m representative.retention --sweeper-status --dir .
"""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from representative.meeting_ingress import (
    REAL_MEETING_RETENTION,
    REHEARSAL_RETENTION,
    RetentionPolicy,
)
from representative.pipeline import TEXT_FIELDS, TEXT_STATE_EXPIRED, TextLayer

# Metin taşıyan kalıcı yüzeyler. jsonl satır satır redakte edilebilir; konsol
# logu (nohup çıktısı) yapısız düz metindir — seçici redaksiyon güvenilir
# değildir, bu yüzden süresi dolduğunda SİLİNİR. İşletimsel kayıt zaten
# jsonl'de sürekli durur, kaybolan yalnız konsol kopyasıdır.
TRANSCRIPT_GLOB = "prova*.jsonl"
LOG_GLOB = "prova*.log"

# Süpürme aralığı. Süpürücü, gördüğü dosyalarda süreyi bir aralık ERKEN
# uygular (aşağıdaki margin): aksi hâlde temizlik, penceresi dolmuş bir dosyayı
# bir tur daha atlar ve silme bir aralık GECİKİRDİ. Bu, gecikmeyi kapatır;
# yukarıdaki iki boşluğu (uyku/kapalı makine, damga tazelenmesi) KAPATMAZ.
SWEEP_INTERVAL_S = 900  # 15 dk
SWEEP_MARGIN_HOURS = SWEEP_INTERVAL_S / 3600.0

# Kalp atışı: süpürme her koştuğunda dokunulan damga dosyası. "plist yüklü"
# olması işin GERÇEKTEN koştuğunu kanıtlamaz (yanlış python yolu, silinmiş
# worktree, hata veren iş — hepsi sessizce sağlıklı görünürdü). Sınırın
# gerçek olup olmadığı ancak son koşunun tazeliğinden bilinir.
SWEEP_STAMP_NAME = ".retention-sweep-stamp"
SWEEP_STAMP_MAX_AGE_S = 2 * SWEEP_INTERVAL_S  # bir tur kaçırmaya tolerans

SWEEPER_LABEL = "ai.lumos.representative.retention-sweep"
SWEEPER_PLIST = Path.home() / "Library" / "LaunchAgents" / f"{SWEEPER_LABEL}.plist"
INSTALL_SCRIPT = "ops/retention/install-retention-sweeper.sh"

POLICIES = {"rehearsal": REHEARSAL_RETENTION, "real-meeting": REAL_MEETING_RETENTION}


def text_layer_for(policy: RetentionPolicy) -> TextLayer:
    """Politikadan metin katmanı: `zero` → metin hiç yazılmaz (kayıt ve konsol)."""
    if not isinstance(policy, RetentionPolicy):
        raise ValueError("policy must be an explicit RetentionPolicy")
    return TextLayer(persists=policy.kind != "zero")


# --------------------------------------------------------------------------
# Süre dolumu
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class PruneResult:
    path: str
    policy: RetentionPolicy
    age_hours: float
    expired: bool  # süre doldu mu
    records: int
    cleared: int  # metni silinen (kuru çalışmada: silinecek) satır
    dropped: int  # çözümlenemeyen (yarım yazılmış) satır
    written: bool  # dosya gerçekten yeniden yazıldı mı
    dry_run: bool = False

    def describe(self) -> str:
        # DİKKAT: kurulum betiği bu satırları kurucuya GÖSTERİP onay istiyor.
        # "silindi" ile "silinecek" karışırsa yanlış bilgiyle onay alınır —
        # bu yüzden kuru çalışma ile gerçek koşu ayrı ayrı yazılır.
        if not self.expired:
            return (
                f"{self.path}: metin katmanı korunuyor "
                f"(yaş {self.age_hours:.1f} saat < {self.policy.hours} saat)"
            )
        if not self.cleared and not self.dropped:
            return f"{self.path}: silinecek metin yok (yaş {self.age_hours:.1f} saat)"
        dropped = f", {self.dropped} bozuk satır düşürülecek" if self.dropped else ""
        if self.dry_run:
            return (
                f"{self.path}: metin katmanı SİLİNECEK — {self.cleared}/{self.records} satır "
                f"(yaş {self.age_hours:.1f} saat{dropped}) [kuru çalışma, dosya değişmedi]"
            )
        dropped = dropped.replace("düşürülecek", "düşürüldü")
        return (
            f"{self.path}: metin katmanı silindi — {self.cleared}/{self.records} satır "
            f"(yaş {self.age_hours:.1f} saat{dropped}); sebep/durum alanları duruyor"
        )


@dataclass(frozen=True)
class LogResult:
    path: str
    age_hours: float
    deleted: bool
    dry_run: bool = False

    def describe(self) -> str:
        if not self.deleted:
            return f"{self.path}: konsol logu korunuyor (yaş {self.age_hours:.1f} saat)"
        if self.dry_run:
            return (
                f"{self.path}: konsol logu SİLİNECEK (yaş {self.age_hours:.1f} saat, "
                f"seçici redaksiyon yok) [kuru çalışma, dosya duruyor]"
            )
        return (
            f"{self.path}: konsol logu SİLİNDİ "
            f"(yaş {self.age_hours:.1f} saat, seçici redaksiyon yok)"
        )


def expire_text_layer(record: dict) -> dict:
    """Bir kaydın metin katmanını boşaltır; diğer her alan aynen kalır.

    `flag_reason`a BAKMAZ: fail-closed satırların metni de seslendirilmiş
    satırlarınki gibi diagnostic katmandır (2026-08-24 kararı, kalem 3).
    """
    cleared = dict(record)
    touched = False
    for field in TEXT_FIELDS:
        if cleared.get(field):
            cleared[field] = ""
            touched = True
    if touched:
        cleared["text_state"] = TEXT_STATE_EXPIRED
    return cleared


def file_age_hours(path: str | os.PathLike[str], now: float | None = None) -> float:
    """Dosyanın yaşı (saat). Erken tarafta hata yapılır: en ESKİ damga esas."""
    stat = os.stat(path)
    anchor = stat.st_mtime
    birth = getattr(stat, "st_birthtime", None)
    if birth:
        anchor = min(anchor, birth)
    now = time.time() if now is None else now
    return max(0.0, (now - anchor) / 3600.0)


def is_expired(
    age_hours: float, policy: RetentionPolicy, *, margin_hours: float = 0.0
) -> bool:
    """`zero` = metin hiç yaşamaz; `timed` = süre (eksi güvenlik payı) dolunca."""
    if policy.kind == "zero":
        return True
    assert policy.hours is not None  # RetentionPolicy zaten doğruluyor
    return age_hours >= max(0.0, policy.hours - margin_hours)


def prune_jsonl(
    path: str,
    *,
    policy: RetentionPolicy = REHEARSAL_RETENTION,
    now: float | None = None,
    margin_hours: float = 0.0,
    dry_run: bool = False,
) -> PruneResult:
    """Süresi dolmuşsa dosyayı (atomik olarak) metinsiz haliyle yeniden yazar.

    Süre dolmadıysa veya silinecek metin yoksa dosyaya HİÇ dokunulmaz — yazma
    damgayı tazeleyip süreyi uzatırdı. Çözümlenemeyen satırlar (çökmede yarım
    kalmış) süre dolduğunda DÜŞÜRÜLÜR: içlerindeki metin redakte edilemez,
    saklamak fail-open olurdu.
    """
    if not isinstance(policy, RetentionPolicy):
        raise ValueError("policy must be an explicit RetentionPolicy")
    age = file_age_hours(path, now)
    if not is_expired(age, policy, margin_hours=margin_hours):
        return PruneResult(path, policy, age, False, 0, 0, 0, False)

    kept: list[str] = []
    records = cleared = dropped = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                dropped += 1
                continue
            records += 1
            pruned = expire_text_layer(record)
            if pruned.get("text_state") == TEXT_STATE_EXPIRED:
                cleared += 1
            kept.append(json.dumps(pruned, ensure_ascii=False))

    if not cleared and not dropped:
        # Silinecek metin yok (ör. sıfır saklamayla üretilmiş dosya):
        # yeniden yazmak yalnız damgayı tazelerdi.
        return PruneResult(path, policy, age, True, records, 0, 0, False)
    if dry_run:
        return PruneResult(path, policy, age, True, records, cleared, dropped, False, True)

    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("".join(line + "\n" for line in kept))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return PruneResult(path, policy, age, True, records, cleared, dropped, True)


def expire_log(
    path: str,
    *,
    policy: RetentionPolicy = REHEARSAL_RETENTION,
    now: float | None = None,
    margin_hours: float = 0.0,
    dry_run: bool = False,
) -> LogResult:
    """Konsol/nohup logunu süresi dolunca siler (seçici redaksiyon mümkün değil).

    `zero` politikası burada UYGULANMAZ: sıfır saklamada metin loga zaten hiç
    düşmez (`TextLayer.show`), dolayısıyla silinecek bir şey yoktur; buradan
    tetiklenseydi o an koşan oturumun logu silinirdi.
    """
    age = file_age_hours(path, now)
    if policy.kind == "zero" or not is_expired(age, policy, margin_hours=margin_hours):
        return LogResult(path, age, False)
    if not dry_run:
        os.remove(path)
    return LogResult(path, age, True, dry_run)


@dataclass(frozen=True)
class SweepResult:
    directory: str
    transcripts: tuple[PruneResult, ...]
    logs: tuple[LogResult, ...]

    def describe(self) -> str:
        lines = [r.describe() for r in self.transcripts]
        lines += [r.describe() for r in self.logs]
        if not lines:
            return f"{self.directory}: prova dosyası yok"
        return "\n".join(lines)


def sweep(
    directory: str | os.PathLike[str],
    *,
    policy: RetentionPolicy = REHEARSAL_RETENTION,
    now: float | None = None,
    margin_hours: float = SWEEP_MARGIN_HOURS,
    dry_run: bool = False,
) -> SweepResult:
    """Zamanlayıcının koştuğu iş: dizindeki TÜM prova yüzeylerini süreye tabi tutar.

    Güvenlik payı varsayılan olarak bir süpürme aralığıdır: penceresi dolmuş bir
    dosya bir tur daha beklemez. Bu, silmenin bir aralık GECİKMESİNİ önler;
    "hiçbir metin 24 saati aşmaz" anlamına GELMEZ (bkz. modül başlığındaki iki
    boşluk: kapalı/uykudaki makine ve dosya damgasının tazelenmesi).
    """
    base = Path(directory)
    transcripts = [
        prune_jsonl(
            str(p), policy=policy, now=now, margin_hours=margin_hours, dry_run=dry_run
        )
        for p in sorted(base.glob(TRANSCRIPT_GLOB))
    ]
    logs = [
        expire_log(str(p), policy=policy, now=now, margin_hours=margin_hours, dry_run=dry_run)
        for p in sorted(base.glob(LOG_GLOB))
    ]
    if not dry_run:
        # Kalp atışı EN SON yazılır: iş yarıda patlarsa damga tazelenmez ve
        # `sweeper_status` bunu "bayat" olarak görür.
        stamp = base / SWEEP_STAMP_NAME
        stamp.write_text(f"{now if now is not None else time.time():.0f}\n", encoding="utf-8")
    return SweepResult(str(base), tuple(transcripts), tuple(logs))


def enforce(path: str, policy: RetentionPolicy = REHEARSAL_RETENTION) -> PruneResult | None:
    """Rig başlangıcı için sarmalayıcı (ikinci ağ; asıl sınır süpürücüdedir)."""
    if not os.path.exists(path):
        return None
    return prune_jsonl(path, policy=policy)


# --------------------------------------------------------------------------
# Üst sınırın gerçekliği: işletim sistemi zamanlayıcısı doğrulanır
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SweeperStatus:
    healthy: bool
    reason: str
    plist_path: str
    interval_s: int | None = None
    directory: str | None = None
    last_sweep_age_s: float | None = None

    def describe(self) -> str:
        if self.healthy:
            return (
                f"saklama süpürücüsü: ÇALIŞIYOR ({self.interval_s} sn aralık, "
                f"dizin {self.directory}, son koşu {self.last_sweep_age_s:.0f} sn önce)"
            )
        return f"saklama süpürücüsü: YOK/GEÇERSİZ ({self.reason})"


def _launchctl_loaded(label: str) -> bool:  # pragma: no cover - sistem çağrısı
    try:
        done = subprocess.run(
            ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def sweeper_status(
    directory: str | os.PathLike[str],
    *,
    plist_path: str | os.PathLike[str] = SWEEPER_PLIST,
    loaded_probe=_launchctl_loaded,
    platform_name: str = sys.platform,
    now: float | None = None,
) -> SweeperStatus:
    """Temizlik işi gerçekten kurulu, yeterince sık, doğru dizin için ve KOŞUYOR mu?

    Sorulan soru "bir plist var mı" değil: aralık yeterince kısa mı, iş bu
    provanın yazdığı dizini mi süpürüyor, son koşu taze mi? Başka bir dizin için
    kurulmuş ya da her turda patlayan bir ajan, temizlik çalışıyormuş gibi
    görünürdü.
    """
    plist_path = Path(plist_path)
    if platform_name != "darwin":
        return SweeperStatus(False, "unsupported_platform", str(plist_path))
    if not plist_path.exists():
        return SweeperStatus(False, "plist_missing", str(plist_path))
    try:
        with open(plist_path, "rb") as f:
            data = plistlib.load(f)
    except Exception:
        return SweeperStatus(False, "plist_unreadable", str(plist_path))

    interval = data.get("StartInterval")
    args = [str(a) for a in data.get("ProgramArguments", [])]
    swept = None
    if "--dir" in args:
        index = args.index("--dir") + 1
        if index < len(args):
            swept = str(Path(args[index]).resolve())
    wanted = str(Path(directory).resolve())

    if not isinstance(interval, int) or interval <= 0 or interval > SWEEP_INTERVAL_S:
        return SweeperStatus(False, "interval_too_long", str(plist_path), interval, swept)
    if swept != wanted:
        return SweeperStatus(False, "wrong_directory", str(plist_path), interval, swept)
    if args and not Path(args[0]).exists():
        # Yanlış/silinmiş yorumlayıcı yolu: iş her turda patlar ama plist
        # sapasağlam görünür (ör. worktree'den kurulup worktree silinince).
        return SweeperStatus(False, "program_missing", str(plist_path), interval, swept)
    if not loaded_probe(data.get("Label", SWEEPER_LABEL)):
        return SweeperStatus(False, "not_loaded", str(plist_path), interval, swept)

    stamp = Path(wanted) / SWEEP_STAMP_NAME
    if not stamp.exists():
        return SweeperStatus(False, "never_ran", str(plist_path), interval, swept)
    age = (time.time() if now is None else now) - os.stat(stamp).st_mtime
    if age > SWEEP_STAMP_MAX_AGE_S:
        return SweeperStatus(False, "stale_heartbeat", str(plist_path), interval, swept, age)
    return SweeperStatus(True, "ok", str(plist_path), interval, swept, age)


def require_sweeper(directory: str | os.PathLike[str], **kwargs) -> SweeperStatus:
    """Fail-closed: periyodik temizlik koşmuyorsa rig metin yazmaya başlamaz.

    Gerekçe (2026-08-25): "bir sonraki rig koşusunda temizlenir" bir temizlik
    politikası değildir — rig bir daha hiç koşmayabilir. Temizliği yürüten şey
    işletim sisteminin zamanlayıcısıdır; o koşmuyorsa metnin ne zaman
    gideceğine dair söylenebilecek bir şey kalmaz, o hâlde metin de yazılmaz.
    Bu kapı temizliğin ÇALIŞTIĞINI doğrular; duvar-saati garantisi VERMEZ.
    """
    status = sweeper_status(directory, **kwargs)
    if status.healthy:
        return status
    raise RuntimeError(
        f"saklama süpürücüsü doğrulanamadı ({status.reason}) — metin katmanının "
        f"periyodik temizliği koşmuyor, bu yüzden koşu başlatılmadı.\n"
        f"  Kur:  bash {INSTALL_SCRIPT}\n"
        f"  Ya da metni hiç saklamadan koş:  --retention real-meeting"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prova kayıtlarının metin katmanına saklama süresi uygular"
    )
    parser.add_argument("paths", nargs="*", help="prova jsonl kaydı/kayıtları")
    parser.add_argument("--sweep", action="store_true", help="dizindeki tüm prova yüzeylerini süpür")
    parser.add_argument("--dir", default=".", help="--sweep/--sweeper-status için dizin")
    parser.add_argument("--dry-run", action="store_true", help="hiçbir şey yazma/silme, ne olacağını yaz")
    parser.add_argument("--sweeper-status", action="store_true", help="zamanlayıcı işini doğrula")
    parser.add_argument(
        "--policy",
        choices=sorted(POLICIES),
        default="rehearsal",
        help="rehearsal: kapalı prova (timed/24h) — varsayılan; "
        "real-meeting: sıfır saklama, metin anında silinir",
    )
    args = parser.parse_args(argv)
    policy = POLICIES[args.policy]

    if args.sweeper_status:
        status = sweeper_status(args.dir)
        print(status.describe())
        return 0 if status.healthy else 1

    if args.sweep:
        result = sweep(args.dir, policy=policy, dry_run=args.dry_run)
        print(result.describe())
        return 0

    if not args.paths:
        parser.error("dosya yolu ver ya da --sweep/--sweeper-status kullan")
    missing = [p for p in args.paths if not os.path.exists(p)]
    for path in args.paths:
        if path in missing:
            print(f"{path}: dosya yok")
            continue
        print(prune_jsonl(path, policy=policy, dry_run=args.dry_run).describe())
    return 1 if missing else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
