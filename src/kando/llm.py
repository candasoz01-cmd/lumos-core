from core.context_store import (
    context_reuse_gate,
    load_context as _store_load_context,
    mark_reuse_active as _store_mark_reuse_active,
    set_repo_search_state as _store_set_repo_search_state,
    set_repo_navigation_state as _store_set_repo_navigation_state,
    set_pending_repo_waiting as _store_set_pending_repo_waiting,
    update_last_repo_query as _store_update_last_repo_query,
)
from core.runtime_state import add_runtime_event, get_feature_signal, mark_feature_signal, sync_kando_from_globals
from importlib.util import find_spec


def _response_text(resp):
    try:
        txt = getattr(resp, "output_text", None)
        if txt is not None:
            return txt
    except Exception:
        pass
    if resp is None:
        return "None"
    try:
        text = str(resp)
    except Exception:
        return ""

    if text is None:
        return ""

    return text


def normalize(text: str) -> str:
    return (
        text.lower()
        .strip()
        .replace("ı", "i")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ğ", "g")
        .replace("ç", "c")
    )


from kando.tools import repo_search  # noqa: E402
from kando.intent_engine import engine  # noqa: E402

LAST_OUTPUT = ""
_CONTEXT_GATE = context_reuse_gate()
CONTEXT = _store_load_context() if _CONTEXT_GATE.get("mode") == "persistent" else {}
PENDING = {}
LAST_REPO_RESULTS = []
LAST_REPO_INDEX = 0


def _context_store_enabled() -> bool:
    return bool(_CONTEXT_GATE.get("capability")) and str(_CONTEXT_GATE.get("health")) == "ok"


def update_last_repo_query(query: str) -> dict:
    if _context_store_enabled():
        return _store_update_last_repo_query(query)
    # context_reuse gate kapalı/degrade: yazma yok
    return CONTEXT


def set_pending_repo_waiting(waiting: bool) -> dict:
    if _context_store_enabled():
        return _store_set_pending_repo_waiting(waiting)
    # context_reuse gate kapalı/degrade: yazma yok
    return CONTEXT


def mark_reuse_active() -> dict:
    if _context_store_enabled():
        return _store_mark_reuse_active()
    # context_reuse gate kapalı/degrade: yazma yok
    return CONTEXT


def set_repo_search_state(*, query: str, has_results: bool) -> dict:
    if _context_store_enabled():
        return _store_set_repo_search_state(query=query, has_results=has_results)
    # context_reuse gate kapalı/degrade: yazma yok
    return CONTEXT


def set_repo_navigation_state(*, results_count: int, cursor_index: int, action: str | None = None) -> dict:
    if _context_store_enabled():
        return _store_set_repo_navigation_state(
            results_count=results_count,
            cursor_index=cursor_index,
            action=action,
        )
    # context_reuse gate kapalı/degrade: yazma yok
    return CONTEXT


def _help_text() -> str:
    return (
        "Komutlar:\n"
        "- durum\n"
        "- proje durum\n"
        "- repo: <arama>\n"
        "- stabil\n"
        "- devam\n"
        "- yardım"
    )


ACTION_MAP = {
    "status": lambda: "Lumos Core aktif. Sistem stabil.",
    "project": lambda: "Lumos Core aktif. Sistem stabil.",
    "changes": lambda: (
        "Son değişiklikler: intent engine ayrıldı, action map eklendi, "
        "repo search akıllı aramaya geçti."
    ),
    "last_output": lambda: LAST_OUTPUT if LAST_OUTPUT else "Henüz önceki çıktı yok.",
    "context": lambda: str(CONTEXT) if CONTEXT else "Context boş.",
    "suggest": lambda: (
        "Repo search + intent sistemi geliştirilebilir. "
        "Sonraki adım: gerçek dosya aramaya bağla."
    ),
    "continue": lambda: "Hazırım, devam ediyorum.",
    "devam": lambda: "Hazırım, devam ediyorum.",
    "stable": lambda: "Belirli scope içinde hatasız çalışıyor.",
    "stabil": lambda: "Belirli scope içinde hatasız çalışıyor.",
    "help": lambda: _help_text(),
    "reason": lambda: "Bağlama göre değişir, biraz aç.",
    "greeting": lambda: "Çalışıyorum.",
    "recent": lambda: "Yeni veri yok.",
    "version": lambda: "Lumos Core 0.1.0-secure-core",
    "health": lambda: "OK",
    "repo": lambda q: repo_search(q),
}

