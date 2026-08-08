/** Meta webhook verification + signed, durable, replay-safe ingestion. */
import {
  ingestMetaWebhook,
  metaWebhookEventKey,
  metaWebhookMaxBytes,
  metaWebhookProvider,
  verifyMetaChallengeToken,
  verifyMetaWebhookSignature,
} from "../_lib/meta_webhook.js";
import { captureError, captureSecurityEvent, logEvent } from "../_lib/observability.js";
import { RawBodyTooLargeError, readBoundedRawBody } from "../_lib/raw_body.js";

const ROUTE = "meta_webhook";

export const config = {
  api: { bodyParser: false },
};

function json(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

function firstHeader(req, name) {
  const target = name.toLowerCase();
  for (const [key, value] of Object.entries(req.headers || {})) {
    if (key.toLowerCase() !== target) continue;
    return Array.isArray(value) ? String(value[0] || "") : String(value || "");
  }
  return "";
}

function handleChallenge(req, res) {
  const url = new URL(req.url || "/", "https://welockai.com");
  const mode = url.searchParams.get("hub.mode");
  const token = url.searchParams.get("hub.verify_token");
  const challenge = String(url.searchParams.get("hub.challenge") || "");
  if (mode !== "subscribe" || !challenge || !verifyMetaChallengeToken(token)) {
    json(res, 403, { ok: false, error: "meta_webhook_verification_failed" });
    return;
  }
  res.statusCode = 200;
  res.setHeader("Content-Type", "text/plain; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(challenge);
}

export default async function handler(req, res) {
  if (req.method === "GET") {
    handleChallenge(req, res);
    return;
  }
  if (req.method !== "POST") {
    json(res, 405, { ok: false, error: "method_not_allowed" });
    return;
  }

  let rawBody;
  try {
    rawBody = await readBoundedRawBody(req, metaWebhookMaxBytes());
  } catch (error) {
    if (error instanceof RawBodyTooLargeError) {
      json(res, 413, { ok: false, error: "meta_webhook_payload_too_large" });
      return;
    }
    await captureError(error, { route: ROUTE, errorCode: "meta_webhook_body_read_failed" });
    json(res, 400, { ok: false, error: "meta_webhook_body_read_failed" });
    return;
  }

  if (!verifyMetaWebhookSignature(rawBody, firstHeader(req, "x-hub-signature-256"))) {
    await captureSecurityEvent("meta_webhook_signature_invalid", { route: ROUTE });
    json(res, 401, { ok: false, error: "meta_webhook_signature_invalid" });
    return;
  }

  let payload;
  try {
    payload = JSON.parse(rawBody.toString("utf8"));
  } catch {
    json(res, 400, { ok: false, error: "meta_webhook_json_invalid" });
    return;
  }
  const provider = metaWebhookProvider(payload);
  if (!provider) {
    json(res, 400, { ok: false, error: "meta_webhook_object_unsupported" });
    return;
  }

  try {
    const eventKey = metaWebhookEventKey(rawBody);
    const result = await ingestMetaWebhook(provider, eventKey, payload);
    json(res, 200, { ok: true, status: result.duplicate ? "duplicate" : "accepted" });
    await logEvent("webhook.ingested", { route: ROUTE, provider, status: result.duplicate ? "duplicate" : "accepted" });
  } catch (error) {
    const errorCode = String(error?.message || "meta_webhook_ingest_failed");
    await captureError(new Error(errorCode), { route: ROUTE, provider, errorCode });
    json(res, 503, { ok: false, error: errorCode });
  }
}
