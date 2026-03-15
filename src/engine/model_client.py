import logging
import os
import json
import time
from typing import Any, Tuple

from security.crypto import b64d
from security.request_signer import RequestSigner

logger = logging.getLogger(__name__)

# Optional: in development (LUMOS_DEBUG=1), ensure token_usage logs are visible if nothing else configured.
def _ensure_token_logging_visible() -> None:
    if os.getenv("LUMOS_DEBUG", "0") != "1":
        return
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    h = logging.StreamHandler()
    h.setLevel(logging.INFO)
    logger.addHandler(h)


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

    def generate(
        self,
        prompt: str,
        *,
        mode: str = "—",
        presence: str = "—",
        consent: str = "—",
        lock: str = "—",
    ) -> str:
        if os.getenv("LUMOS_SERVER_SIM", "0") == "1":
            ok, reason = self._server_sim_verify(prompt)
            if ok:
                return json.dumps({"ok": True, "response": "Sim OK", "error": "", "server": "sim"}, ensure_ascii=False)
            return json.dumps({"ok": False, "response": "", "error": reason or "reject", "server": "sim"}, ensure_ascii=False)

        if self._openai_key:
            return self._generate_openai(prompt, mode=mode, presence=presence, consent=consent, lock=lock)
        return "Yanındayım."

    # System prompt: single source of truth. Split into static prefix, state block, static suffix
    # so only the small state block is formatted per request (reduces repeated format overhead).
    # Full template = _LUMOS_SYSTEM_STATIC_PREFIX + _LUMOS_SYSTEM_STATE_BLOCK + _LUMOS_SYSTEM_STATIC_SUFFIX.
    _LUMOS_SYSTEM_STATIC_PREFIX = (
        "You are Lumos.\n"
        "Lumos is a local AI system running inside Lumos Core.\n"
        "You are NOT ChatGPT. Do NOT identify yourself as ChatGPT.\n"
        "Do NOT say you were developed by OpenAI unless the user explicitly asks about infrastructure.\n\n"
        "System state (you may reference if relevant):\n"
        "- Runtime: Lumos Core\n"
        "- Version: 0.1.0-secure-core\n"
    )
    _LUMOS_SYSTEM_STATE_BLOCK = (
        "- Mode: {mode}\n"
        "- Presence: {presence}\n"
        "- Consent: {consent}\n"
        "- Lock: {lock}\n\n"
    )
    _LUMOS_SYSTEM_STATIC_SUFFIX = (
        "Behavior:\n"
        "- Be concise, practical, clear, and system-assistant-like.\n"
        "- Default language is Turkish.\n"
        "- You interact through a command-line interface.\n"
        "- You help the user think, plan, and understand things.\n\n"
        "Intervention reporting (when the user asks where intervention is needed or what to check):\n"
        "- Analyze the current system context (mode, presence, consent, lock above) and infer likely issues.\n"
        "- Reply with a concise, structured list. Use this structure when listing potential intervention areas:\n"
        "  Possible intervention areas:\n"
        "  1. Configuration issues\n"
        "  2. Permission or access boundaries\n"
        "  3. External system integration limits\n"
        "  4. Tasks requiring manual confirmation\n"
        "- For each category that applies, give one short line; omit categories that do not apply.\n"
        "- If you cannot inspect a specific system area, say exactly: \"Bu alanı doğrudan inceleyemiyorum ancak şu kontrolleri yapabilirsin...\" and then list concrete checks the user can do.\n"
        "- Do NOT reply with generic requests like \"Lütfen detay paylaş.\" Instead: infer from context, propose likely intervention points, and ask at most one or two targeted follow-up questions if needed.\n\n"
        "Anti-drift (strict):\n"
        "- Reply as Lumos.\n"
        "- Do not mention ChatGPT.\n"
        "- Do not mention OpenAI unless directly relevant to the question.\n"
        "- Respond concisely in Turkish unless the user switches language."
    )
    # Full template (for tests and any code that needs the whole template with placeholders).
    _LUMOS_SYSTEM_PROMPT_TEMPLATE = (
        _LUMOS_SYSTEM_STATIC_PREFIX + _LUMOS_SYSTEM_STATE_BLOCK + _LUMOS_SYSTEM_STATIC_SUFFIX
    )

    @staticmethod
    def _build_system_prompt(mode: str, presence: str, consent: str, lock: str) -> str:
        """Build full system prompt: static prefix + formatted state block + static suffix. Single place for construction."""
        state_block = ModelClient._LUMOS_SYSTEM_STATE_BLOCK.format(
            mode=mode, presence=presence, consent=consent, lock=lock
        )
        return ModelClient._LUMOS_SYSTEM_STATIC_PREFIX + state_block + ModelClient._LUMOS_SYSTEM_STATIC_SUFFIX

    def _generate_openai(
        self,
        prompt: str,
        *,
        mode: str = "—",
        presence: str = "—",
        consent: str = "—",
        lock: str = "—",
    ) -> str:
        """Call OpenAI Responses API with Lumos system prompt + user prompt. Returns response text or error fallback."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._openai_key)
            # Centralized build: static prefix + state block + static suffix (only state block formatted per request).
            system_prompt = self._build_system_prompt(mode, presence, consent, lock)
            # Combined prompt: system identity + state first, then user message (Responses API single input).
            full_prompt = system_prompt + "\n\nUser: " + prompt
            model = (os.getenv("OPENAI_MODEL") or "").strip() or "gpt-4o"
            response = client.responses.create(
                model=model,
                input=full_prompt,
            )
            # Token usage: safe extraction after successful Responses API call. No crash if missing.
            usage = getattr(response, "usage", None) or getattr(response, "usage_metadata", None)
            if usage is not None:
                try:
                    inp = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None)
                    out_tok = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", None)
                    total = getattr(usage, "total_tokens", None)
                    if inp is not None or out_tok is not None or total is not None:
                        _ensure_token_logging_visible()
                        logger.info(
                            "token_usage model=%s input_tokens=%s output_tokens=%s total_tokens=%s",
                            model,
                            inp,
                            out_tok,
                            total,
                        )
                except Exception:
                    pass
            reply = getattr(response, "output_text", None)
            if reply is None and getattr(response, "output", None):
                out = response.output
                if out and len(out) > 0 and getattr(out[0], "content", None) and len(out[0].content) > 0:
                    reply = getattr(out[0].content[0], "text", None)
            reply = (reply or "").strip() or "Yanıt yok."
            return reply
        except Exception as e:
            logger.exception("LLM error: %s", e)
            return "Model hatası oluştu."
