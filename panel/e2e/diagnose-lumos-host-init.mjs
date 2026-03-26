/**
 * Gerçek tarayıcı: lumos-host-init.js ağ durumu, console, window.LUMOS_PANEL_KEYSTORE_UNLOCK
 * Çalıştır: node panel/e2e/diagnose-lumos-host-init.mjs
 */
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import http from "node:http";
import { chromium } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PANEL_DIR = resolve(join(__dirname, ".."));
const REPO_ROOT = resolve(join(PANEL_DIR, ".."));
const PY_SCRIPT = join(REPO_ROOT, "panel/scripts/panel_tasks_server.py");

const PORT = String(22000 + (process.pid % 1000));
const BASE = `http://127.0.0.1:${PORT}`;
const TMP = mkdtempSync(join(tmpdir(), "lumos-diag-"));

function waitFor200(url, ms) {
  const deadline = Date.now() + ms;
  return new Promise((resolveFn, rejectFn) => {
    function once() {
      http
        .get(url, (res) => {
          res.resume();
          if (res.statusCode === 200) return resolveFn();
          if (Date.now() > deadline) return rejectFn(new Error(String(res.statusCode)));
          setTimeout(once, 50);
        })
        .on("error", () => {
          if (Date.now() > deadline) return rejectFn(new Error("timeout"));
          setTimeout(once, 50);
        });
    }
    once();
  });
}

async function run() {
  const py = spawn("python3", [PY_SCRIPT], {
    env: Object.assign({}, process.env, {
      LUMOS_BASE_DIR: TMP,
      LUMOS_PANEL_TASKS_PORT: PORT,
      LUMOS_PANEL_TASKS_HOST: "127.0.0.1",
    }),
    stdio: "pipe",
  });

  const report = {
    server: `panel_tasks_server ${BASE}`,
    scriptRequest: null,
    scriptStatus: null,
    consoleLogs: [],
    pageErrors: [],
    manualUnlockCallOk: null,
    typeofLUMOS_PANEL_KEYSTORE_UNLOCK: null,
    rootCause: "",
  };

  try {
    await waitFor200(BASE + "/index.html", 15000);
  } catch (e) {
    report.rootCause = "Sunucu ayakta değil veya index 200 değil: " + String(e.message || e);
    try {
      py.kill("SIGTERM");
    } catch (_) {}
    console.log(JSON.stringify(report, null, 2));
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  page.on("console", (msg) => {
    const t = msg.text();
    report.consoleLogs.push({ type: msg.type(), text: t });
  });

  page.on("pageerror", (err) => {
    report.pageErrors.push(String(err && err.message ? err.message : err));
  });

  page.on("response", (res) => {
    const u = res.url();
    if (u.indexOf("lumos-host-init.js") !== -1) {
      report.scriptRequest = u;
      report.scriptStatus = res.status();
    }
  });

  await page.goto(BASE + "/index.html", { waitUntil: "load", timeout: 30000 });

  report.typeofLUMOS_PANEL_KEYSTORE_UNLOCK = await page.evaluate(() => {
    return typeof window.LUMOS_PANEL_KEYSTORE_UNLOCK;
  });

  try {
    await page.evaluate(async () => {
      if (typeof window.LUMOS_PANEL_KEYSTORE_UNLOCK !== "function") {
        throw new Error("no_unlock_fn");
      }
      var r = await window.LUMOS_PANEL_KEYSTORE_UNLOCK("1770");
      if (!r || r.ok !== true) {
        throw new Error("expected_ok_true");
      }
    });
    report.manualUnlockCallOk = true;
  } catch (e) {
    report.manualUnlockCallOk = false;
    report.pageErrors.push(String(e && e.message ? e.message : e));
  }

  await browser.close();
  try {
    py.kill("SIGTERM");
  } catch (_) {}

  if (report.scriptStatus !== 200) {
    report.rootCause =
      "lumos-host-init.js isteği 200 değil veya hiç yakalanmadı (404/path/network).";
  } else if (report.typeofLUMOS_PANEL_KEYSTORE_UNLOCK !== "function") {
    report.rootCause = "lumos-host-init yüklendi ama window.LUMOS_PANEL_KEYSTORE_UNLOCK fonksiyon değil.";
  } else if (!report.manualUnlockCallOk) {
    report.rootCause = "Fonksiyon var ama LUMOS_PANEL_KEYSTORE_UNLOCK(\"1770\") beklenen sonucu vermedi.";
  } else {
    report.rootCause =
      "Tamam: window tanımlı; LUMOS_PANEL_KEYSTORE_UNLOCK(\"1770\") → { ok: true }.";
  }

  console.log(JSON.stringify(report, null, 2));
}

run().catch((e) => {
  console.error(JSON.stringify({ error: String(e) }, null, 2));
  process.exit(1);
});
