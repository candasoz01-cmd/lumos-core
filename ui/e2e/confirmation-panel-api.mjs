/**
 * Faz-2 — confirmation gate E2E via panel_tasks_server REST (API-only).
 * Flow: POST /tasks blocked → POST /lumos-confirm/request → retry with confirmation_id.
 * Regression: confirmation disabled → create succeeds; /lumos-confirm/request → 404.
 */
import {
  buildTasksApiBase,
  createTempLumosBase,
  fetchTasksDoc,
  postJson,
  resolveTasksApiPort,
  startTasksServer,
  stopTasksServer,
  tasksDocHasTitle,
  waitForTasksApi,
} from "./lib/tasks-server.mjs";

const MARK = "conf-api-" + Date.now();
const TITLE = "Onaylı " + MARK;

function fail(step, msg) {
  throw new Error("[confirmation-panel-api-e2e] " + step + ": " + msg);
}

function offsetPort(basePort, delta) {
  return String(Number(basePort) + delta);
}

async function runConfirmationEnabledFlow() {
  const port = resolveTasksApiPort();
  const base = buildTasksApiBase(port);
  const tmpBase = createTempLumosBase("lumos-conf-api-on-");
  const pyProc = startTasksServer(tmpBase, port, { confirmationEnabled: true });

  try {
    await waitForTasksApi(base, 20000);

    const blocked = await postJson(base, "/tasks", { title: TITLE });
    if (blocked.status !== 409) {
      fail("gate/block-status", "expected 409, got " + blocked.status);
    }
    const blockReason = String((blocked.body && blocked.body.reason) || "");
    const blockError = blocked.body && blocked.body.error;
    const blockedByConfirmation =
      blockError === "confirmation_required" ||
      blockReason.includes("confirmation_required") ||
      blockReason.includes("CONFIRMATION_BLOCKED");
    if (!blockedByConfirmation) {
      fail(
        "gate/block-error",
        "expected confirmation gate block; error=" +
          JSON.stringify(blockError) +
          " reason=" +
          JSON.stringify(blockReason),
      );
    }

    const docAfterBlock = await fetchTasksDoc(base);
    if (tasksDocHasTitle(docAfterBlock, TITLE)) {
      fail("gate/no-persist", "task must not persist before confirmation grant");
    }

    const confirmReq = await postJson(base, "/lumos-confirm/request", {
      mutation_path: "/tasks",
      mutation_body: { title: TITLE },
    });
    if (confirmReq.status !== 200) {
      fail("confirm-request/status", "expected 200, got " + confirmReq.status);
    }
    const confirmationId = confirmReq.body && confirmReq.body.confirmation_id;
    if (!confirmationId) {
      fail("confirm-request/id", "missing confirmation_id");
    }
    if (!confirmReq.body.preview || confirmReq.body.preview.what !== "create_task") {
      fail("confirm-request/preview", "unexpected preview: " + JSON.stringify(confirmReq.body && confirmReq.body.preview));
    }
    if (confirmReq.body.preview.where !== TITLE) {
      fail("confirm-request/where", "preview.where mismatch");
    }

    const created = await postJson(base, "/tasks", {
      title: TITLE,
      confirmation_id: confirmationId,
    });
    if (created.status !== 200) {
      fail("create-grant/status", "expected 200, got " + created.status + "; body=" + JSON.stringify(created.body));
    }
    if (!created.body || !created.body.task || created.body.task.title !== TITLE) {
      fail("create-grant/task", "task payload missing or title mismatch");
    }

    const docAfterCreate = await fetchTasksDoc(base);
    if (!tasksDocHasTitle(docAfterCreate, TITLE)) {
      fail("create-grant/persist", "task not found in tasks.json");
    }
  } finally {
    stopTasksServer(pyProc);
  }
}

async function runConfirmationDisabledRegression() {
  const port = offsetPort(resolveTasksApiPort(), 1);
  const base = buildTasksApiBase(port);
  const tmpBase = createTempLumosBase("lumos-conf-api-off-");
  const pyProc = startTasksServer(tmpBase, port, { confirmationEnabled: false });

  try {
    await waitForTasksApi(base, 20000);

    const disabledTitle = "Kapalı " + MARK;
    const created = await postJson(base, "/tasks", { title: disabledTitle });
    if (created.status !== 200) {
      fail("disabled/create-status", "expected 200, got " + created.status);
    }
    if (!created.body || !created.body.task) {
      fail("disabled/create-body", "task missing in response");
    }

    const doc = await fetchTasksDoc(base);
    if (!tasksDocHasTitle(doc, disabledTitle)) {
      fail("disabled/persist", "task not persisted when confirmation disabled");
    }

    const confirmReq = await postJson(base, "/lumos-confirm/request", {
      mutation_path: "/tasks",
      mutation_body: { title: "Should not matter" },
    });
    if (confirmReq.status !== 404) {
      fail("disabled/confirm-endpoint", "expected 404, got " + confirmReq.status);
    }
    if (!confirmReq.body || confirmReq.body.error !== "confirmation_disabled") {
      fail("disabled/confirm-error", "expected confirmation_disabled");
    }
  } finally {
    stopTasksServer(pyProc);
  }
}

let exitCode = 0;

runConfirmationEnabledFlow()
  .then(function () {
    return runConfirmationDisabledRegression();
  })
  .then(function () {
    console.log("CONFIRMATION_PANEL_API_E2E_RESULT: PASS");
    console.log("surface: panel_tasks_server REST");
    console.log("mark:", MARK);
  })
  .catch(function (err) {
    console.error("CONFIRMATION_PANEL_API_E2E_RESULT: FAIL");
    console.error(String(err && err.message ? err.message : err));
    exitCode = 1;
  })
  .then(function () {
    process.exit(exitCode);
  });
