/**
 * GET /api/auth/readiness — secret sızdırmaz canlı hazırlık
 */
export default async function handler(req, res) {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.end("method_not_allowed");
    return;
  }
  const clientId = (process.env.LUMOS_GOOGLE_WEB_CLIENT_ID || "").trim();
  const secret = (process.env.LUMOS_GOOGLE_WEB_CLIENT_SECRET || "").trim();
  // Ayrı state secret tercih (Client Secret’tan bağımsız) — değerde sızdırma yok
  const stateDedicated = (process.env.LUMOS_AUTH_STATE_SECRET || "").trim();
  const identityDedicated = (process.env.LUMOS_ID_SECRET || "").trim();
  const memoryUrl = (process.env.LUMOS_MEMORY_LOOKUP_URL || "").trim();
  const memoryToken = (process.env.LUMOS_MEMORY_SERVICE_TOKEN || "").trim();
  const hasModelKey = Boolean(
    (process.env.OPENAI_API_KEY || "").trim() ||
    (process.env.LUMOS_GOOGLE_GEMINI_API_KEY || "").trim()
  );
  const redirect = (
    process.env.LUMOS_GOOGLE_WEB_REDIRECT_URI ||
    "https://welockai.com/auth/google/callback"
  ).trim();
  const live =
    Boolean(clientId) &&
    Boolean(secret) &&
    Boolean(stateDedicated) &&
    stateDedicated.length >= 32;
  res.statusCode = 200;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(
    JSON.stringify({
      ok: true,
      live_login: live,
      client_id_prefix: clientId ? clientId.slice(0, 8) : "",
      redirect_uri: redirect,
      has_client_secret: Boolean(secret),
      has_dedicated_state_secret: Boolean(stateDedicated),
      stable_identity: identityDedicated.length >= 32,
      has_dedicated_identity_secret: identityDedicated.length >= 32,
      has_model_key: hasModelKey,
      // Yalnız env hazırlığı; gerçek OAuth/model çağrısı veya canlı kabul kanıtı değil.
      panel_configured: live && identityDedicated.length >= 32 && hasModelKey,
      consent_memory_lookup: Boolean(memoryUrl && memoryToken),
      door: "lumos",
    })
  );
}
