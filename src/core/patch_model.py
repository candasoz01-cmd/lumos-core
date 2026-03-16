from __future__ import annotations

"""
Patch domain modeli ve basit diff yardımcıları.

Amaç:
- Core/protected hedefler için doğrudan write yerine patch önerisi taşıyan veri modeli sağlamak.
- Değişiklikleri diff metni ile ifade etmek ve audit/guard katmanlarının bu modeli kullanabilmesini kolaylaştırmak.

Notlar:
- Bu modül filesystem'e yan etki yapmaz; sadece veri modeli ve diff üretimi sağlar.
- Uygulama (apply) ve guard kararları ayrı modüllerde ele alınır (ör. patch_pipeline).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional
import difflib
import hashlib
import uuid


PatchOperation = Literal["replace_file"]


@dataclass(frozen=True)
class PatchFingerprint:
    """
    Hedef dosyanın mevcut durumuna ait basit parmak izi.

    - hash_alg: Şu an için yalnızca sha256 desteklenir.
    - hex_digest: Mevcut içeriğin hex digest karşılığı; dosya yoksa boş string.
    - size: Byte cinsinden boyut; dosya yoksa 0.
    """

    hash_alg: str
    hex_digest: str
    size: int

    @staticmethod
    def from_text(content: str, *, encoding: str = "utf-8") -> "PatchFingerprint":
        data = content.encode(encoding)
        h = hashlib.sha256()
        h.update(data)
        return PatchFingerprint(hash_alg="sha256", hex_digest=h.hexdigest(), size=len(data))


@dataclass(frozen=True)
class PatchMetadata:
    """
    Patch önerisi ile birlikte taşınan açıklayıcı metadata.

    - reason: Neden bu değişiklik isteniyor?
    - caller: Öneriyi üreten kod yüzeyi (modül/fonksiyon adı gibi).
    - source: Kullanıcı veya sistem kaynağı (örn. "cli", "agent", "panel").
    - user_initiated: Kullanıcının açık aksiyonu ile mi tetiklendi?
    - requires_review: Uygulama öncesi review zorunlu mu?
    - protected_target: Hedef core/protected kapsamda mı?
    """

    reason: str
    caller: str
    source: str = "unknown"
    user_initiated: bool = False
    requires_review: bool = False
    protected_target: bool = False


@dataclass(frozen=True)
class PatchProposal:
    """
    Tek dosya için patch önerisi.

    Şu an için yalnızca "replace_file" operasyonu desteklenir:
    - original_text: Mevcut içerik (dosya yoksa boş string).
    - proposed_text: Önerilen yeni içerik.
    - diff_text: unified diff metni; None ise lazily üretilebilir.
    """

    id: str
    target_path: Path
    operation: PatchOperation
    original_fingerprint: PatchFingerprint
    original_text: str
    proposed_text: str
    metadata: PatchMetadata
    diff_text: Optional[str] = field(default=None)

    @staticmethod
    def new_replace_file(
        target_path: Path,
        *,
        original_text: str,
        proposed_text: str,
        metadata: PatchMetadata,
    ) -> "PatchProposal":
        fp = PatchFingerprint.from_text(original_text)
        diff = compute_unified_diff(
            original_text,
            proposed_text,
            from_path=str(target_path),
            to_path=str(target_path),
        )
        return PatchProposal(
            id=str(uuid.uuid4()),
            target_path=target_path,
            operation="replace_file",
            original_fingerprint=fp,
            original_text=original_text,
            proposed_text=proposed_text,
            metadata=metadata,
            diff_text=diff,
        )


def compute_unified_diff(
    original: str,
    proposed: str,
    *,
    from_path: str = "before",
    to_path: str = "after",
) -> str:
    """
    Basit unified diff üretimi.

    - Orijinal ve önerilen içerikleri satır satır karşılaştırır.
    - Panel veya loglarda gösterilebilecek sade bir diff çıktısı döner.
    """
    original_lines = original.splitlines(keepends=True)
    proposed_lines = proposed.splitlines(keepends=True)
    diff_iter = difflib.unified_diff(
        original_lines,
        proposed_lines,
        fromfile=from_path,
        tofile=to_path,
    )
    return "".join(diff_iter)

