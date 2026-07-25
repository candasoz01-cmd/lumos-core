import {
  hostedOpenAIKey,
  hostedSessionClaims,
} from "../_lib/hosted_lumos.js";
import { sessionLumosId } from "../_lib/lumos_session.js";

export const REALTIME_MODEL = "gpt-realtime-2.1";
const WINDOW_MS = 60_000;
const MAX_SESSIONS_PER_WINDOW = 6;
const sessionWindows = new Map();

function allowSession(lumosId, now = Date.now()) {
  const current = sessionWindows.get(lumosId);
  if (!current || now - current.startedAt >= WINDOW_MS) {
    sessionWindows.set(lumosId, { startedAt: now, count: 1 });
    return true;
  }
  if (current.count >= MAX_SESSIONS_PER_WINDOW) return false;
  current.count += 1;
  return true;
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "POST") {
    return res.status(405).json({ error: "method_not_allowed" });
  }

  const lumosId = sessionLumosId(hostedSessionClaims(req));
  if (!lumosId) return res.status(401).json({ error: "unauthorized" });
  if (!allowSession(lumosId)) {
    return res.status(429).json({ error: "rate_limited" });
  }

  const apiKey = hostedOpenAIKey();
  if (!apiKey) {
    return res.status(503).json({ error: "realtime_unconfigured" });
  }

  let upstream;
  try {
    upstream = await fetch("https://api.openai.com/v1/realtime/client_secrets", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "OpenAI-Safety-Identifier": lumosId,
      },
      body: JSON.stringify({
        session: {
          type: "realtime",
          model: REALTIME_MODEL,
          instructions: [
            "Sen Lumos'sun.",
            "Türkçe, doğal ve kısa konuş.",
            "Kullanıcı sözünü keserse dur ve onu dinle.",
            "Emin olmadığın bilgiyi kesinmiş gibi söyleme.",
            "Ödeme, silme veya geri döndürülemez işlemleri açık onay olmadan yapma.",
          ].join(" "),
          audio: {
            input: {
              turn_detection: {
                type: "semantic_vad",
                eagerness: "medium",
                create_response: true,
                interrupt_response: true,
              },
            },
            output: {
              voice: "marin",
              speed: 1.0,
            },
          },
          max_output_tokens: 512,
        },
      }),
      signal: AbortSignal.timeout(8_000),
    });
  } catch {
    return res.status(502).json({ error: "realtime_unavailable" });
  }

  if (!upstream.ok) {
    return res.status(502).json({ error: "realtime_unavailable" });
  }

  let payload;
  try {
    payload = await upstream.json();
  } catch {
    return res.status(502).json({ error: "realtime_invalid_response" });
  }
  const value = String(payload?.value || "").trim();
  if (!value) {
    return res.status(502).json({ error: "realtime_invalid_response" });
  }

  return res.status(200).json({
    ok: true,
    client_secret: {
      value,
      expires_at: Number(payload?.expires_at || 0),
    },
    model: REALTIME_MODEL,
    page: "/canli-ses",
  });
}
