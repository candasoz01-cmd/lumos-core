import {
  buildGeminiRequest,
  buildOpenAIRequest,
  geminiReply,
  hostedGeminiKey,
  hostedOpenAIKey,
  HOSTED_MODEL,
  identityStatusReply,
  loadHostedUserContext,
  localTimeReply,
  memoryWriteStatusReply,
  OPENAI_HOSTED_MODEL,
  openAIReply,
  readJsonBody,
} from "../_lib/hosted_lumos.js";
import { captureError, captureSecurityEvent } from "../_lib/observability.js";

const ROUTE = "bridge_chat";

async function callOpenAI(body, context) {
  const apiKey = hostedOpenAIKey();
  if (!apiKey) return null;
  const upstream = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildOpenAIRequest(body, context)),
    signal: AbortSignal.timeout(25000),
  });
  if (!upstream.ok) {
    await captureError(new Error("integration_openai_error"), {
      route: ROUTE,
      provider: "openai",
      errorCode: "integration_error",
      upstreamStatus: upstream.status,
    });
    return null;
  }
  const reply = openAIReply(await upstream.json());
  return reply ? { reply, provider: "openai", model: OPENAI_HOSTED_MODEL } : null;
}

async function callGemini(body, context) {
  const apiKey = hostedGeminiKey();
  if (!apiKey) return null;
  const upstream = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${HOSTED_MODEL}:generateContent`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": apiKey,
      },
      body: JSON.stringify(buildGeminiRequest(body, context)),
      signal: AbortSignal.timeout(25000),
    },
  );
  if (!upstream.ok) {
    await captureError(new Error("integration_google_gemini_error"), {
      route: ROUTE,
      provider: "google",
      errorCode: "integration_error",
      upstreamStatus: upstream.status,
    });
    return null;
  }
  const reply = geminiReply(await upstream.json());
  return reply ? { reply, provider: "google", model: HOSTED_MODEL } : null;
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method_not_allowed" });
  let body;
  try {
    body = readJsonBody(req);
  } catch {
    return res.status(400).json({ error: "invalid_json" });
  }
  const message = String(body?.message || "").trim();
  if (!message) return res.status(400).json({ error: "message_required" });

  const userContext = await loadHostedUserContext(req, body);
  if (!userContext.ok) {
    if (userContext.error === "identity_mismatch") {
      // İstemcinin gönderdiği lumos_id, oturum çerezindekiyle uyuşmuyor — tahrifat denemesi olabilir.
      await captureSecurityEvent("identity_mismatch", { route: ROUTE, status: userContext.status });
    }
    return res.status(userContext.status).json({
      error: userContext.error,
      errorKind: userContext.error === "identity_mismatch" ? "identity_mismatch" : "unauthorized",
    });
  }
  const identity = {
    lumos_id: userContext.lumos_id,
    profile_status: userContext.profile.status,
    memory_status: userContext.memory.status,
    account_connected: userContext.profile.connected,
    package: userContext.package,
  };
  const identityReply = identityStatusReply(message, userContext);
  if (identityReply) {
    return res.status(200).json({ reply: identityReply, mode: "hosted_identity_status", identity });
  }

  const memoryReply = memoryWriteStatusReply(userContext);
  if (memoryReply) {
    return res.status(200).json({ reply: memoryReply, mode: "hosted_memory_status", identity });
  }

  const localReply = localTimeReply(message);
  if (localReply) return res.status(200).json({ reply: localReply, mode: "hosted_local", identity });

  if (!hostedOpenAIKey() && !hostedGeminiKey()) {
    await captureError(new Error("model_unconfigured"), { route: ROUTE, errorCode: "model_unconfigured" });
    return res.status(503).json({ error: "model_unconfigured", errorKind: "model_error" });
  }

  try {
    let answer = null;
    try {
      answer = await callOpenAI(body, userContext);
    } catch (e) {
      await captureError(e, { route: ROUTE, provider: "openai", errorCode: "integration_exception" });
      answer = null;
    }
    if (!answer) answer = await callGemini(body, userContext);
    if (!answer) {
      await captureError(new Error("model_unavailable"), { route: ROUTE, errorCode: "model_unavailable" });
      return res.status(502).json({ error: "model_unavailable", errorKind: "model_error" });
    }
    return res.status(200).json({ ...answer, mode: "hosted_chat", identity });
  } catch (e) {
    await captureError(e, { route: ROUTE, errorCode: "model_unavailable_exception" });
    return res.status(502).json({ error: "model_unavailable", errorKind: "model_error" });
  }
}
