import {
  hasLumosSession,
  hostedGeminiKey,
  hostedOpenAIKey,
} from "../_lib/hosted_lumos.js";
import { captureError } from "../_lib/observability.js";

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "GET") return res.status(405).json({ error: "method_not_allowed" });
  if (!hasLumosSession(req)) return res.status(401).json({ error: "unauthorized" });
  const ready = Boolean(hostedOpenAIKey() || hostedGeminiKey());
  if (!ready) {
    await captureError(new Error("bridge_status_unconfigured"), {
      route: "bridge_status",
      errorCode: "unconfigured",
    });
  }
  return res.status(ready ? 200 : 503).json({
    health: ready ? "ok" : "unconfigured",
    chat: ready ? "ready" : "unconfigured",
    visionConfigured: ready,
    visionLastStatus: "—",
    // PR-005 / ADR-019: sağlayıcı ve model adı kullanıcı yüzeyine yazılmaz.
    // Bu ayrıntı yalnız Lumos Agent Wall (iç operatör yüzeyi) kapsamındadır.
    runtime: "hosted",
  });
}
