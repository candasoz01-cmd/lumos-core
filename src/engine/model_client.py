import logging
import os
import json
import time
from typing import Any, Tuple

from security.crypto import b64d
from security.request_signer import RequestSigner

logger = logging.getLogger(__name__)

PURPOSE_CHAT = "chat"
PURPOSE_CYBER = "cyber"
CYBER_AVAILABLE = "available"
CYBER_NOT_CONFIGURED = "not_configured"
CYBER_UNAVAILABLE = "unavailable"
CYBER_UNKNOWN = "unknown"
_CHAT_DEFAULT_MODEL = "gpt-4.1-mini"
_CYBER_UNAVAILABLE_TYPES = frozenset(
    {
        "NotFoundError",
        "PermissionDeniedError",
    }
)


class CyberModelError(Exception):
    """Fail-closed cyber model path. status is not_configured | unavailable | unknown."""

    def __init__(self, status: str, model: str = "") -> None:
        self.status = status
        self.model = model
        super().__init__(status)


def resolve_openai_model(purpose: str = PURPOSE_CHAT) -> tuple[str, str | None]:
    """Return (model, cyber_error_status). Chat: OPENAI_MODEL_CHAT then OPENAI_MODEL. Cyber: no fallback."""
    normalized = (purpose or PURPOSE_CHAT).strip().lower() or PURPOSE_CHAT
    if normalized != PURPOSE_CYBER:
        model = (
            (os.getenv("OPENAI_MODEL_CHAT") or "").strip()
            or (os.getenv("OPENAI_MODEL") or "").strip()
            or _CHAT_DEFAULT_MODEL
        )
        return model, None
    model = (os.getenv("OPENAI_MODEL_CYBER") or "").strip()
    if not model:
        return "", CYBER_NOT_CONFIGURED
    return model, None


def classify_cyber_api_error(exc: BaseException) -> str:
    """Map a single failed cyber API call. No retry. Does not read response bodies."""
    raw_code = getattr(exc, "status_code", None)
    code: int | None
    try:
        code = int(raw_code) if raw_code is not None else None
    except (TypeError, ValueError):
        code = None
    if code in (403, 404):
        return CYBER_UNAVAILABLE
    if code == 401 or (code is not None and code >= 500):
        return CYBER_UNKNOWN
    if type(exc).__name__ in _CYBER_UNAVAILABLE_TYPES:
        return CYBER_UNAVAILABLE
    return CYBER_UNKNOWN


def log_cyber_model(status: str, model: str) -> None:
    """Log only status and model name — never API keys or raw response bodies."""
    logger.info("cyber_model status=%s model=%s", status, model or "")


