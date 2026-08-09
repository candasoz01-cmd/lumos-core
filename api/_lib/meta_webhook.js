import { createHash, createHmac, timingSafeEqual } from "node:crypto";

function clean(value) {
  return String(value || "").trim();
}

function safeEqual(actual, expected) {
  const left = Buffer.from(clean(actual));
  const right = Buffer.from(clean(expected));
  return left.length > 0 && left.length === right.length && timingSafeEqual(left, right);
}

export function metaWebhookMaxBytes() {
  const configured = Number(process.env.LUMOS_META_WEBHOOK_MAX_BYTES || 262144);
  if (!Number.isSafeInteger(configured) || configured < 1024) return 262144;
  return Math.min(configured, 2097152);
}

export function verifyMetaChallengeToken(token) {
  const expected = clean(process.env.LUMOS_META_WEBHOOK_VERIFY_TOKEN);
  return Boolean(expected) && safeEqual(token, expected);
}

export function verifyMetaWebhookSignature(rawBody, signatureHeader) {
  const match = clean(signatureHeader).match(/^sha256=([a-f0-9]{64})$/i);
  if (!match || !Buffer.isBuffer(rawBody)) return false;
  const provided = Buffer.from(match[1].toLowerCase(), "hex");
  const secrets = [
    clean(process.env.LUMOS_META_APP_SECRET),
    clean(process.env.LUMOS_INSTAGRAM_APP_SECRET),
    // ADR-021 S4: WhatsApp ayrı Business app kimliğiyle koşarsa webhook
    // imzaları o app'in secret'ıyla gelir.
    clean(process.env.LUMOS_WHATSAPP_APP_SECRET),
  ].filter((value, index, values) => value && values.indexOf(value) === index);
  return secrets.some((secret) => {
    const expected = createHmac("sha256", secret).update(rawBody).digest();
    return provided.length === expected.length && timingSafeEqual(provided, expected);
  });
}

export function metaWebhookProvider(payload) {
  const object = clean(payload?.object).toLowerCase();
  if (object === "whatsapp_business_account") return "whatsapp";
  if (object === "instagram") return "instagram";
  if (object === "page") return "facebook";
  return "";
}

export function metaWebhookEventKey(rawBody) {
  return createHash("sha256").update(rawBody).digest("hex");
}

function webhookSinkConfiguration() {
  const url = clean(process.env.LUMOS_META_WEBHOOK_SINK_URL);
  const token = clean(process.env.LUMOS_META_WEBHOOK_SINK_TOKEN);
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") return { configured: false, url: "", token: "" };
  } catch {
    return { configured: false, url: "", token: "" };
  }
  return { configured: Boolean(token), url, token };
}

export async function ingestMetaWebhook(provider, eventKey, payload, fetchImpl = fetch) {
  const config = webhookSinkConfiguration();
  if (!config.configured) throw new Error("meta_webhook_sink_not_configured");
  const response = await fetchImpl(config.url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      operation: "webhook.ingest",
      provider,
      event_key: eventKey,
      payload,
    }),
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error("meta_webhook_sink_failed");
  const result = await response.json();
  if (result?.ok !== true || !new Set(["accepted", "duplicate"]).has(result?.status)) {
    throw new Error("meta_webhook_sink_invalid_response");
  }
  return { duplicate: result.status === "duplicate" };
}