FOLLOWUPS = {
    "tekrar": "repeat",
    "aynı": "repeat",
    "aynisini": "repeat",
    "genişlet": "expand",
    "detay": "expand",
    "detaylandır": "expand",
    "sonrakı": "next",
    "sonraki": "next",
    "devam et": "next",
    "önceki": "prev",
    "onceki": "prev",
    "geri": "prev",
}

PRIORITY = {
    "repo": 100,
    "status": 80,
    "project": 80,
    "changes": 70,
    "suggest": 60,
    "continue": 50,
    "stable": 50,
    "last_output": 40,
    "help": 10,
}


def detect_intent(text: str) -> str:
    r = engine.match(text)
    if isinstance(r, list):
        return r[0] if r else "unknown"
    return r


def _log_event(event_type: str, detail: str) -> None:
    add_runtime_event(event_type, detail)


def _repo_search_capability_ok() -> bool:
    try:
        return find_spec("kando.tools") is not None
    except Exception:
        return False


def _repo_search_health_ok() -> bool:
    # Backend signal modeli: repo_search sinyali varsa sağlıklı kabul edilir.
    sig = get_feature_signal("repo_search")
    return bool((sig or "").strip())


def _run_repo_search_with_gate(query: str) -> tuple[str, bool]:
    q = (query or "").strip()
    if not _repo_search_capability_ok():
        return "Repo arama şu anda devre dışı.", False

    if not _repo_search_health_ok():
        # Degrade: yalnızca son bilinen session/context verisini kullan.
        if LAST_OUTPUT and LAST_REPO_RESULTS:
            return LAST_OUTPUT, False
        last_q = (CONTEXT.get("last_repo_query") or "").strip()
        if last_q:
            return f"Repo arama degrade modda. Son sorgu: {last_q}", False
        return "Repo arama geçici olarak hazır değil.", False

    return repo_search(q), True


def _repo_navigation_capability_ok() -> bool:
    try:
        return find_spec("kando.tools") is not None
    except Exception:
        return False


def _repo_navigation_health_ok() -> bool:
    if bool((get_feature_signal("repo_navigation") or "").strip()):
        return True
    return bool(LAST_REPO_RESULTS)


def _repo_navigation_degrade_output() -> str:
    if LAST_OUTPUT and LAST_REPO_RESULTS:
        return LAST_OUTPUT
    if LAST_REPO_RESULTS:
        return LAST_REPO_RESULTS[0]
    return "Repo gezinme geçici olarak hazır değil."


def _pending_completion_capability_ok() -> bool:
    try:
        return find_spec("core.context_store") is not None
    except Exception:
        return False


def _pending_completion_health_ok() -> bool:
    return _context_store_enabled()


