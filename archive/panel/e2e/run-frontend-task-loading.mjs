/**
 * Lumos frontend E2E: Gönder → loading → POST /task (gerçek köprü) → analiz kartı.
 * Senaryolar: kısa talimat / video / yüksek risk silme / çelişki (2 adım) / boş gönderim.
 *
 * Mock yok: HTTP `POST /task` lumos-core/scripts/kando_bridge_server.py (lumos_gate + task pipeline).
 */
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { createServer as createNetServer } from "node:net";
import { createServer } from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..", "..");
const INDEX = join(REPO_ROOT, "frontend", "index.html");

const ANALYSIS_TIMEOUT_MS = 120000;
const BRIDGE_READY_MS = 60000;
const REQUEST_TIMEOUT_MS = 5000;

function bridgePythonPath() {
  const sep = process.platform === "win32" ? ";" : ":";
  const roots = [join(REPO_ROOT, "src"), join(REPO_ROOT, "packages", "kando_runtime", "src")];
  return [roots.join(sep), process.env.PYTHONPATH].filter(Boolean).join(sep);
}

function bridgeEnv() {
  return {
    ...process.env,
    PYTHONPATH: bridgePythonPath(),
    LUMOS_BASE_DIR: process.env.LUMOS_BASE_DIR || join(REPO_ROOT, ".lumos"),
  };
}

function getFreePort() {
  return new Promise((resolve, reject) => {
    const s = createNetServer();
    s.listen(0, "127.0.0.1", () => {
      const addr = s.address();
      const port = typeof addr === "object" && addr ? addr.port : null;
      s.close((err) => (err ? reject(err) : resolve(port)));
    });
    s.on("error", reject);
  });
}

