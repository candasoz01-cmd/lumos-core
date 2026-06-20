/**
 * OD-046 Faz 1 — shared Playwright helpers for ui/dist panel E2E.
 */
import { DEFAULT_READY_MS } from "./static-server.mjs";

export const PANEL_READY_MS = DEFAULT_READY_MS;
export const CHAT_INPUT_SELECTOR = "#panel-msg";
export const CHAT_SEND_SELECTOR = "#panel-send";
export const CHAT_THREAD_SELECTOR = "#chat-thread";
export const CONN_BADGE_SELECTOR = "#panel-conn-badge";
export const PANEL_USER_MODE_LS_KEY = "lumos_panel_user_mode_v1";

export async function waitForSelectorAttached(page, selector, timeout = PANEL_READY_MS) {
  await page.waitForSelector(selector, { state: "attached", timeout });
}

export async function waitForPanelDom(page, timeout = PANEL_READY_MS) {
  await waitForSelectorAttached(page, CHAT_THREAD_SELECTOR, timeout);
  await waitForSelectorAttached(page, CONN_BADGE_SELECTOR, timeout);
}

export async function clickModule(page, moduleId, timeout = PANEL_READY_MS) {
  const selector = `.panel-body button[data-module="${moduleId}"]`;
  await waitForSelectorAttached(page, selector, timeout);
  await page.click(selector);
}

/**
 * Legacy panel state_inject + Astro ui panel user-mode patch for task E2E policy gates.
 */
export async function patchPolicyAllowTasks(page) {
  await page.evaluate(function (lsKey) {
    var rs = window.__LUMOS_READ_STATE__;
    if (rs && typeof rs === "object") {
      if (!rs.guidance) rs.guidance = {};
      rs.guidance.mode = "online";
      rs.guidance.lock = "UNLOCKED";
      rs.guidance.consent = true;
      if (rs.keystore && typeof rs.keystore === "object") {
        rs.keystore.keystore_state = "Açık";
        rs.keystore.keystore_ready = true;
      }
      if (rs.dashboard && typeof rs.dashboard === "object") {
        rs.dashboard.guard_status = "Açık";
      }
    }
    try {
      localStorage.setItem(lsKey, "full");
    } catch (_) {}
  }, PANEL_USER_MODE_LS_KEY);

  const fullMode = page.locator('input[name="panel-user-mode"][value="full"]');
  if ((await fullMode.count()) > 0) {
    await fullMode.check();
  }
}

export async function sendChatMessage(page, text, options = {}) {
  const timeout = options.timeout || PANEL_READY_MS;
  const submit = options.submit !== false;
  await waitForSelectorAttached(page, CHAT_INPUT_SELECTOR, timeout);
  await page.fill(CHAT_INPUT_SELECTOR, text);
  if (!submit) return;
  await waitForSelectorAttached(page, CHAT_SEND_SELECTOR, timeout);
  await page.click(CHAT_SEND_SELECTOR);
}
