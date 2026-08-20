/**
 * dashboard-health-v1 saf katman testleri.
 * Sözleşme: docs/contracts/dashboard-health-v1.md — §9 kabul kriterleri.
 *
 * Tarayıcı gerektirmez; saf türetme mantığını doğrular.
 */
import {
  STATES,
  STATE_LIST,
  STATE_PRESENTATION,
  CARD_TTL_SECONDS,
  deriveBridgeLlm,
  applyFreshness,
  notCheckedCard,
  freshnessMinutes,
  isMeasuredState,
} from "../src/lib/dashboard-health.mjs";

let failures = 0;
let checks = 0;

function ok(cond, label) {
  checks += 1;
  if (!cond) {
    failures += 1;
    console.error(`  ✗ ${label}`);
  }
}

function eq(actual, expected, label) {
  ok(actual === expected, `${label} — beklenen ${JSON.stringify(expected)}, gelen ${JSON.stringify(actual)}`);
}

function throws(fn, label) {
  checks += 1;
  try {
    fn();
    failures += 1;
    console.error(`  ✗ ${label} — hata bekleniyordu, atılmadı`);
  } catch {
    /* beklenen */
  }
}

const T0 = Date.parse("2026-08-20T10:00:00Z");
const AT = "2026-08-20T10:00:00Z";

// ── §9.1 — state daima beş literalden biri ────────────────────────────────
console.log("§9.1 kapalı sözlük");
eq(STATE_LIST.length, 5, "sözlük tam beş literal");
for (const probe of [
  { kind: "response", status: 200, body: { status: "ok" }, checkedAt: AT },
  { kind: "response", status: 503, body: { status: "unconfigured" }, checkedAt: AT },
  { kind: "response", status: 401, body: {}, checkedAt: AT },
  { kind: "response", status: 500, body: {}, checkedAt: AT },
  { kind: "response", status: 418, body: { status: "teapot" }, checkedAt: AT },
  { kind: "network", detail: "timeout", checkedAt: null },
]) {
  const card = deriveBridgeLlm(probe);
  ok(STATE_LIST.includes(card.state), `state sözlükte: ${JSON.stringify(probe)}`);
}
eq(deriveBridgeLlm({ kind: "response", status: 418, body: { status: "teapot" }, checkedAt: AT }).reason_code,
  "unmapped_value", "sözlük dışı değer → unmapped_value");

// ── §4 türetme tablosu ─────────────────────────────────────────────────────
console.log("§4 backend → durum türetme");
eq(deriveBridgeLlm({ kind: "response", status: 200, body: { status: "ok" }, checkedAt: AT }).state,
  STATES.HEALTHY, "200 ok → healthy");
eq(deriveBridgeLlm({ kind: "response", status: 503, body: { status: "unconfigured" }, checkedAt: AT }).state,
  STATES.NOT_CONFIGURED, "503 unconfigured → not_configured");
eq(deriveBridgeLlm({ kind: "network", detail: "timeout" }).state,
  STATES.UNKNOWN, "ağ hatası → unknown");
eq(deriveBridgeLlm({ kind: "network", detail: "timeout" }).reason_code,
  "probe_unreachable", "ağ hatası → probe_unreachable");
eq(notCheckedCard("bridge.llm").state, STATES.UNKNOWN, "hiç çağrılmadı → unknown");
eq(notCheckedCard("bridge.llm").checked_at, null, "hiç çağrılmadı → checked_at null");
eq(notCheckedCard("bridge.llm").reason_code, "not_checked", "hiç çağrılmadı → not_checked");

// 200 ama gövde 'ok' değil → healthy DEĞİL
eq(deriveBridgeLlm({ kind: "response", status: 200, body: { status: "maybe" }, checkedAt: AT }).state,
  STATES.UNKNOWN, "200 + beklenmeyen gövde → healthy değil, unknown");

