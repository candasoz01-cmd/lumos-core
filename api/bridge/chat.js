import {
  buildGeminiRequest,
  geminiReply,
  hasLumosSession,
  hostedGeminiKey,
  HOSTED_MODEL,
  localTimeReply,
  readJsonBody,
} from "../_lib/hosted_lumos.js";

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method_not_allowed" });
  if (!hasLumosSession(req)) {
    return res.status(401).json({ error: "unauthorized", errorKind: "unauthorized" });
  }

  let body;
  try {
    body = readJsonBody(req);
  } catch {
    return res.status(400).json({ error: "invalid_json" });
  }
  const message = String(body?.message || "").trim();
  if (!message) return res.status(400).json({ error: "message_required" });

  const localReply = localTimeReply(message);
  if (localReply) return res.status(200).json({ reply: localReply, mode: "hosted_local" });

  const apiKey = hostedGeminiKey();
  if (!apiKey) {
    return res.status(503).json({ error: "model_unconfigured", errorKind: "model_error" });
  }

  try {
    const upstream = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${HOSTED_MODEL}:generateContent`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-goog-api-key": apiKey,
        },
        body: JSON.stringify(buildGeminiRequest(body)),
        signal: AbortSignal.timeout(25000),
      },
    );
    if (!upstream.ok) {
      return res.status(502).json({ error: "model_unavailable", errorKind: "model_error" });
    }
    const reply = geminiReply(await upstream.json());
    if (!reply) {
      return res.status(502).json({ error: "empty_model_reply", errorKind: "model_error" });
    }
    return res.status(200).json({ reply, mode: "hosted_chat", model: HOSTED_MODEL });
  } catch {
    return res.status(502).json({ error: "model_unavailable", errorKind: "model_error" });
  }
}