def _safe_int(value: Any) -> int:
    """Convert usage fields to int; strict so MagicMock/unknown types become 0, never 1."""
    if isinstance(value, bool):
        return 0
    if type(value) is int:
        return value
    if type(value) is float:
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


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
        purpose: str = PURPOSE_CHAT,
    ) -> str:
        if os.getenv("LUMOS_SERVER_SIM", "0") == "1":
            ok, reason = self._server_sim_verify(prompt)
            if ok:
                return json.dumps({"ok": True, "response": "Sim OK", "error": "", "server": "sim"}, ensure_ascii=False)
            return json.dumps({"ok": False, "response": "", "error": reason or "reject", "server": "sim"}, ensure_ascii=False)

        if (purpose or PURPOSE_CHAT).strip().lower() == PURPOSE_CYBER:
            return self._generate_openai(
                prompt,
                mode=mode,
                presence=presence,
                consent=consent,
                lock=lock,
                purpose=PURPOSE_CYBER,
            )
        if self._openai_key:
            return self._generate_openai(
                prompt,
                mode=mode,
                presence=presence,
                consent=consent,
                lock=lock,
                purpose=PURPOSE_CHAT,
            )
        return "Yanındayım."

    # System prompt: single source of truth. Split into static prefix, state block, static suffix
    # so only the small state block is formatted per request (reduces repeated format overhead).
    # Full template = _LUMOS_SYSTEM_STATIC_PREFIX + _LUMOS_SYSTEM_STATE_BLOCK + _LUMOS_SYSTEM_STATIC_SUFFIX.
    _LUMOS_SYSTEM_STATIC_PREFIX = (
        "You are Lumos.\n"
        "Lumos is an AI control / assistant layer under the We Lock AI umbrella. "
        "Product identity here is Lumos (not the raw foundation-model brand). "
        "This deployment runs inside Lumos Core.\n\n"
        "Identity rules (strict):\n"
        "- Do NOT say you are ChatGPT, a ChatGPT variant, or an \"OpenAI assistant\".\n"
        "- Do NOT claim OpenAI built Lumos or that Lumos *is* ChatGPT.\n"
        "- Do NOT present yourself as \"OpenAI-developed\"; OpenAI may supply model APIs, not product ownership.\n"
        "- The user talks to you through this Lumos interface; keep product vs model provider distinct.\n\n"
        "When the user asks who you are (especially in Turkish), answer briefly using this core wording "
        "(you may shorten slightly but do not contradict):\n"
        "\"Ben Lumos. We Lock AI çatısı altında çalışan, kullanıcıya yardımcı olmak için tasarlanmış bir yapay zekâ kontrol/asistan katmanıyım.\"\n\n"
        "When the user asks about technical infrastructure / model provider / API (Turkish), answer honestly and briefly, e.g.:\n"
        "\"Bazı yanıt üretimlerinde OpenAI modelleri gibi harici yapay zekâ servislerinden yararlanabilirim; "
        "ancak bu arayüzde ürün kimliğim Lumos'tur.\"\n"
        "Do not deny external model usage if true; do not imply OpenAI owns the Lumos product.\n\n"
        "If asked whether your root is ChatGPT or the same as ChatGPT (Turkish), use essentially:\n"
        "\"Doğrudan ChatGPT olarak konumlanmam; Lumos, We Lock AI ürünü olarak çalışan bir katmandır. "
        "Model altyapısında OpenAI gibi servislerden yararlanılabilir.\"\n\n"
        "Ownership / responsibility (Turkish), when relevant — keep short:\n"
        "\"Lumos çıktılarının nihai kullanımı ve kararı kullanıcıdadır; Lumos destekleyici katmandır.\"\n\n"
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
        "Rol (Türkçe yanıt öntanımlı; kullanıcı başka dilde yazarsa o dile uy):\n"
        "Amacın sohbet etmek değil, işi doğru yönlendirmek. Kısa, net, doğrudan; kurumsal veya "
        "yumuşatılmış dil yok.\n\n"
        "İletişim:\n"
        "- Gereksiz açıklama yok; uzun cevap verme.\n"
        "- Yanlış veya imkânsızsa doğrudan söyle.\n"
        "- Tahmin ediyorsan açıkça söyle; emin değilsen kesin iddia etme.\n"
        "- Gereksiz soru yağdırma; en fazla tek hedefli soru.\n\n"
        "Görev–sohbet ayrımı (her mesajda):\n"
        "- Mesajı önce sınıflandır.\n"
        "- Yalnızca sohbet / bilgi / fikir (sistemde işlem isteği yoksa) → normal, kısa cevap ver.\n"
        "- Repo, dosya, komut, patch, silme, deploy vb. bir işlem istiyorsa → görev modu.\n\n"
        "Görev modu (zorunlu):\n"
        "- Task ≠ Execution: görev tanımı ile yürütme aynı şey değildir. Arada her zaman onay "
        "(approval) vardır; sen yürütmezsin.\n"
        "- Asla doğrudan işlem yapma veya yapmış gibi konuşma; köprü/onay akışı execution’ı yapar.\n"
        "- Önce kısa analiz.\n"
        "- En kritik 2–3 seçenek sun; her biri için risk: düşük / orta / yüksek.\n"
        "- En mantıklı seçeneği tek cümleyle öner.\n"
        "- Açık onay iste (ör. hangi seçenek, hangi kapsam); onay olmadan execution yok.\n\n"
        "Yasaklar:\n"
        "- Onaysız işlem iddiası veya onaysız yürütme\n"
        "- Gereksiz uzun yanıt, kurumsal ton\n"
        "- Emin olmadığın şeyi kesin söylemek\n\n"
        "Anti-drift (strict):\n"
        "- Reply as Lumos (We Lock AI product layer).\n"
        "- Do not identify as ChatGPT; do not volunteer that you \"are\" ChatGPT.\n"
        "- Do not volunteer vendor/model-provider names in unrelated small talk.\n"
        "- If the user explicitly asks about infrastructure, ChatGPT vs Lumos, or providers: answer truthfully "
        "and briefly; naming OpenAI or similar is allowed there.\n"
        "- Turkish identity and responsibility lines above take priority for Turkish answers.\n"
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
        purpose: str = PURPOSE_CHAT,
    ) -> str:
        """Call OpenAI Responses API with Lumos system prompt + user prompt. Returns response text or error fallback."""
        is_cyber = (purpose or PURPOSE_CHAT).strip().lower() == PURPOSE_CYBER
        model, cyber_status = resolve_openai_model(purpose)
        if is_cyber and cyber_status:
            log_cyber_model(cyber_status, model)
            raise CyberModelError(cyber_status, model)
        if is_cyber and not self._openai_key:
            log_cyber_model(CYBER_NOT_CONFIGURED, model)
            raise CyberModelError(CYBER_NOT_CONFIGURED, model)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._openai_key)
            # Centralized build: static prefix + state block + static suffix (only state block formatted per request).
            system_prompt = self._build_system_prompt(mode, presence, consent, lock)
            # Combined prompt: system identity + state first, then user message (Responses API single input).
            full_prompt = system_prompt + "\n\nUser: " + prompt
            try:
                if is_cyber:
                    # Cyber: one create() only. No TypeError retry, no chat-model fallback.
                    response = client.responses.create(
                        model=model,
                        input=full_prompt,
                        timeout=10,
                    )
                else:
                    try:
                        response = client.responses.create(
                            model=model,
                            input=full_prompt,
                            timeout=10,
                        )
                    except TypeError:
                        response = client.responses.create(
                            model=model,
                            input=full_prompt,
                        )
            except Exception as exc:
                if is_cyber:
                    status = classify_cyber_api_error(exc)
                    log_cyber_model(status, model)
                    raise CyberModelError(status, model) from None
                return "Model yanıt vermedi"
            # Token usage: strict extraction; only real int/float/digit-string count (MagicMock -> 0).
            usage = getattr(response, "usage", None) or getattr(response, "usage_metadata", None)
            if usage is not None:
                try:
                    # Supported usage field names: input_tokens, prompt_tokens, output_tokens, completion_tokens, total_tokens
                    in_raw = getattr(usage, "input_tokens", None)
                    if not isinstance(in_raw, (int, float)):
                        in_raw = getattr(usage, "prompt_tokens", None)

                    out_raw = getattr(usage, "output_tokens", None)
                    if not isinstance(out_raw, (int, float)):
                        out_raw = getattr(usage, "completion_tokens", None)

                    input_tokens = _safe_int(in_raw)
                    output_tokens = _safe_int(out_raw)

                    total_raw = getattr(usage, "total_tokens", None)
                    if not isinstance(total_raw, (int, float)):
                        total_raw = input_tokens + output_tokens

                    total_tokens = _safe_int(total_raw)
                    _ensure_token_logging_visible()
                    logger.info(
                        "token_usage model=%s input_tokens=%s output_tokens=%s total_tokens=%s",
                        model,
                        input_tokens,
                        output_tokens,
                        total_tokens,
                    )
                except Exception:
                    pass
            reply = getattr(response, "output_text", None)
            if reply is None and getattr(response, "output", None):
                out = response.output
                if out and len(out) > 0 and getattr(out[0], "content", None) and len(out[0].content) > 0:
                    reply = getattr(out[0].content[0], "text", None)
            reply = (reply or "").strip() or "Yanıt yok."
            if is_cyber:
                log_cyber_model(CYBER_AVAILABLE, model)
            return reply
        except CyberModelError:
            raise
        except Exception as e:
            if is_cyber:
                log_cyber_model(CYBER_UNKNOWN, model)
                raise CyberModelError(CYBER_UNKNOWN, model) from None
            logger.exception("LLM error: %s", e)
            return "Model hatası oluştu."
