"""Tek açık onay okuyucusu.

Kalıcı silme ve görev motoru burada birleşmez. Görev yürütmesi kendi profil
matrisini kullanır; silme kendi yolunda kalır. Bu modül yalnız «açık onay
şu an var mı» sorusunun tek cevabıdır.

Kaynaklar:
- oturum: ``grant_explicit_approval`` / ``revoke_explicit_approval``
  (CLI ``genel onay aç/kapat``, canlı beyin onay cümlesi)
- panel operatörü: ``LUMOS_GENERAL_APPROVAL=1|true|yes``

Çekirdek sabit doğrulaması çalışma anında burada yapılır. Doğrulama
başarısızsa onay kapalı sayılır.
"""
from __future__ import annotations

import os

_session_open = False


def _constants_hold() -> bool:
    from core.inviolable import verify_core_constants

    return verify_core_constants()


def is_explicit_approval_open() -> bool:
    """Onay açıksa True. Sabitler bozuksa her zaman False."""
    if not _constants_hold():
        return False
    if _session_open:
        return True
    raw = (os.environ.get("LUMOS_GENERAL_APPROVAL") or "").strip().lower()
    return raw in ("1", "true", "yes")


def grant_explicit_approval() -> bool:
    """Oturum onayını aç. Sabitler tutmuyorsa açmaz ve False döner."""
    global _session_open
    if not _constants_hold():
        return False
    _session_open = True
    return True


def revoke_explicit_approval() -> None:
    """Oturum onayını kapat. Ortam değişkenine dokunmaz."""
    global _session_open
    _session_open = False


def reset_explicit_approval_session() -> None:
    """Testler süreç bayrağını sonraki teste taşınmasın diye bırakır."""
    revoke_explicit_approval()