// ── §9.6 / §6 — 401 tüm kartları unknown yapar, failed YAPMAZ ──────────────
console.log("§6 401 → unknown, failed değil");
const un = deriveBridgeLlm({ kind: "response", status: 401, body: {}, checkedAt: AT });
eq(un.state, STATES.UNKNOWN, "401 → unknown");
ok(un.state !== STATES.FAILED, "401 asla failed üretmez");
eq(un.reason_code, "unauthorized", "401 → unauthorized");
eq(un.checked_at, null, "401 → ölçüm sayılmaz, checked_at null");

// ── §9.10 / invariant 1 — ölçülmeyen asla healthy ─────────────────────────
console.log("invariant 1: ölçülmeyen şey yeşil olamaz");
for (const probe of [
  { kind: "network", detail: "dns" },
  { kind: "response", status: 401, body: {}, checkedAt: AT },
  { kind: "response", status: 418, body: { status: "?" }, checkedAt: AT },
  { kind: "response", status: 503, body: { status: "unconfigured" }, checkedAt: AT },
  undefined,
]) {
  ok(deriveBridgeLlm(probe).state !== STATES.HEALTHY, `healthy üretmemeli: ${JSON.stringify(probe)}`);
}
ok(!isMeasuredState(STATES.UNKNOWN), "unknown ölçülmüş sayılmaz");
ok(!isMeasuredState(STATES.NOT_CONFIGURED), "not_configured ölçülmüş sayılmaz");

// ── §3.2 — checked_at=null disiplini ───────────────────────────────────────
console.log("§3.2 checked_at=null disiplini");
throws(
  () => deriveBridgeLlm({ kind: "response", status: 200, body: { status: "ok" }, checkedAt: null }),
  "healthy checked_at olmadan üretilemez",
);
for (const probe of [
  { kind: "network", detail: "x" },
  { kind: "response", status: 401, body: {}, checkedAt: AT },
]) {
  const c = deriveBridgeLlm(probe);
  ok(c.checked_at === null && (c.state === STATES.UNKNOWN || c.state === STATES.NOT_CONFIGURED),
    "null checked_at yalnız unknown/not_configured ile birleşir");
}

// ── §3.1 / §9.7 — freshness ────────────────────────────────────────────────
console.log("§3.1 freshness → stale, last_known korunur");
const ttl = CARD_TTL_SECONDS["bridge.llm"];
const healthy = deriveBridgeLlm({ kind: "response", status: 200, body: { status: "ok" }, checkedAt: AT });
eq(healthy.ttl_seconds, ttl, "kart TTL'i tek kaynaktan gelir");

eq(applyFreshness(healthy, T0 + (ttl - 1) * 1000).state, STATES.HEALTHY, "bütçe içinde healthy kalır");
eq(applyFreshness(healthy, T0 + ttl * 1000).state, STATES.HEALTHY, "tam sınırda henüz stale değil");
const staled = applyFreshness(healthy, T0 + (ttl + 1) * 1000);
eq(staled.state, STATES.STALE, "bütçe aşımı → stale");
eq(staled.last_known, STATES.HEALTHY, "stale son bilinen sonucu korur");
eq(staled.reason_code, "freshness_expired", "stale → freshness_expired");
eq(staled.checked_at, AT, "stale checked_at'i uydurmaz, geçmişi taşır");

const failedCard = deriveBridgeLlm({ kind: "response", status: 500, body: {}, checkedAt: AT });
eq(failedCard.state, STATES.FAILED, "500 (servis kendi hatası) → failed");

// ── §4 `failed` dar tanımı — yalnız kanıtlanmış arıza ─────────────────────
console.log("§4 failed dar tanımı: erişim belirsizliği arıza değildir");
for (const [st, label] of [[502, "502 gateway"], [504, "504 upstream timeout"]]) {
  const c = deriveBridgeLlm({ kind: "response", status: st, body: {}, checkedAt: AT });
  eq(c.state, STATES.UNKNOWN, `${label} → unknown (failed DEĞİL)`);
  eq(c.reason_code, "probe_inconclusive", `${label} → probe_inconclusive`);
  eq(c.checked_at, null, `${label} → ölçüm sayılmaz`);
}
const bare503 = deriveBridgeLlm({ kind: "response", status: 503, body: {}, checkedAt: AT });
eq(bare503.state, STATES.UNKNOWN, "gövdesiz 503 → unknown (not_configured da DEĞİL)");
eq(bare503.reason_code, "probe_inconclusive", "gövdesiz 503 → probe_inconclusive");
eq(deriveBridgeLlm({ kind: "response", status: 503, body: { status: "unconfigured" }, checkedAt: AT }).state,
  STATES.NOT_CONFIGURED, "gövdeli 503 hâlâ not_configured");
