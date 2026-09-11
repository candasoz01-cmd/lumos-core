import {
  hasLumosSession,
  hostedGeminiKey,
  hostedOpenAIKey,
  OPENAI_HOSTED_MODEL,
} from "../_lib/hosted_lumos.js";
import { captureError } from "../_lib/observability.js";

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "GET" && req.method !== "HEAD") {
    return res.status(405).json({ error: "method_not_allowed" });
  }
  if (!hasLumosSession(req)) return res.status(401).json({ error: "unauthorized" });
  const ready = Boolean(hostedOpenAIKey() || hostedGeminiKey());
  if (!ready) {
    await captureError(new Error("bridge_health_unconfigured"), {
      route: "bridge_health",
      errorCode: "unconfigured",
    });
  }
  return res.status(ready ? 200 : 503).json({
    status: ready ? "ok" : "unconfigured",
    gate: true,
    llm: ready,
    mode: "hosted_secure",
    model: hostedOpenAIKey() ? OPENAI_HOSTED_MODEL : "fallback",
  });
}
