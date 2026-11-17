import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

import {
  consume,
  DEFAULT_LIMITS,
  ensureSchema,
  readLimits,
  ROWS_WRITTEN_PER_ALLOWED_REQUEST,
  windows,
} from "../ops/usage-guard/limits.mjs";

// Durable Object `ctx.storage.sql` arayüzünün gerçek SQLite ile birebir taklidi;
// yazılan satır sayısı Cloudflare'in "rows written" ölçüsüne karşılık gelir.
function sqliteShim() {
  const db = new DatabaseSync(":memory:");
  const shim = {
    rowsWritten: 0,
    exec(query, ...bindings) {
      const stmt = db.prepare(query);
      if (/^\s*SELECT/i.test(query)) {
        const rows = stmt.all(...bindings);
        return { toArray: () => rows };
      }
      const info = stmt.run(...bindings);
      shim.rowsWritten += Number(info.changes || 0);
      return { toArray: () => [] };
    },
  };
  return shim;
}

const T0 = Date.parse("2026-11-17T10:00:05Z");

function fresh() {
  const sql = sqliteShim();
  ensureSchema(sql);
  sql.rowsWritten = 0;
  return sql;
}

test("defaults are the founder-approved starting limits", () => {
  assert.deepEqual({ ...DEFAULT_LIMITS }, { userPerMinute: 10, userPerDay: 100, globalPerDay: 2000 });
  assert.deepEqual(readLimits({}), { userPerMinute: 10, userPerDay: 100, globalPerDay: 2000 });
  assert.deepEqual(
    readLimits({ LUMOS_USAGE_USER_PER_MINUTE: "3", LUMOS_USAGE_USER_PER_DAY: "0", LUMOS_USAGE_GLOBAL_PER_DAY: "abc" }),
    { userPerMinute: 3, userPerDay: 100, globalPerDay: 2000 },
  );
});

test("windows are UTC minute and UTC day", () => {
  assert.deepEqual(windows(T0), { minute: "2026-11-17T10:00", day: "2026-11-17" });
});

test("11th request in the same minute is denied by the per-user minute limit", () => {
  const sql = fresh();
  for (let i = 0; i < 10; i += 1) assert.equal(consume(sql, "lumos_a", DEFAULT_LIMITS, T0 + i).allowed, true);
  const denied = consume(sql, "lumos_a", DEFAULT_LIMITS, T0 + 20);
  assert.deepEqual(denied, { allowed: false, scope: "user_minute" });
  assert.equal(consume(sql, "lumos_a", DEFAULT_LIMITS, T0 + 60_000).allowed, true, "next minute opens again");
});

test("per-user daily limit holds across minutes and resets at 00:00 UTC", () => {
  const sql = fresh();
  const limits = { userPerMinute: 1000, userPerDay: 5, globalPerDay: 1000 };
  for (let i = 0; i < 5; i += 1) assert.equal(consume(sql, "lumos_a", limits, T0 + i * 60_000).allowed, true);
  assert.deepEqual(consume(sql, "lumos_a", limits, T0 + 3_600_000), { allowed: false, scope: "user_day" });
  assert.equal(consume(sql, "lumos_b", limits, T0 + 3_600_000).allowed, true, "other users unaffected");
  const nextDay = Date.parse("2026-11-18T00:00:01Z");
  assert.equal(consume(sql, "lumos_a", limits, nextDay).allowed, true);
});

test("global daily limit stops every user", () => {
  const sql = fresh();
  const limits = { userPerMinute: 1000, userPerDay: 1000, globalPerDay: 3 };
  assert.equal(consume(sql, "lumos_a", limits, T0).allowed, true);
  assert.equal(consume(sql, "lumos_b", limits, T0).allowed, true);
  assert.equal(consume(sql, "lumos_c", limits, T0).allowed, true);
  assert.deepEqual(consume(sql, "lumos_d", limits, T0), { allowed: false, scope: "global_day" });
});

test("allowed request writes exactly 3 rows; denied request writes none; table does not grow", () => {
  const sql = fresh();
  const limits = { userPerMinute: 2, userPerDay: 100, globalPerDay: 100 };
  consume(sql, "lumos_a", limits, T0);
  assert.equal(sql.rowsWritten, ROWS_WRITTEN_PER_ALLOWED_REQUEST);
  consume(sql, "lumos_a", limits, T0 + 1);
  consume(sql, "lumos_a", limits, T0 + 2); // denied
  assert.equal(sql.rowsWritten, 2 * ROWS_WRITTEN_PER_ALLOWED_REQUEST);
  for (let m = 1; m <= 50; m += 1) consume(sql, "lumos_a", { ...limits, userPerDay: 1000 }, T0 + m * 60_000);
  const rows = sql.exec("SELECT key FROM counters").toArray();
  assert.equal(rows.length, 3, "one row per counter, overwritten per window");
});

test("free-plan budget: the default global cap uses a small share of daily DO quota", () => {
  const FREE_DO_ROWS_WRITTEN_PER_DAY = 100_000;
  const FREE_DO_REQUESTS_PER_DAY = 100_000;
  const rows = DEFAULT_LIMITS.globalPerDay * ROWS_WRITTEN_PER_ALLOWED_REQUEST;
  assert.equal(rows, 6000);
  assert.ok(rows / FREE_DO_ROWS_WRITTEN_PER_DAY <= 0.06);
  assert.ok(DEFAULT_LIMITS.globalPerDay < FREE_DO_REQUESTS_PER_DAY);
});
