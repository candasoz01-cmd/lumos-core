/**
 * Geri bildirim paneli v0 — welockai.com
 * GET  /api/feedback  → endpoint durumu (secret sızdırmaz)
 * POST /api/feedback  → ön izleme kabul (kalıcı store YOK; sahte «alındı» yok)
 */
import { randomUUID } from "node:crypto";

const TYPES = new Set(["bug", "copy", "ux", "idea", "other"]);
const MAX_MESSAGE = 2000;
const MAX_SURFACE = 160;
const MAX_EMAIL = 160;
const RATE_WINDOW_MS = 60_000;
const RATE_MAX = 5;

/** Best-effort (warm instance). Serverless soğuk başlangıçta sıfırlanır. */
const _rateByIp = new Map();

function json(res, status, body, extraHeaders) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  if (extraHeaders) {
    for (const [k, v] of Object.entries(extraHeaders)) res.setHeader(k, v);
  }
  res.end(JSON.stringify(body));
}

function userMessage(code) {
  const map = {
    method_not_allowed: "Bu yöntem desteklenmiyor.",
    body_too_large: "İstek çok büyük.",
    invalid_json: "Geçersiz istek.",
    invalid_feedback_type: "Geçerli bir tür seçin.",
    message_too_short: "Mesaj çok kısa.",
    invalid_contact_email: "E-posta geçersiz görünüyor.",
    rate_limited: "Çok sık deneme. Bir dakika sonra tekrar dene.",
    honeypot: "İstek reddedildi.",
  };
  return map[code] || "İstek işlenemedi.";
}

function clientIp(req) {
  const xf = String(req.headers["x-forwarded-for"] || "")
    .split(",")[0]
    .trim();
  return xf || String(req.socket?.remoteAddress || "unknown");
}

function rateLimitOk(ip) {
  const now = Date.now();
  const cut = now - RATE_WINDOW_MS;
  const prev = (_rateByIp.get(ip) || []).filter((t) => t > cut);
  if (prev.length >= RATE_MAX) {
    _rateByIp.set(ip, prev);
    return false;
  }
  prev.push(now);
  _rateByIp.set(ip, prev);
  if (_rateByIp.size > 2000) {
    for (const [k, times] of _rateByIp) {
      const keep = times.filter((t) => t > cut);
      if (keep.length === 0) _rateByIp.delete(k);
      else _rateByIp.set(k, keep);
    }
  }
  return true;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (c) => {
      size += c.length;
      if (size > 24_000) {
        reject(new Error("body_too_large"));
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => {
      try {
        const raw = Buffer.concat(chunks).toString("utf8") || "{}";
        resolve(JSON.parse(raw));
      } catch (e) {
        reject(e);
      }
    });
    req.on("error", reject);
  });
}

function clean(s, max) {
  return String(s || "")
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "")
    .trim()
    .slice(0, max);
}

export default async function handler(req, res) {
  if (req.method === "GET") {
    json(res, 200, {
      ok: true,
      endpoint: "web_form",
      accepts_post: true,
      persisted: false,
      preview: true,
      pool: "Lumos Ortak Geri Bildirim Havuzu",
      delivery: {
        web_form: "preview_only_no_store",
        slack: "not_in_this_slice",
        lark: "not_in_this_slice",
      },
      principle:
        "Ön izleme — kalıcı kaydedilmez. Kimlik korunur; DM taranmaz. Sahte «canlı alındı» yok.",
      page: "/geri-bildirim",
      rate_limit: { window_sec: 60, max_post: RATE_MAX, note: "best_effort_per_instance" },
    });
    return;
  }

  if (req.method !== "POST") {
    json(res, 405, {
      ok: false,
      error: "method_not_allowed",
      persisted: false,
      message: userMessage("method_not_allowed"),
    });
    return;
  }

  const ip = clientIp(req);
  if (!rateLimitOk(ip)) {
    json(
      res,
      429,
      {
        ok: false,
        error: "rate_limited",
        persisted: false,
        message: userMessage("rate_limited"),
      },
      { "Retry-After": "60" }
    );
    return;
  }

  let body;
  try {
    body = await readBody(req);
  } catch (e) {
    const err =
      String(e && e.message) === "body_too_large" ? "body_too_large" : "invalid_json";
    const code = err === "body_too_large" ? 413 : 400;
    json(res, code, {
      ok: false,
      error: err,
      persisted: false,
      message: userMessage(err),
    });
    return;
  }

  // Honeypot — doldurulursa başarı iddiası olmadan reddet
  if (clean(body.website || body.company_url, 80)) {
    json(res, 400, {
      ok: false,
      error: "honeypot",
      persisted: false,
      message: userMessage("honeypot"),
    });
    return;
  }

  const feedbackType = clean(body.feedback_type, 32);
  const message = clean(body.message, MAX_MESSAGE);
  const surface = clean(body.surface, MAX_SURFACE);
  const contact = clean(body.contact_email, MAX_EMAIL);

  if (!TYPES.has(feedbackType)) {
    json(res, 400, {
      ok: false,
      error: "invalid_feedback_type",
      persisted: false,
      message: userMessage("invalid_feedback_type"),
    });
    return;
  }
  if (message.length < 8) {
    json(res, 400, {
      ok: false,
      error: "message_too_short",
      persisted: false,
      message: userMessage("message_too_short"),
    });
    return;
  }
  if (contact && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)) {
    json(res, 400, {
      ok: false,
      error: "invalid_contact_email",
      persisted: false,
      message: userMessage("invalid_contact_email"),
    });
    return;
  }

  const previewId = `fb_preview_${randomUUID().replace(/-/g, "").slice(0, 12)}`;
  // Ön izleme: message / contact_email / page_url asla loglanmaz (opt-in dahil)
  console.log(
    "[feedback_preview]",
    JSON.stringify({
      preview_id: previewId,
      feedback_type: feedbackType,
      surface: surface || null,
      has_contact: Boolean(contact),
      message_len: message.length,
      at: new Date().toISOString(),
      status: "preview_only",
      persisted: false,
      delivery: "preview_only_no_store",
    })
  );

  json(res, 200, {
    ok: true,
    preview_id: previewId,
    status: "preview_only",
    persisted: false,
    delivery: "preview_only_no_store",
    message:
      "Deneme tamam — kalıcı kaydedilmedi. Ortak havuz / Slack / Lark aktarımı bu dilimde yok.",
  });
}