def _llm_impl(prompt: str) -> str:
    global LAST_OUTPUT
    global CONTEXT
    global PENDING
    global LAST_REPO_RESULTS
    global LAST_REPO_INDEX
    global CONTEXT

    lines = prompt.strip().splitlines()
    if not lines:
        LAST_OUTPUT = "Boş girdin. 'yardım' yaz."
        return LAST_OUTPUT

    last = lines[-1].strip()
    if not last:
        LAST_OUTPUT = "Boş girdin."
        return LAST_OUTPUT

    lower = normalize(last)

    if lower.startswith("sec ") or lower.startswith("seç "):
        if not _repo_navigation_capability_ok():
            LAST_OUTPUT = "Repo gezinme kullanılamıyor."
            return LAST_OUTPUT
        if not _repo_navigation_health_ok():
            LAST_OUTPUT = _repo_navigation_degrade_output()
            return LAST_OUTPUT
        try:
            idx = int(lower.split()[1]) - 1
            if 0 <= idx < len(LAST_REPO_RESULTS):
                LAST_REPO_INDEX = idx
                LAST_OUTPUT = LAST_REPO_RESULTS[idx]
                CONTEXT = set_repo_navigation_state(
                    results_count=len(LAST_REPO_RESULTS),
                    cursor_index=LAST_REPO_INDEX,
                    action="select",
                )
                mark_feature_signal("repo_navigation")
                _log_event("repo_select", f"Repo sonucu seçildi: {idx + 1}")
                return LAST_OUTPUT
        except Exception:
            pass
        LAST_OUTPUT = "Geçerli seçim yok."
        _log_event("repo_select", "Geçersiz repo seçim denemesi.")
        return LAST_OUTPUT

    # doğal follow-up yakalama (anahtarlar normalize ile lower ile uyumlu)
    for key, val in FOLLOWUPS.items():
        if normalize(key) in lower:
            PENDING["followup"] = val

    # follow-up execution
    if PENDING.get("followup") == "repeat":
        PENDING.pop("followup", None)
        return LAST_OUTPUT if LAST_OUTPUT else "Tekrar edecek veri yok."

    if PENDING.get("followup") == "expand":
        PENDING.pop("followup", None)
        if LAST_OUTPUT:
            return LAST_OUTPUT + "\n(detay: daha fazla analiz eklenebilir)"
        return "Genişletilecek veri yok."

    if PENDING.get("followup") == "next":
        PENDING.pop("followup", None)
        if not _repo_navigation_capability_ok():
            LAST_OUTPUT = "Repo gezinme kullanılamıyor."
            return LAST_OUTPUT
        if not _repo_navigation_health_ok():
            LAST_OUTPUT = _repo_navigation_degrade_output()
            return LAST_OUTPUT
        if LAST_REPO_RESULTS:
            if LAST_REPO_INDEX + 1 < len(LAST_REPO_RESULTS):
                LAST_REPO_INDEX += 1
                LAST_OUTPUT = LAST_REPO_RESULTS[LAST_REPO_INDEX]
                CONTEXT = set_repo_navigation_state(
                    results_count=len(LAST_REPO_RESULTS),
                    cursor_index=LAST_REPO_INDEX,
                    action="next",
                )
                mark_feature_signal("repo_navigation")
                _log_event("repo_next", "Repo sonucu sonraki kayda ilerledi.")
                return LAST_OUTPUT
            LAST_OUTPUT = "Sonraki sonuç yok."
            _log_event("repo_next", "Sonraki repo sonucu yok.")
            return LAST_OUTPUT
        LAST_OUTPUT = "İlerleyecek sonuç yok."
        _log_event("repo_next", "Repo gezinme listesi boş.")
        return LAST_OUTPUT

    if PENDING.get("followup") == "prev":
        PENDING.pop("followup", None)
        if not _repo_navigation_capability_ok():
            LAST_OUTPUT = "Repo gezinme kullanılamıyor."
            return LAST_OUTPUT
        if not _repo_navigation_health_ok():
            LAST_OUTPUT = _repo_navigation_degrade_output()
            return LAST_OUTPUT
        if LAST_REPO_RESULTS:
            if LAST_REPO_INDEX - 1 >= 0:
                LAST_REPO_INDEX -= 1
                LAST_OUTPUT = LAST_REPO_RESULTS[LAST_REPO_INDEX]
                CONTEXT = set_repo_navigation_state(
                    results_count=len(LAST_REPO_RESULTS),
                    cursor_index=LAST_REPO_INDEX,
                    action="prev",
                )
                mark_feature_signal("repo_navigation")
                _log_event("repo_prev", "Repo sonucu önceki kayda döndü.")
                return LAST_OUTPUT
            LAST_OUTPUT = "Önceki sonuç yok."
            _log_event("repo_prev", "Önceki repo sonucu yok.")
            return LAST_OUTPUT
        LAST_OUTPUT = "Geri gidilecek sonuç yok."
        _log_event("repo_prev", "Repo gezinme listesi boş.")
        return LAST_OUTPUT

    # pending flow (yarım komut tamamlama)
    if PENDING.get("intent") == "repo":
        if not _pending_completion_capability_ok():
            PENDING.clear()
        elif not _pending_completion_health_ok():
            PENDING.clear()
            CONTEXT = set_pending_repo_waiting(False)
            LAST_OUTPUT = "Bekleyen işlem sıfırlandı. Komutu tekrar yaz."
            return LAST_OUTPUT
        else:
            q = lower.strip()
            PENDING.clear()
            CONTEXT = set_pending_repo_waiting(False)
            CONTEXT = update_last_repo_query(q)
            repo_out, repo_ok = _run_repo_search_with_gate(q)
            LAST_OUTPUT = repo_out
            if repo_ok:
                LAST_REPO_RESULTS = [x for x in LAST_OUTPUT.split("\n\n") if x.strip()]
                LAST_REPO_INDEX = 0
                CONTEXT = set_repo_search_state(query=q, has_results=bool(LAST_REPO_RESULTS))
                CONTEXT = set_repo_navigation_state(
                    results_count=len(LAST_REPO_RESULTS),
                    cursor_index=LAST_REPO_INDEX,
                    action="search",
                )
                mark_feature_signal("repo_search")
            _log_event("pending_repo_complete", f"Pending repo sorgusu tamamlandı: {q or '—'}")
            mark_feature_signal("pending_completion")
            return LAST_OUTPUT

    intent = engine.match(lower)

    # basit context yakalama (repo:)
    if "repo:" in lower:
        q = lower.split("repo:", 1)[1].strip()
        if not q:
            if not _pending_completion_capability_ok():
                LAST_OUTPUT = "repo: <arama> yaz."
                return LAST_OUTPUT
            if not _pending_completion_health_ok():
                PENDING.clear()
                CONTEXT = set_pending_repo_waiting(False)
                LAST_OUTPUT = "Pending geçici olarak kapalı. repo: <arama> yaz."
                return LAST_OUTPUT
            PENDING["intent"] = "repo"
            CONTEXT = set_pending_repo_waiting(True)
            LAST_OUTPUT = "Repo arama geçici olarak hazır değil."
            _log_event("pending_repo_wait", "Repo için sorgu bekleniyor.")
            mark_feature_signal("pending_completion")
            return LAST_OUTPUT
        CONTEXT = update_last_repo_query(q)

    if isinstance(intent, list):
        intents = list(intent)
        if ("repo" in lower.split() or "repo:" in lower) and "repo" not in intents:
            intents.append("repo")

        # priority + unique + order
        seen = set()
        ordered = sorted(intents, key=lambda x: PRIORITY.get(x, 0), reverse=True)

        outputs = []
        for i in ordered:
            if i in seen:
                continue
            seen.add(i)

            fn = ACTION_MAP.get(i)
            if not fn:
                continue

            # repo özel davranış
            if i == "repo":
                if lower.startswith("repo:"):
                    q = lower.split("repo:", 1)[1].strip()
                    if q:
                        repo_out, repo_ok = _run_repo_search_with_gate(q)
                        outputs.append(repo_out)
                        if repo_ok:
                            LAST_REPO_RESULTS = [x for x in repo_out.split("\n\n") if x.strip()]
                            LAST_REPO_INDEX = 0
                            CONTEXT = set_repo_search_state(query=q, has_results=bool(LAST_REPO_RESULTS))
                            CONTEXT = set_repo_navigation_state(
                                results_count=len(LAST_REPO_RESULTS),
                                cursor_index=LAST_REPO_INDEX,
                                action="search",
                            )
                            mark_feature_signal("repo_search")
                            _log_event("repo_search", f"Repo araması yapıldı: {q}")
                else:
                    q = CONTEXT.get("last_repo_query")
                    if q:
                        repo_out, repo_ok = _run_repo_search_with_gate(q)
                        outputs.append(repo_out)
                        if repo_ok:
                            LAST_REPO_RESULTS = [x for x in repo_out.split("\n\n") if x.strip()]
                            LAST_REPO_INDEX = 0
                            CONTEXT = set_repo_search_state(query=q, has_results=bool(LAST_REPO_RESULTS))
                            CONTEXT = set_repo_navigation_state(
                                results_count=len(LAST_REPO_RESULTS),
                                cursor_index=LAST_REPO_INDEX,
                                action="search",
                            )
                            mark_feature_signal("repo_search")
                            CONTEXT = mark_reuse_active()
                            _log_event("repo_search", f"Repo araması context ile tekrarlandı: {q}")
                continue

            outputs.append(fn())

        LAST_OUTPUT = "\n".join(outputs)
        if outputs:
            mark_feature_signal("intent_engine")
        return LAST_OUTPUT

    fn = ACTION_MAP.get(intent)
    if fn:
        if intent == "repo":
            if lower.startswith("repo:"):
                q = lower.split("repo:", 1)[1].strip()
                LAST_OUTPUT, repo_ok = _run_repo_search_with_gate(q)
                if repo_ok:
                    LAST_REPO_RESULTS = [x for x in LAST_OUTPUT.split("\n\n") if x.strip()]
                    LAST_REPO_INDEX = 0
                    CONTEXT = set_repo_search_state(query=q, has_results=bool(LAST_REPO_RESULTS))
                    CONTEXT = set_repo_navigation_state(
                        results_count=len(LAST_REPO_RESULTS),
                        cursor_index=LAST_REPO_INDEX,
                        action="search",
                    )
                    mark_feature_signal("repo_search")
                    _log_event("repo_search", f"Repo araması yapıldı: {q or '—'}")
                mark_feature_signal("intent_engine")
                return LAST_OUTPUT
            q = CONTEXT.get("last_repo_query")
            if q:
                LAST_OUTPUT, repo_ok = _run_repo_search_with_gate(q)
                if repo_ok:
                    LAST_REPO_RESULTS = [x for x in LAST_OUTPUT.split("\n\n") if x.strip()]
                    LAST_REPO_INDEX = 0
                    CONTEXT = set_repo_search_state(query=q, has_results=bool(LAST_REPO_RESULTS))
                    CONTEXT = set_repo_navigation_state(
                        results_count=len(LAST_REPO_RESULTS),
                        cursor_index=LAST_REPO_INDEX,
                        action="search",
                    )
                    mark_feature_signal("repo_search")
                    CONTEXT = mark_reuse_active()
                    _log_event("repo_search", f"Repo araması context ile tekrarlandı: {q}")
                mark_feature_signal("intent_engine")
                return LAST_OUTPUT
            LAST_OUTPUT = "repo: <arama> yaz."
            _log_event("repo_search", "Repo araması için sorgu eksik.")
            mark_feature_signal("intent_engine")
            return LAST_OUTPUT
        if intent in ("continue", "devam"):
            q = (CONTEXT.get("last_repo_query") or "").strip()
            if q:
                LAST_OUTPUT, repo_ok = _run_repo_search_with_gate(q)
                if repo_ok:
                    LAST_REPO_RESULTS = [x for x in LAST_OUTPUT.split("\n\n") if x.strip()]
                    LAST_REPO_INDEX = 0
                    CONTEXT = set_repo_search_state(query=q, has_results=bool(LAST_REPO_RESULTS))
                    CONTEXT = set_repo_navigation_state(
                        results_count=len(LAST_REPO_RESULTS),
                        cursor_index=LAST_REPO_INDEX,
                        action="search",
                    )
                    mark_feature_signal("repo_search")
                    CONTEXT = mark_reuse_active()
                    _log_event("repo_search", f"Repo araması devam ile tekrarlandı: {q}")
                mark_feature_signal("intent_engine")
                return LAST_OUTPUT
        mark_feature_signal("intent_engine")
        LAST_OUTPUT = fn()
        if intent in ("status", "project"):
            _log_event("status_query", "Durum sorgusu yapıldı.")
        elif intent == "help":
            _log_event("help_call", "Yardım komutu çağrıldı.")
        else:
            _log_event("intent", f"Intent işlendi: {intent}")
        return LAST_OUTPUT

    if len(normalize(last)) > 2:
        # fallback mini yorumlayıcı
        text = lower

        if any(normalize(x) in text for x in ["nasıl", "neden", "niye"]):
            LAST_OUTPUT = "Sebep/işleyiş sorusu algılandı. Bağlama göre analiz gerekir."
            return LAST_OUTPUT

        if any(normalize(x) in text for x in ["ne", "nedir"]):
            LAST_OUTPUT = "Tanım/çıktı sorusu. Daha spesifik yazarsan netleşir."
            return LAST_OUTPUT

        if any(normalize(x) in text for x in ["yap", "et", "çalıştır"]):
            LAST_OUTPUT = "Aksiyon isteği algılandı. Komut formatına yakın yaz."
            return LAST_OUTPUT

        LAST_OUTPUT = "Tam anlaşılmadı ama bir şey soruyorsun. 'yardım' yaz veya biraz netleştir."
        return LAST_OUTPUT

    LAST_OUTPUT = "Sonuç bulunamadı"
    return LAST_OUTPUT


def llm(prompt: str) -> str:
    out = _llm_impl(prompt)
    sync_kando_from_globals(LAST_OUTPUT, CONTEXT, PENDING, LAST_REPO_RESULTS, LAST_REPO_INDEX)
    return out
