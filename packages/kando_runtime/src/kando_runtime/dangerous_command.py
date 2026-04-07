"""
Kök dizin, disk ve kabuk yıkımı gibi sistem bozucu yüzey taraması.

«Dosyayı sil» / TARGET dosya görevleri eşleşmez; yalnızca açık yıkım komut kalıpları.
"""
from __future__ import annotations

import re

_RE_WS = re.compile(r"\s+")


def normalize_command_surface(text: str) -> str:
    return _RE_WS.sub(" ", (text or "").strip().lower())


_RM_WORD = re.compile(r"\brm\b", re.I)
# rm + opsiyonel bayraklar + tehlikeli hedef
_RM_DANGEROUS_TARGET = re.compile(
    r"\brm\b"
    r"(?:\s+-[a-z0-9]+)*"
    r"\s+"
    r"(?:"
    r"/(?:\s|$)|"
    r"/\*|"
    r"\.\./|"
    r"~(?:/|\s|$)|"
    r"/dev/|"
    r"/etc(?:/|\s|$)|"
    r"/sys(?:/|\s|$)|"
    r"/proc(?:/|\s|$)|"
    r"/boot(?:/|\s|$)|"
    r"/usr(?:/|\s|$)|"
    r"/bin(?:/|\s|$)|"
    r"/sbin(?:/|\s|$)"
    r")",
    re.I,
)


def _matches_rm_root_like(n: str) -> bool:
    if not _RM_WORD.search(n):
        return False
    if "--no-preserve-root" in n:
        return True
    return bool(_RM_DANGEROUS_TARGET.search(n))


_DISK_WIPE = re.compile(
    r"(?:\bdd\b\s+if=|\bmkfs\.?\w*\b|\bwipefs\b|\bparted\b.*\b/dev/|\bfdisk\b.*\b/dev/)",
    re.I,
)
_FORK_BOMB = re.compile(r":\(\)\s*\{\s*:\|:&\s*\}\s*;", re.I)
_CHROOT_PERM = re.compile(
    r"(?:\bchmod\b[^;\n|&`$]{0,120}\s(?:777|1777)\s*/|\bchmod\b[^;\n|&`$]{0,120}\s-r\s+[^;\n|&`$]{0,80}\s*/\s)",
    re.I,
)
_PIPE_SHELL = re.compile(
    r"(?:\b(?:curl|wget)\b[^;\n|&`$]{0,240}\|\s*(?:bash|sh)\b|\|\s*(?:bash|sh)\s+-c\b)",
    re.I,
)
_DEV_BLOCK = re.compile(
    r"(?:^|\s)of=/dev/(?:sd|hd|vd|nvme|loop)|(?:^|\s)/dev/(?:sd|hd|vd)\w*\b|"
    r"\bdd\b[^;\n|&`$]{0,120}of=/dev/",
    re.I,
)
_WIN_RIP = re.compile(
    r"\bformat\s+[a-z]:\s*/y\b|"
    r"\brd\s+/s\s+/q\b\s+\\?windows\\",
    re.I,
)


def destructive_surface_blocks_task(text: str) -> tuple[bool, str | None]:
    """
    True ise köprü görev oluşturmadan reddetmeli; ikinci değer iç kod.
    """
    n = normalize_command_surface(text)
    if not n:
        return False, None
    if _matches_rm_root_like(n):
        return True, "destructive_rm_root"
    if _DISK_WIPE.search(n):
        return True, "disk_wipe"
    if _FORK_BOMB.search(n):
        return True, "fork_bomb"
    if _CHROOT_PERM.search(n):
        return True, "chmod_root_loosen"
    if _PIPE_SHELL.search(n):
        return True, "remote_pipe_shell"
    if _DEV_BLOCK.search(n):
        return True, "block_device_target"
    if _WIN_RIP.search(n):
        return True, "windows_system_rip"
    return False, None


def destructive_command_user_message_tr() -> str:
    return (
        "Lumos: Bu istek kök dizin, disk veya kabuk üzerinde yıkıcı komut içeriyor; "
        "görev oluşturulmadan reddedildi."
    )
