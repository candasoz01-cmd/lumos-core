/**
 * Dashboard health sözleşmesi v1 — saf türetme katmanı.
 *
 * Sözleşme: docs/contracts/dashboard-health-v1.md
 * Kaynak gerçeği kuralı: sözleşme ile kod ayrışırsa kod esastır; ayrışma borç sayılır.
 *
 * Bu modülde DOM, fetch ve zaman kaynağı YOKTUR. `now` her zaman dışarıdan
 * verilir — böylece freshness davranışı sahte timestamp üretmeden test edilir
 * (§3.3: "Sayfa yüklenme anı, render anı, cache yazma anı, now() varsayılanı —
 * hiçbiri checked_at değildir").
 */

/** §1 — kapalı durum sözlüğü. */
export const STATES = Object.freeze({
  NOT_CONFIGURED: "not_configured",
  UNKNOWN: "unknown",
  HEALTHY: "healthy",
  FAILED: "failed",
  STALE: "stale",
});

export const STATE_LIST = Object.freeze(Object.values(STATES));

/**
 * §3 — provisional TTL değerleri. TEK KAYNAK; kart tarafında sabit yazılmaz.
 * Bunlar ölçülmüş SLO değildir. TTL değişikliği sözleşme değişikliği değildir;
 * `stale` semantiğinin değişmesi sözleşme değişikliğidir.
 */
export const TTL_SECONDS = Object.freeze({
  session: 60,
  bridge: 120,
  integration: 300,
});

/** Kart kimliği → freshness bütçesi. */
export const CARD_TTL_SECONDS = Object.freeze({
  "bridge.llm": TTL_SECONDS.bridge,
});

/** §8 invariant 1 — ölçülmemiş hiçbir yol `healthy` üretemez. */
const MEASURED_STATES = Object.freeze([STATES.HEALTHY, STATES.FAILED, STATES.STALE]);

export function isMeasuredState(state) {
  return MEASURED_STATES.includes(state);
}

function ttlFor(id) {
  const ttl = CARD_TTL_SECONDS[id];
  if (!Number.isFinite(ttl) || ttl <= 0) {
    throw new Error(`dashboard-health: '${id}' için TTL tanımlı değil (§3.5: TTL tek kaynaktan gelir)`);
  }
  return ttl;
}

/**
 * Kart yükü üreticisi (§2). Tek çıkış noktası — böylece invariantlar tek yerde
 * zorlanır ve hiçbir çağıran elle `healthy` kartı kuramaz.
 */
function makeCard(id, state, { checkedAt = null, lastKnown = null, reasonCode = null, evidence }) {
  if (!STATE_LIST.includes(state)) {
    throw new Error(`dashboard-health: sözlük dışı state '${state}'`);
  }
  // §3.2 — ölçülmüş durumlar asla null checked_at ile görünmez.
  if (isMeasuredState(state) && !checkedAt) {
    throw new Error(`dashboard-health: '${state}' checked_at olmadan üretilemez (§3.2)`);
  }
  // §3.2 — checked_at=null yalnız not_configured/unknown ile birleşir.
  if (!checkedAt && !(state === STATES.UNKNOWN || state === STATES.NOT_CONFIGURED)) {
    throw new Error(`dashboard-health: checked_at=null yalnız unknown/not_configured ile birleşir (§3.2)`);
  }
  // §2 — last_known yalnız stale iken anlamlı.
  if (state !== STATES.STALE && lastKnown !== null) {
    throw new Error(`dashboard-health: last_known yalnız state=stale iken taşınır (§2)`);
  }
  return Object.freeze({
    id,
    state,
    checked_at: checkedAt,
    ttl_seconds: ttlFor(id),
    last_known: lastKnown,
    reason_code: reasonCode,
    evidence,
  });
}

/**
 * §4 — "hiç çağrılmadı" satırı. Sunucudan gelen ilk hal budur; ölçüm yapılmadan
 * hiçbir kart yeşil başlayamaz.
 */
export function notCheckedCard(id) {
  return makeCard(id, STATES.UNKNOWN, {
    checkedAt: null,
    reasonCode: "not_checked",
    evidence: "probe çalıştırılmadı",
  });
}

/**
 * §4 — `api/bridge/health.js` gözlemi → kart durumu.
 *
 * @param {object} probe
 * @param {"response"|"network"} probe.kind
 * @param {number} [probe.status]      HTTP durum kodu (kind="response")
 * @param {object} [probe.body]        Ayrıştırılmış JSON gövde
 * @param {string} [probe.detail]      Ağ hatası açıklaması (kind="network")
 * @param {string|null} probe.checkedAt ISO 8601 — probe'un TAMAMLANDIĞI an.
 *                                      Çağıran uydurmaz; gerçek bitiş anıdır.
 */
