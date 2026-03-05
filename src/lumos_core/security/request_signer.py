import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from lumos_core.security.crypto import b64e, b64d
from lumos_core.security.entropy import get_random_bytes


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


@dataclass
class SignedRequest:
    lumos_id: str
    ts: int
    nonce: str
    payload: Any
    sig_b64: str
    pub_b64: Optional[str] = None

    def to_headers(self) -> Dict[str, str]:
        h = {
            "X-Lumos-Id": self.lumos_id,
            "X-Lumos-Ts": str(self.ts),
            "X-Lumos-Nonce": self.nonce,
            "X-Lumos-Sig": self.sig_b64,
        }
        if self.pub_b64:
            h["X-Lumos-Pub"] = self.pub_b64
        return h


class RequestSigner:
    def __init__(self, lumos_id: str, private_key_bytes: bytes, public_key_bytes: Optional[bytes] = None):
        lumos_id = (lumos_id or "").strip()
        if not lumos_id:
            raise ValueError("lumos_id boş olamaz")

        if not private_key_bytes or len(private_key_bytes) != 32:
            raise ValueError("private_key_bytes 32 bayt olmalı (ed25519 seed)")

        self.lumos_id = lumos_id
        self._priv = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        self._pub_bytes = public_key_bytes if public_key_bytes else None

    def sign(self, payload: Any, ts: Optional[int] = None, nonce: Optional[str] = None, include_pub: bool = False) -> SignedRequest:
        ts = int(ts if ts is not None else time.time())
        nonce = nonce or base64.urlsafe_b64encode(get_random_bytes(12)).decode("utf-8").rstrip("=")

        envelope = {
            "lumos_id": self.lumos_id,
            "ts": ts,
            "nonce": nonce,
            "payload": payload,
        }

        sig = self._priv.sign(_canon(envelope))
        sig_b64 = b64e(sig)

        pub_b64 = b64e(self._pub_bytes) if (include_pub and self._pub_bytes) else None

        return SignedRequest(
            lumos_id=self.lumos_id,
            ts=ts,
            nonce=nonce,
            payload=payload,
            sig_b64=sig_b64,
            pub_b64=pub_b64,
        )

    @staticmethod
    def verify(lumos_id: str, public_key_bytes: bytes, ts: int, nonce: str, payload: Any, sig_b64: str) -> bool:
        try:
            if not public_key_bytes or len(public_key_bytes) != 32:
                return False
            pub = Ed25519PublicKey.from_public_bytes(public_key_bytes)

            envelope = {
                "lumos_id": (lumos_id or "").strip(),
                "ts": int(ts),
                "nonce": str(nonce),
                "payload": payload,
            }
            sig = b64d(sig_b64)
            pub.verify(sig, _canon(envelope))
            return True
        except Exception:
            return False


def _selftest() -> None:
    if os.getenv("LUMOS_SIGNER_SELFTEST", "0") != "1":
        return
    seed = get_random_bytes(32)
    priv = Ed25519PrivateKey.from_private_bytes(seed)
    pub = priv.public_key().public_bytes_raw()

    s = RequestSigner(lumos_id="TEST", private_key_bytes=seed, public_key_bytes=pub)
    payload = {"msg": "hello", "n": 1}
    req = s.sign(payload, ts=1710000000, nonce="abc", include_pub=True)

    ok = RequestSigner.verify(
        lumos_id=req.lumos_id,
        public_key_bytes=pub,
        ts=req.ts,
        nonce=req.nonce,
        payload=req.payload,
        sig_b64=req.sig_b64,
    )

    print("SELFTEST", "OK" if ok else "FAIL")


_selftest()
