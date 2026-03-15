import os
import json
import time
from typing import Any, Tuple

from security.crypto import b64d
from security.request_signer import RequestSigner


class ModelClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("LUMOS_API_KEY")
        self._openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()

        self._ts_skew = int(os.getenv("LUMOS_TS_SKEW", "60"))

        self._nonce_ttl = int(os.getenv("LUMOS_NONCE_TTL", "120"))
        self._nonce_cache_max = int(os.getenv("LUMOS_NONCE_CACHE_MAX", "200"))

        self._nonce_cache: dict[str, int] = {}

        self._server_pub_b64 = (os.getenv("LUMOS_SERVER_PUB_B64", "") or "").strip()

    def _cleanup_nonces(self, now: int) -> None:
        if not self._nonce_cache:
            return
        dead = [n for n, exp in self._nonce_cache.items() if exp <= now]
        for n in dead:
            self._nonce_cache.pop(n, None)
        if len(self._nonce_cache) > self._nonce_cache_max:
            items = sorted(self._nonce_cache.items(), key=lambda x: x[1])
            drop = len(items) - self._nonce_cache_max
            for n, _ in items[:drop]:
                self._nonce_cache.pop(n, None)

    def _server_sim_verify(self, signed_json: str) -> Tuple[bool, str]:
        try:
            obj = json.loads(signed_json)
        except Exception:
            return False, "bad_json"

        lumos_id = (obj.get("lumos_id") or "").strip()
        ts = obj.get("ts")
        nonce = (obj.get("nonce") or "").strip()
        payload: Any = obj.get("payload")
        sig_b64 = (obj.get("sig_b64") or "").strip()
        pub_b64 = (obj.get("pub_b64") or "").strip()

        if not lumos_id or ts is None or not nonce or not sig_b64:
            return False, "missing_fields"

        try:
            ts_i = int(ts)
        except Exception:
            return False, "bad_ts"

        now = int(time.time())

        if abs(now - ts_i) > self._ts_skew:
            return False, "ts_skew"

        self._cleanup_nonces(now)

        if nonce in self._nonce_cache:
            return False, "replay"

        pub_source = pub_b64 or self._server_pub_b64
        if not pub_source:
            return False, "no_pubkey"

        try:
            pub_bytes = b64d(pub_source)
        except Exception:
            return False, "bad_pubkey_b64"

        ok = RequestSigner.verify(
            lumos_id=lumos_id,
            public_key_bytes=pub_bytes,
            ts=ts_i,
            nonce=nonce,
            payload=payload,
            sig_b64=sig_b64,
        )
        if not ok:
            return False, "bad_sig"

        self._nonce_cache[nonce] = now + self._nonce_ttl
        return True, "ok"

    def is_openai_available(self) -> bool:
        """True when OPENAI_API_KEY is set; enables direct OpenAI path without signing."""
        return bool(self._openai_key)

    def generate(self, prompt: str) -> str:
        if os.getenv("LUMOS_SERVER_SIM", "0") == "1":
            ok, reason = self._server_sim_verify(prompt)
            if ok:
                return json.dumps({"ok": True, "response": "Sim OK", "error": "", "server": "sim"}, ensure_ascii=False)
            return json.dumps({"ok": False, "response": "", "error": reason or "reject", "server": "sim"}, ensure_ascii=False)

        if self._openai_key:
            return self._generate_openai(prompt)
        return "Yanındayım."

    def _generate_openai(self, prompt: str) -> str:
        """Call OpenAI Chat Completions with the given prompt. Returns response text or error fallback."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._openai_key)
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "512")),
            )
            if response.choices:
                content = (response.choices[0].message.content or "").strip()
                return content if content else "Yanıt yok."
            return "Yanıt yok."
        except Exception:
            return "Yanıt üretilirken hata oluştu."
