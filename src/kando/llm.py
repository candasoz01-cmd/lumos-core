from core.context_store import (
    load_context,
    mark_reuse_active,
    set_repo_search_state,
    set_repo_navigation_state,
    set_pending_repo_waiting,
    update_last_repo_query,
)
from core.runtime_state import add_runtime_event, mark_feature_signal, sync_kando_from_globals


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
CONTEXT = load_context()
PENDING = {}
LAST_REPO_RESULTS = []
LAST_REPO_INDEX = 0


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
        q = lower.strip()
        PENDING.clear()
        CONTEXT = set_pending_repo_waiting(False)
        CONTEXT = update_last_repo_query(q)
        LAST_OUTPUT = repo_search(q)
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
            PENDING["intent"] = "repo"
            CONTEXT = set_pending_repo_waiting(True)
            LAST_OUTPUT = "Ne arıyorsun?"
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
                        repo_out = fn(q)
                        outputs.append(repo_out)
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
                        repo_out = fn(q)
                        outputs.append(repo_out)
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
                LAST_OUTPUT = fn(q)
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
                LAST_OUTPUT = fn(q)
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
                LAST_OUTPUT = repo_search(q)
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