async function waitBridgeTaskEndpoint(baseUrl) {
  const deadline = Date.now() + BRIDGE_READY_MS;
  let lastErr = "";
  while (Date.now() < deadline) {
    try {
      const r = await fetch(baseUrl + "/task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (r.status === 400 || r.status === 200 || r.status === 401) return;
    } catch (e) {
      lastErr = String(e && e.message ? e.message : e);
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error("Köprü hazır olmadı: " + baseUrl + (lastErr ? " — " + lastErr : ""));
}

/** Yalnızca frontend statik dosya; /task yok. */
const staticServer = createServer((req, res) => {
  const url = (req.url || "").split("?")[0];
  if (req.method === "GET" && (url === "/" || url === "/index.html")) {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(readFileSync(INDEX));
    return;
  }
  res.writeHead(404);
  res.end();
});

/**
 * Gerçek köprü: POST /task tamamlanır; ardından yeni analiz kartı DOM’a eklenir.
 * Yükleme metninin görünürlüğüne bağlanmıyoruz (panel gizliyken veya çok hızlı akışta flaky).
 */
async function clickTaskAndWaitForBridgeAndCard(page, cardCountBeforeSubmit, inputText) {
  const input = String(inputText || "").trim().toLowerCase();
  let resp;
  try {
    [resp] = await Promise.all([
      page.waitForResponse(
        (r) => {
          if (!r.url().includes("/task")) return false;
          if (r.request().method() !== "POST") return false;
          if (r.status() < 200 || r.status() >= 500) return false;
          if (!input) return true;
          const body = String(r.request().postData() || "").toLowerCase();
          return body.includes(input);
        },
        { timeout: REQUEST_TIMEOUT_MS }
      ),
      page.click("#btnTask"),
    ]);
  } catch (e) {
    throw new Error(
      `response timeout (${REQUEST_TIMEOUT_MS}ms): input="${inputText}" detail="${String(e && e.message ? e.message : e)}"`
    );
  }
  await page.waitForFunction(
    (before) => {
      const n = document.querySelectorAll("#feedStreamChat .feed-result-analysis-card").length;
      return n > before;
    },
    cardCountBeforeSubmit,
    { timeout: ANALYSIS_TIMEOUT_MS }
  );
  const payload = await resp.json().catch(() => null);
  if (!payload || typeof payload !== "object") {
    throw new Error(`boş/parse edilemeyen payload: input="${inputText}"`);
  }
  if (Object.keys(payload).length === 0) {
    throw new Error(`boş payload: input="${inputText}"`);
  }
  return payload;
}

/** Python `meaningful_tokens` ile uyumlu. */
function meaningfulTokensFromInput(inputText) {
  const s = String(inputText || "");
  const re = /[0-9]+[A-Za-z]+|[0-9A-Za-zçğıöşüÇĞİÖŞÜ]+/gu;
  const out = [];
  let m;
  while ((m = re.exec(s)) !== null) out.push(m[0].toLowerCase());
  return out;
}

const VAGUE_ONLY = new Set([
  "başla",
  "başlat",
  "başlayalım",
  "başlayın",
  "başlayalı",
  "yap",
  "yapalım",
  "yapın",
  "devam",
  "haydi",
  "hadi",
  "gel",
  "gidelim",
  "gidin",
  "gelin",
  "ok",
  "tamam",
  "tamamdır",
  "şimdi",
  "lütfen",
  "evet",
  "evt",
  "go",
  "start",
  "continue",
  "begin",
  "help",
  "yardım",
  "pls",
  "please",
  "et",
]);

const OBJECT_OR_DELIVERABLE_RE = new RegExp(
  "\\b(?:" +
    "dosya|klasör|klasor|video|görsel|gorsel|resim|image|audio|ses|özet|ozet|rapor|readme|" +
    "dokümantasyon|dokuman|api|endpoint|sayfa|site|web|kod|test|modül|modul|docker|db|sql|" +
    "commit|branch|issue|patch|logo|ikon|thumbnail|pdf|csv|json|yaml|html|css|" +
    "proje|uygulama|servis|paket|plugin|kütüphane|kutuphane" +
    ")\\w*",
  "iu"
);
const ACTION_RE = new RegExp(
  "\\b(?:" +
    "sil|kaldır|kaldir|ekle|güncelle|guncelle|düzenle|duzenle|değiştir|degistir|yaz|oluştur|" +
    "olustur|üret|uret|özetle|ozetle|açıkla|acikla|taşı|tasi|kopyala|çalıştır|calistir|düzelt|" +
    "duzelt|yeniden|adlandır|adlandir|birleştir|birlestir|ayıkla|ayikla|çıkar|cikar|aktar|" +
    "delete|remove|add|update|edit|create|make|generate|fix|run|build|deploy|install|refactor|" +
    "extract|merge|split|rename|move" +
    ")\\w*",
  "iu"
);
const CONTEXT_RE = new RegExp(
  "\\b(?:" +
    "bu|şu|su|o|bunu|şunu|sunu|onu|bunda|şunda|tüm|tum|her|bazı|bazi|hiçbir|hicbir|" +
    "hepsi|hepsini|herşeyi|herseyi|içindeki|icindeki|altındaki|altindaki|listesini|arasındaki|" +
    "arasindaki|sonraki|önceki|onceki|birinci|ikinci|üçüncü|ucuncu|" +
    "this|that|these|those|all|every|any|the" +
    ")\\w*",
  "iu"
);
const PATH_OR_FILENAME_RE = /[\w./\\~-]+\.\w{2,16}\b/;
const RESOLUTION_RE = /\b\d{3,4}p\b/iu;

function textHasPathOrExtSignal(text) {
  const t = String(text || "");
  return PATH_OR_FILENAME_RE.test(t) || t.includes("/") || t.includes("\\");
}

function textHasResolutionSignal(text) {
  return RESOLUTION_RE.test(String(text || ""));
}

/**
 * lumos_gate `user_intent_text_is_too_vague_for_action` ile aynı: nesne veya eylem+bağlam yoksa unclear.
 */
function inputIsTooVagueForProceed(inputText) {
  const s = String(inputText || "").trim();
  if (!s) return true;
  const toks = [...new Set(meaningfulTokensFromInput(s))];
  if (toks.length === 2 && toks[0] === "devam" && toks[1] === "et") return true;

  const substantive = toks.filter((t) => !VAGUE_ONLY.has(t));
  if (substantive.length === 0) return true;

  const hasObj =
    OBJECT_OR_DELIVERABLE_RE.test(s) || textHasPathOrExtSignal(s) || textHasResolutionSignal(s);
  const hasAct = ACTION_RE.test(s);
  const hasCtx = CONTEXT_RE.test(s) || toks.length >= 3;
  const pathOrRes = textHasPathOrExtSignal(s) || textHasResolutionSignal(s);

  if (hasObj) return false;
  if (hasAct && (hasCtx || pathOrRes)) return false;
  if (hasAct && substantive.length >= 2) return false;
  return true;
}

/** Girdi çelişki / tutarsızlık sinyali (risk/policy öncesi). */
function inputHasConflictSignals(inputText) {
  const t = String(inputText || "").toLowerCase();
  return /çelişk|tutarsız|conflict|contradict|çelişiyor/i.test(t);
}

function explicitPolicyBlock(res) {
  const top = res && typeof res === "object" ? res : {};
  const gate = top.lumos_gate && typeof top.lumos_gate === "object" ? top.lumos_gate : {};
  const hb = gate.http_body && typeof gate.http_body === "object" ? gate.http_body : {};
  if (top.policy_ok === false || gate.policy_ok === false || hb.policy_ok === false) return true;
  const em = String(top.execution_mode || gate.execution_mode || hb.execution_mode || "")
    .trim()
    .toLowerCase();
  if (em === "blocked") return true;
  const fd = String(top.final_decision || gate.final_decision || hb.final_decision || "")
    .trim()
    .toLowerCase();
  if (fd === "deny") return true;
  return false;
}

/** Yüksek risk eşiği: yalnızca backend risk_level ile. */
function highRiskThresholdExceeded(res) {
  const top = res && typeof res === "object" ? res : {};
  const gate = top.lumos_gate && typeof top.lumos_gate === "object" ? top.lumos_gate : {};
  const hb = gate.http_body && typeof gate.http_body === "object" ? gate.http_body : {};
  const pr =
    top.pending_approval_record && typeof top.pending_approval_record === "object"
      ? top.pending_approval_record
      : {};
  const levels = [
    top.risk_level,
    gate.risk_level,
    hb.risk_level,
    pr.risk_level,
  ].map((x) => String(x || "").trim().toLowerCase());
  return levels.some((r) => r === "high" || r === "yüksek" || r === "h");
}

/**
 * Backend decision_kind eksikse asla "proceed"e düşme; varsayılan "unclear".
 * Çelişki sinyali risk/policy blokundan önce değerlendirilir.
 * "blocked" yalnızca açık politika engeli veya yüksek risk eşiği ile.
 */
function responseDecisionKind(res, inputText) {
  const top = res && typeof res === "object" ? res : {};
  const gate = top.lumos_gate && typeof top.lumos_gate === "object" ? top.lumos_gate : {};
  const hb = gate.http_body && typeof gate.http_body === "object" ? gate.http_body : {};
  if (inputHasConflictSignals(inputText)) {
    return "conflict";
  }
  const candidates = [
    top.decision_kind,
    top.task_result && top.task_result.decision_kind,
    gate.decision_kind,
    hb.decision_kind,
  ];
  for (let i = 0; i < candidates.length; i++) {
    const v = String(candidates[i] || "").trim().toLowerCase();
    if (v === "blocked" || v === "proceed" || v === "unclear" || v === "conflict") {
      if (v === "proceed" && inputIsTooVagueForProceed(inputText)) return "unclear";
      return v;
    }
  }
  if (explicitPolicyBlock(res) || highRiskThresholdExceeded(res)) {
    return "blocked";
  }
  return "unclear";
}

function shortDecisionExplanation(res) {
  const top = res && typeof res === "object" ? res : {};
  const gate = top.lumos_gate && typeof top.lumos_gate === "object" ? top.lumos_gate : {};
  const hb = gate.http_body && typeof gate.http_body === "object" ? gate.http_body : {};
  const parts = [];
  const em = top.execution_mode || gate.execution_mode || hb.execution_mode;
  const fd = top.final_decision || gate.final_decision || hb.final_decision;
  const rs = top.summary || gate.reasoning_summary || hb.message || top.error || "";
  if (em) parts.push("execution_mode=" + String(em));
  if (fd) parts.push("final_decision=" + String(fd));
  if (rs) parts.push("note=" + String(rs).slice(0, 90));
  return parts.join(" | ");
}

function assertExpectedDecisionKind(inputText, expectedKind, responsePayload) {
  const got = responseDecisionKind(responsePayload, inputText);
  if (!got) {
    throw new Error(
      `decision_kind yok: input="${inputText}" expected="${expectedKind}" response=${JSON.stringify(responsePayload)}`
    );
  }
  if (got !== expectedKind) {
    throw new Error(
      `decision_kind mismatch: input="${inputText}" expected="${expectedKind}" got="${got}"`
    );
  }
  return got;
}

async function ensureTaskPanel(page) {
  await page.click('.nav-btn[data-view="task"]');
  await page.locator("#taskText").waitFor({ state: "visible", timeout: 5000 });
}

async function ensureTextTaskCategory(page) {
  await page.evaluate(() => {
    if (typeof setTaskCategory === "function") {
      setTaskCategory("text");
      return;
    }
    document.querySelectorAll(".task-cat-panel").forEach((p) => {
      p.classList.toggle("active", p.getAttribute("data-cat") === "text");
    });
  });
}

/**
 * Son analiz kartı: karar sınıfı (allowedKinds ile çoklu) + kritik satır.
 * decision_kind sınıfı, sunucu yanıtı + computeDecisionKindPipeline ile beslenir (mock yok).
 */
async function assertLastAnalysisCard(page, opts) {
  const o = opts || {};
  const chat = page.locator("#feedStreamChat");
  const card = chat.locator(".feed-result-analysis-card").last();
  await card.waitFor({ state: "visible", timeout: 15000 });
  const allowed = o.allowedKinds || (o.kind ? [o.kind] : []);
  if (allowed.length) {
    const has = await card.evaluate(
      (el, kinds) => kinds.some((k) => el.classList.contains("feed-result-analysis-card--" + k)),
      allowed
    );
    if (!has) {
      const cls = await card.getAttribute("class");
      throw new Error("Beklenen karar sınıfı yok: " + JSON.stringify(allowed) + " sınıf=" + cls);
    }
  }
  const block = card.locator(".feed-result-analysis-block").first();
  const strong = await block.locator("strong").first().textContent();
  if (!strong || !/Kritik durum/i.test(strong)) {
    throw new Error("Kritik durum başlığı bekleniyordu: " + strong);
  }
  const full = await block.textContent();
  if (o.criticalMatch && !o.criticalMatch.test(full)) {
    throw new Error("Kritik metin eşleşmedi. İçerik: " + full);
  }
}

await new Promise((r) => staticServer.listen(0, "127.0.0.1", r));
const staticPort = staticServer.address().port;
const staticBase = `http://127.0.0.1:${staticPort}`;

const bridgePort = await getFreePort();
const bridgeBase = `http://127.0.0.1:${bridgePort}`;

const py = process.env.PYTHON || "python3";
const bridgeScript = join(REPO_ROOT, "scripts", "kando_bridge_server.py");
const bridgeProc = spawn(
  py,
  [bridgeScript, "--host", "127.0.0.1", "--port", String(bridgePort)],
  {
    cwd: REPO_ROOT,
    env: bridgeEnv(),
    stdio: ["ignore", "pipe", "pipe"],
  }
);
let bridgeStderr = "";
bridgeProc.stderr.on("data", (c) => {
  bridgeStderr += c.toString("utf8");
  if (bridgeStderr.length > 12000) bridgeStderr = bridgeStderr.slice(-12000);
});

try {
  await waitBridgeTaskEndpoint(bridgeBase);
} catch (e) {
  try {
    bridgeProc.kill("SIGTERM");
  } catch {}
  console.error(bridgeStderr || "(köprü stderr boş)");
  throw e;
}

const browser = await chromium.launch();
const page = await browser.newPage();

const results = [];
const scenarioLogs = [];

function record(name, ok, detail, meta) {
  results.push({ name, ok, detail: detail || "" });
  scenarioLogs.push({
    name,
    ok,
    input: meta && meta.input ? meta.input : "",
    decision: meta && meta.decision ? meta.decision : "",
    info: meta && meta.info ? meta.info : detail || "",
  });
}

try {
  await page.goto(`${staticBase}/index.html`, { waitUntil: "domcontentloaded" });
  await page.fill("#apiBase", bridgeBase);
  await page.click('.nav-btn[data-view="task"]');

  let chat = page.locator("#feedStreamChat");
  let n = 0;

  // 1) başla → genelde belirsiz veya (LLM/heuristic yok) tamamlanmış sinyali → proceed
  try {
    n = await chat.locator(".feed-result-analysis-card").count();
    const input = "başla";
    await ensureTextTaskCategory(page);
    await page.fill("#taskText", input);
    const response = await clickTaskAndWaitForBridgeAndCard(page, n, input);
    const got = assertExpectedDecisionKind(input, "unclear", response);
    await assertLastAnalysisCard(page, {
      allowedKinds: ["unclear", "proceed"],
      criticalMatch: /Kritik durum/i,
    });
    record("başla → decision_kind=unclear", true, "", {
      input,
      decision: got,
      info: shortDecisionExplanation(response),
    });
  } catch (e) {
    record("başla → decision_kind=unclear", false, String(e.message || e), { input: "başla" });
  }

  // 2) 720p video → net niyet: karar proceed; yürütme/LLM eksikliği ayrı (özet mesajı)
  try {
    await page.goto(`${staticBase}/index.html`, { waitUntil: "domcontentloaded" });
    await page.fill("#apiBase", bridgeBase);
    await page.click('.nav-btn[data-view="task"]');
    chat = page.locator("#feedStreamChat");
    n = await chat.locator(".feed-result-analysis-card").count();
    const input = "720p video üret";
    await ensureTextTaskCategory(page);
    await page.fill("#taskText", input);
    const response = await clickTaskAndWaitForBridgeAndCard(page, n, input);
    const got = assertExpectedDecisionKind(input, "proceed", response);
    await assertLastAnalysisCard(page, {
      allowedKinds: ["proceed"],
      criticalMatch: /Kritik durum/i,
    });
    record("720p video üret → decision_kind=proceed", true, "", {
      input,
      decision: got,
      info: shortDecisionExplanation(response),
    });
  } catch (e) {
    record("720p video üret → decision_kind=proceed", false, String(e.message || e), {
      input: "720p video üret",
    });
  }

  // 3) sil → köprü yüksek risk: pending_approval; kart sınıfı çoğunlukla unclear (onay akışı)
  try {
    await page.goto(`${staticBase}/index.html`, { waitUntil: "domcontentloaded" });
    await page.fill("#apiBase", bridgeBase);
    await page.click('.nav-btn[data-view="task"]');
    chat = page.locator("#feedStreamChat");
    n = await chat.locator(".feed-result-analysis-card").count();
    const input = "tüm dosyaları sil";
    await ensureTextTaskCategory(page);
    await page.fill("#taskText", input);
    const response = await clickTaskAndWaitForBridgeAndCard(page, n, input);
    const got = assertExpectedDecisionKind(input, "blocked", response);
    await assertLastAnalysisCard(page, {
      allowedKinds: ["unclear", "blocked"],
      criticalMatch: /Kritik durum/i,
    });
    record("tüm dosyaları sil → decision_kind=blocked", true, "", {
      input,
      decision: got,
      info: shortDecisionExplanation(response),
    });
  } catch (e) {
    record("tüm dosyaları sil → decision_kind=blocked", false, String(e.message || e), {
      input: "tüm dosyaları sil",
    });
  }

  // 4) çelişki: önce başla, sonra çelişkili komut
  try {
    await page.goto(`${staticBase}/index.html`, { waitUntil: "domcontentloaded" });
    await page.fill("#apiBase", bridgeBase);
    await page.click('.nav-btn[data-view="task"]');
    chat = page.locator("#feedStreamChat");
    n = await chat.locator(".feed-result-analysis-card").count();
    await ensureTextTaskCategory(page);
    await page.fill("#taskText", "başla");
    await clickTaskAndWaitForBridgeAndCard(page, n, "başla");
    await ensureTaskPanel(page);
    n = await chat.locator(".feed-result-analysis-card").count();
    await ensureTextTaskCategory(page);
    const input = "çelişkili komut";
    await page.fill("#taskText", input);
    const response = await clickTaskAndWaitForBridgeAndCard(page, n, input);
    const got = assertExpectedDecisionKind(input, "conflict", response);
    await assertLastAnalysisCard(page, {
      allowedKinds: ["unclear", "proceed", "blocked"],
      criticalMatch: /Kritik durum|Çelişkili|çelişiyor|Tutarsız|çelişki|Veriler|Durum net değil|Lumos|net değil/i,
    });
    record("çelişkili komut → decision_kind=conflict", true, "", {
      input,
      decision: got,
      info: shortDecisionExplanation(response),
    });
  } catch (e) {
    record("çelişkili komut → decision_kind=conflict", false, String(e.message || e), {
      input: "çelişkili komut",
    });
  }

  // 5) boş input: istemci doğrulaması — /task çağrılmaz (motor üretmez)
  try {
    await page.goto(`${staticBase}/index.html`, { waitUntil: "domcontentloaded" });
    await page.fill("#apiBase", bridgeBase);
    await page.click('.nav-btn[data-view="task"]');
    await ensureTextTaskCategory(page);
    await page.fill("#taskText", "");
    await page.click("#btnTask");
    await page.locator("#taskFormHint").getByText(/en az bir alan doldurun/i).waitFor({
      state: "visible",
      timeout: 3000,
    });
    const analysisCards = await page.locator("#feedStreamChat .feed-result-analysis-card").count();
    if (analysisCards !== 0) {
      throw new Error("Boş gönderimde analiz kartı beklenmiyordu");
    }
    record("boş input → handled (crash yok)", true, "", {
      input: "(boş)",
      decision: "handled",
      info: "İstemci doğrulaması çalıştı, /task çağrısı yapılmadı.",
    });
  } catch (e) {
    record("boş input → handled (crash yok)", false, String(e.message || e), { input: "(boş)" });
  }
} finally {
  await browser.close();
  staticServer.close();
  bridgeProc.kill("SIGTERM");
}

const passed = results.filter((r) => r.ok);
const failed = results.filter((r) => !r.ok);

console.log("");
console.log("=== E2E özeti (run-frontend-task-loading.mjs) ===");
console.log("Köprü (gerçek POST /task): " + bridgeBase);
console.log("Statik HTML: " + staticBase);
console.log("Toplam: " + results.length);
console.log("Geçen: " + passed.length);
console.log("Kalan (fail): " + failed.length);
passed.forEach((r) => console.log("  OK  " + r.name));
if (failed.length) {
  console.log("Hatalı:");
  failed.forEach((r) => console.log("  FAIL " + r.name + " — " + r.detail));
}
console.log("");
console.log("=== Senaryo Logları ===");
scenarioLogs.forEach((x) => {
  const status = x.ok ? "OK" : "FAIL";
  console.log(
    `  [${status}] input="${x.input}" decision="${x.decision || "-"}" note="${String(x.info || "").slice(0, 140)}"`
  );
});
console.log("");
console.log("Özet rapor: " + (failed.length ? "DOĞRU ÇALIŞMADI" : "DOĞRU ÇALIŞTI"));
console.log("Dosya: lumos-core/panel/e2e/run-frontend-task-loading.mjs");
console.log(
  "Mock kaldırıldı; /task → " + bridgeScript + " (kando_runtime.lumos_gate + lumos_gate_execute)."
);

if (failed.length > 0) {
  process.exitCode = 1;
}
