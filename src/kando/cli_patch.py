from kando.context import collect_context

def detect_intent(user_input: str) -> str:
    u = (user_input or "").lower().strip()
    if any(x in u for x in ["hangi fonksiyon", "hangi işlev", "hangi islev", "changed_functions"]):
        return "changed_functions"
    if any(x in u for x in ["risk", "riskli", "kritik", "tehlike"]):
        return "risk"
    if any(x in u for x in ["test", "test listesi", "doğrula", "dogrula", "kontrol"]):
        return "test"
    if any(x in u for x in ["özet", "ozet", "ne değişti", "ne degisti", "durum"]):
        return "summary"
    if any(x in u for x in ["patch", "aksiyon", "aksiyon planı", "aksiyon plani", "plan çıkar", "plan cikar", "uygula", "düzelt", "duzelt", "değiştir", "degistir", "ekle", "sil", "refactor"]):
        return "action"
    return "chat"

def _trim(s: str, n: int = 8000) -> str:
    s = s or ""
    return s[:n]

def enrich_prompt(user_input: str) -> str:
    intent = detect_intent(user_input)

    if intent == "chat":
        return f"""
Kullanıcıyla normal sohbet et.
Cevabı Türkçe, kısa ve doğal ver.

USER:
{user_input}
""".strip()

    ctx = collect_context()
    changed_functions = _trim(ctx.get("changed_functions", ""), 3000)
    changed_snippets = _trim(ctx.get("changed_snippets", ""), 6000)
    git_branch = ctx.get("git_branch", "")
    last_commit = ctx.get("last_commit", "")
    git_status = _trim(ctx.get("git_status", ""), 2000)

    if intent == "changed_functions":
        return f"""
Aşağıdaki değişikliklerden sadece değişen fonksiyonları çıkar.
Cevabı Türkçe ver.

Format:
CHANGED_FUNCTIONS:
- <fonksiyon>
- <fonksiyon>

KISA_YORUM:
- <en fazla 2 madde>

GIT_BRANCH:
{git_branch}

LAST_COMMIT:
{last_commit}

GIT_STATUS:
{git_status}

CHANGED_FUNCTIONS_SOURCE:
{changed_functions}

USER:
{user_input}
""".strip()

    if intent == "risk":
        return f"""
Aşağıdaki değişiklikler için sadece en riskli 3 yeri çıkar.
Cevabı Türkçe ver.

Format:
EN_RISKLI_3_YER:
1. <dosya:fonksiyon>
2. <dosya:fonksiyon>
3. <dosya:fonksiyon>

NEDEN_RISKLI:
1. <tek cümle>
2. <tek cümle>
3. <tek cümle>

NE_TEST_EDILMELI:
1. <test>
2. <test>
3. <test>

Kural:
- Genel tavsiye verme
- Sadece verilen içerikten konuş
- Emin değilsen 'emin değilim' yaz

GIT_BRANCH:
{git_branch}

LAST_COMMIT:
{last_commit}

CHANGED_FUNCTIONS:
{changed_functions}

CHANGED_SNIPPETS:
{changed_snippets}

USER:
{user_input}
""".strip()

    if intent == "test":
        return f"""
Aşağıdaki değişiklikler için sadece test listesi çıkar.
Cevabı Türkçe ver.

Format:
TEST_LISTESI:
1. <test>
2. <test>
3. <test>

ONCELIK:
- yüksek: <neden>
- orta: <neden>
- düşük: <neden>

GIT_BRANCH:
{git_branch}

LAST_COMMIT:
{last_commit}

CHANGED_FUNCTIONS:
{changed_functions}

CHANGED_SNIPPETS:
{changed_snippets}

USER:
{user_input}
""".strip()

    if intent == "summary":
        return f"""
Aşağıdaki değişiklikleri sadece kısa özetle.
Cevabı Türkçe ver.

Format:
OZET:
- <madde>
- <madde>
- <madde>

ETKILENEN_DOSYALAR:
- <dosya>
- <dosya>

SONRAKI_ADIM:
- <madde>
- <madde>

GIT_BRANCH:
{git_branch}

LAST_COMMIT:
{last_commit}

GIT_STATUS:
{git_status}

CHANGED_FUNCTIONS:
{changed_functions}

CHANGED_SNIPPETS:
{changed_snippets}

USER:
{user_input}
""".strip()

    if intent == "action":
        return f"""
SADECE PATCH ÜRET. AÇIKLAMA YAZMA.

Kurallar:
- Sadece gerçek Python kodu üret
- Açıklama, yorum, analiz YASAK
- Eksik format YASAK

Format:

PATCH_TARGET:
<dosya>

CHANGE:
```python
<kod>
```

COMMAND:
<tek satır repo komutu>

VERIFY:
<tek satır doğrulama>

GIT_BRANCH:
{git_branch}

LAST_COMMIT:
{last_commit}

GIT_STATUS:
{git_status}

CHANGED_FUNCTIONS:
{changed_functions}

CHANGED_SNIPPETS:
{changed_snippets}

USER:
{user_input}
""".strip()

    raise RuntimeError(f"unhandled intent: {intent!r}")
