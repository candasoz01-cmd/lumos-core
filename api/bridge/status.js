import { hasLumosSession, hostedGeminiKey, HOSTED_MODEL } from "../_lib/hosted_lumos.js";

export default function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "GET") return res.status(405).json({ error: "method_not_allowed" });
  if (!hasLumosSession(req)) return res.status(401).json({ error: "unauthorized" });
  const ready = Boolean(hostedGeminiKey());
  return res.status(ready ? 200 : 503).json({
    health: ready ? "ok" : "unconfigured",
    chat: ready ? "ready" : "unconfigured",
    visionConfigured: ready,
    visionLastStatus: "—",
    model: HOSTED_MODEL,
    runtime: "hosted",
  });
}
