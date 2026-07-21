import {
  deleteAllowedMemory,
  grantMemoryConsent,
  hostedSessionClaims,
  loadAllowedMemory,
  readJsonBody,
} from "../_lib/hosted_lumos.js";
import { sessionLumosId } from "../_lib/lumos_session.js";

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "GET" && req.method !== "POST") {
    return res.status(405).json({ error: "method_not_allowed" });
  }
  const lumosId = sessionLumosId(hostedSessionClaims(req));
  if (!lumosId) return res.status(401).json({ error: "unauthorized" });

  if (req.method === "GET") {
    const memory = await loadAllowedMemory(lumosId);
    return res.status(200).json({
      ok: true,
      status: memory.status,
      consent: memory.status === "loaded" || memory.status === "empty",
      count: memory.items.length,
    });
  }

  let body;
  try {
    body = readJsonBody(req);
  } catch {
    return res.status(400).json({ error: "invalid_json" });
  }
  if (body?.action === "grant") {
    if (body?.consent !== true) {
      return res.status(400).json({ error: "explicit_consent_required" });
    }
    const result = await grantMemoryConsent(lumosId);
    return res.status(result.ok ? 200 : 503).json(result);
  }
  if (body?.action === "delete") {
    if (body?.confirm !== true) {
      return res.status(400).json({ error: "explicit_delete_confirmation_required" });
    }
    const result = await deleteAllowedMemory(lumosId);
    return res.status(result.ok ? 200 : 503).json(result);
  }
  return res.status(400).json({ error: "unsupported_memory_action" });
}