export function deriveBridgeLlm(probe) {
  const id = "bridge.llm";

  if (!probe || typeof probe !== "object") {
    return notCheckedCard(id);
  }

  // Ağ hatası / zaman aşımı → unknown (bilgi yokluğu, olumsuz sonuç değil).
  if (probe.kind === "network") {
    return makeCard(id, STATES.UNKNOWN, {
      checkedAt: null,
      reasonCode: "probe_unreachable",
      evidence: `GET /api/bridge/health → ağ hatası: ${probe.detail || "bilinmiyor"}`,
    });
  }

  const status = Number(probe.status);
  const body = probe.body && typeof probe.body === "object" ? probe.body : {};
  const checkedAt = probe.checkedAt || null;
  const seen = `GET /api/bridge/health → ${Number.isFinite(status) ? status : "?"}`;

  // §6 — 401 kart durumu DEĞİLDİR. Oturum yoksa Lumos bakamamıştır:
  // kart `unknown` olur, `failed` OLMAZ. Başlık kendi kaynağından beslenir.
  if (status === 401) {
    return makeCard(id, STATES.UNKNOWN, {
      checkedAt: null,
      reasonCode: "unauthorized",
      evidence: `${seen} (oturum yok — §6: kart durumu değil)`,
    });
  }

  if (status === 200 && body.status === "ok") {
    return makeCard(id, STATES.HEALTHY, {
      checkedAt,
      evidence: `${seen} {status:"ok"}`,
    });
  }

  if (status === 503 && body.status === "unconfigured") {
    return makeCard(id, STATES.NOT_CONFIGURED, {
      checkedAt,
      reasonCode: "unconfigured",
      evidence: `${seen} {status:"unconfigured"}`,
    });
  }

  // §4 `failed` DAR TANIMI — yalnız kanıtlanmış arıza:
  // (1) uca gerçekten ulaşıldı, (2) yapılandırma mevcut, (3) servis başarısız.
  // 502/504 cevabı ARACI üretir, gövdesiz 503'ün kaynağı belirsizdir (edge/CDN
  // olabilir) — ikisinde de servisin kendisi gözlenmemiştir. Erişim belirsizliği
  // arıza suçlaması değildir; bunlar `unknown` kalır.
  if (status === 502 || status === 504 || status === 503) {
    return makeCard(id, STATES.UNKNOWN, {
      checkedAt: null,
      reasonCode: "probe_inconclusive",
      evidence: `${seen} (aracı/erişim belirsizliği — servis gözlenmedi)`,
    });
  }

  if (Number.isFinite(status) && status >= 500) {
    return makeCard(id, STATES.FAILED, {
      checkedAt,
      reasonCode: "bridge_error",
      evidence: `${seen} (servis kendi hatasını bildirdi)`,
    });
  }

  // §4 son satır — beklenmeyen değer ASLA healthy sayılmaz.
  return makeCard(id, STATES.UNKNOWN, {
    checkedAt: null,
    reasonCode: "unmapped_value",
    evidence: `${seen} body.status=${JSON.stringify(body.status ?? null)}`,
  });
}

/**
 * §3.1 — freshness uygulaması. `age > ttl` → `stale`; son bilinen sonuç
 * `last_known` alanında KORUNUR (bilgi yok edilmez).
 *
 * @param {object} card   deriveBridgeLlm çıktısı
 * @param {number} nowMs  Şu anki zaman (ms). Dışarıdan verilir.
 */
export function applyFreshness(card, nowMs) {
  if (!card || !card.checked_at) return card;
  if (!isMeasuredState(card.state)) return card;
  if (card.state === STATES.STALE) return card;

  const checkedMs = Date.parse(card.checked_at);
  if (!Number.isFinite(checkedMs)) {
    // Çözümlenemeyen timestamp → uydurma yok, bilgi yokluğu.
    return makeCard(card.id, STATES.UNKNOWN, {
      checkedAt: null,
      reasonCode: "unmapped_value",
      evidence: `${card.evidence} (checked_at çözümlenemedi)`,
    });
  }

  const ageSeconds = (nowMs - checkedMs) / 1000;
  if (ageSeconds <= card.ttl_seconds) return card;

  return makeCard(card.id, STATES.STALE, {
    checkedAt: card.checked_at,
    lastKnown: card.state === STATES.HEALTHY ? STATES.HEALTHY : STATES.FAILED,
    reasonCode: "freshness_expired",
    evidence: card.evidence,
  });
}

/**
 * §5 — durum → UI sunumu. Her durumun KENDİ glifi ve KENDİ erişilebilir etiket
 * anahtarı vardır; ikisi de paylaşılmaz (en olası ihlal: not_configured ile
 * unknown'ın tek gri rozete indirgenmesi).
 */
export const STATE_PRESENTATION = Object.freeze({
  [STATES.NOT_CONFIGURED]: Object.freeze({
    glyph: "⚪",
    tone: "neutral",
    labelKey: "panel.health.state.not_configured",
    a11yKey: "panel.health.a11y.not_configured",
    actionKey: "panel.health.action.setup",
  }),
  [STATES.UNKNOWN]: Object.freeze({
    glyph: "◌",
    tone: "neutral-secondary",
    labelKey: "panel.health.state.unknown",
    a11yKey: "panel.health.a11y.unknown",
    actionKey: "panel.health.action.check",
  }),
  [STATES.HEALTHY]: Object.freeze({
    glyph: "🟢",
    tone: "positive",
    labelKey: "panel.health.state.healthy",
    a11yKey: "panel.health.a11y.healthy",
    actionKey: null,
  }),
  [STATES.FAILED]: Object.freeze({
    glyph: "🔴",
    tone: "negative",
    labelKey: "panel.health.state.failed",
    a11yKey: "panel.health.a11y.failed",
    actionKey: "panel.health.action.retry",
  }),
  [STATES.STALE]: Object.freeze({
    glyph: "🟡",
    tone: "warning",
    labelKey: "panel.health.state.stale",
    a11yKey: "panel.health.a11y.stale",
    actionKey: "panel.health.action.check",
  }),
});

/**
 * §3.4 — `checked_at = null` HİÇBİR koşulda göreli zamana çevrilmez.
 * Dönüş `null` ise çağıran "hiç kontrol edilmedi" metnini kullanır.
 */
export function freshnessMinutes(card, nowMs) {
  if (!card || !card.checked_at) return null;
  const checkedMs = Date.parse(card.checked_at);
  if (!Number.isFinite(checkedMs)) return null;
  return Math.max(0, Math.floor((nowMs - checkedMs) / 60000));
}