for (const st of [401, 502, 503, 504]) {
  ok(deriveBridgeLlm({ kind: "response", status: st, body: {}, checkedAt: AT }).state !== STATES.FAILED,
    `${st} asla failed suçlaması üretmez`);
}
ok(deriveBridgeLlm({ kind: "network", detail: "dns" }).state !== STATES.FAILED,
  "ağ hatası asla failed üretmez");
eq(applyFreshness(failedCard, T0 + (ttl + 1) * 1000).last_known, STATES.FAILED,
  "stale, son bilinen failed'i de korur");

// unknown/not_configured freshness'tan etkilenmez
eq(applyFreshness(notCheckedCard("bridge.llm"), T0 + 9e6).state, STATES.UNKNOWN,
  "ölçülmemiş kart stale'e düşmez");

// ── §3.4 / §9.2 — null freshness göreli zamana çevrilmez ──────────────────
console.log("§3.4 null freshness göreli zamana çevrilmez");
eq(freshnessMinutes(notCheckedCard("bridge.llm"), T0), null, "checked_at=null → null döner");
eq(freshnessMinutes(deriveBridgeLlm({ kind: "network", detail: "x" }), T0), null,
  "ağ hatası kartı → null döner");
eq(freshnessMinutes(healthy, T0 + 65000), 1, "gerçek ölçüm → dakika hesaplanır");

// ── §9.3 / §8.2-3 — görsel çakışma yok ────────────────────────────────────
console.log("§9.3 durumlar görsel olarak ezilmez");
const glyphs = STATE_LIST.map((s) => STATE_PRESENTATION[s].glyph);
eq(new Set(glyphs).size, STATE_LIST.length, "her durumun kendi glifi var");
const a11y = STATE_LIST.map((s) => STATE_PRESENTATION[s].a11yKey);
eq(new Set(a11y).size, STATE_LIST.length, "her durumun kendi erişilebilir etiketi var");
const tones = STATE_LIST.map((s) => STATE_PRESENTATION[s].tone);
eq(new Set(tones).size, STATE_LIST.length, "her durumun kendi renk rolü var");
ok(STATE_PRESENTATION[STATES.NOT_CONFIGURED].glyph !== STATE_PRESENTATION[STATES.UNKNOWN].glyph,
  "en olası ihlal: not_configured ile unknown aynı glifi paylaşamaz");

// ── §9.4 — aynı state → aynı sunum ────────────────────────────────────────
console.log("§9.4 aynı state → aynı sunum");
const a = deriveBridgeLlm({ kind: "response", status: 503, body: { status: "unconfigured" }, checkedAt: AT });
const b = deriveBridgeLlm({ kind: "response", status: 503, body: { status: "unconfigured" }, checkedAt: "2026-08-20T11:00:00Z" });
eq(STATE_PRESENTATION[a.state].labelKey, STATE_PRESENTATION[b.state].labelKey,
  "aynı state farklı ölçümde aynı metin şablonunu üretir");

// ── §2 — last_known yalnız stale'de ───────────────────────────────────────
console.log("§2 last_known disiplini");
eq(healthy.last_known, null, "healthy kartta last_known null");
eq(a.last_known, null, "not_configured kartta last_known null");

console.log("");
if (failures > 0) {
  console.error(`HEALTH_CONTRACT_RESULT: FAIL (${failures}/${checks} kontrol başarısız)`);
  process.exit(1);
}
console.log(`HEALTH_CONTRACT_RESULT: PASS (${checks} kontrol)`);
