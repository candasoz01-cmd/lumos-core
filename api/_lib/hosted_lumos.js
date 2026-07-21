import { openSession, readCookie, sessionLumosId } from "./lumos_session.js";

export const HOSTED_MODEL = "gemini-2.5-flash";
export const OPENAI_HOSTED_MODEL = "gpt-5.6-luna";

// Cookie kullanamayan mobil istemci oturumu Bearer başlığıyla sunabilir.
// Cookie her zaman önceliklidir; başlık yalnız cookie yoksa değerlendirilir.
function bearerClaims(req) {
  const rawAuthorization = String(
    req?.headers?.authorization || req?.headers?.Authorization || "",
  ).trim();
  const match = rawAuthorization.match(/^Bearer\s+([^\s]+)$/i);
  return match ? openSession(match[1]) : null;
}

export function hasLumosSession(req) {
  return Boolean(hostedSessionClaims(req));
}

export function hostedSessionClaims(req) {
  return openSession(readCookie(req)) || bearerClaims(req);
}

function cleanMemoryItems(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .slice(0, 12)
    .map((item) =>
      typeof item === "string" ? item : String(item?.summary || item?.text || ""),
    )
    .map((item) => item.trim().slice(0, 1000))
    .filter(Boolean);
}

export async function loadAllowedMemory(lumosId) {
  const url = String(process.env.LUMOS_MEMORY_LOOKUP_URL || "").trim();
  const token = String(process.env.LUMOS_MEMORY_SERVICE_TOKEN || "").trim();
  if (!url || !token) return { status: "unavailable", items: [] };
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ lumos_id: lumosId, purpose: "hosted_chat" }),
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return { status: "unavailable", items: [] };
    const payload = await response.json();
    if (payload?.consent !== true) return { status: "not_granted", items: [] };
    const items = cleanMemoryItems(payload?.memories);
    return { status: items.length ? "loaded" : "empty", items };
  } catch {
    return { status: "unavailable", items: [] };
  }
}

export async function loadHostedUserContext(req, body) {
  const claims = hostedSessionClaims(req);
  if (!claims) return { ok: false, error: "unauthorized", status: 401 };
  const lumosId = sessionLumosId(claims);
  if (!lumosId) return { ok: false, error: "identity_missing", status: 401 };
  const requestedLumosId = String(body?.identity?.lumos_id || "").trim();
  if (requestedLumosId && requestedLumosId !== lumosId) {
    return { ok: false, error: "identity_mismatch", status: 409 };
  }
  const name = String(claims.name || "").trim();
  const email = String(claims.email || "").trim();
  const memory = await loadAllowedMemory(lumosId);
  return {
    ok: true,
    lumos_id: lumosId,
    session_id: String(claims.sid || ""),
    conversation_id: String(body?.conversation_id || "").trim().slice(0, 120),
    profile: {
      status: name || email ? "loaded" : "unavailable",
      name,
      email,
      provider: String(claims.provider || "google_web"),
      connected: true,
    },
    memory,
    package: String(claims.package || "base"),
  };
}

function memoryStatusText(memory) {
  if (memory?.status === "loaded") return "İzin verilmiş kişisel hafıza yüklendi.";
  if (memory?.status === "empty") return "İzin var; kişisel hafıza kaydı bulunamadı.";
  if (memory?.status === "not_granted") return "Kişisel hafıza izni verilmedi; özel hafıza yüklenmedi.";
  return "Oturum bağlı ama kişisel hafıza yüklenmedi.";
}

export function identityStatusReply(message, context) {
  if (!/(beni tanıyor musun|ben kimim|kim olduğumu biliyor musun|do you know me|who am i)/i.test(String(message || ""))) {
    return "";
  }
  if (!context?.profile || context.profile.status !== "loaded") {
    return "Oturum bağlı ama kullanıcı profili yüklenmedi. " + memoryStatusText(context?.memory);
  }
  const name = context.profile.name || context.profile.email || "kullanıcı";
  return `Evet, ${name}. Google hesabın Lumos oturumuna bağlı. ${memoryStatusText(context.memory)}`;
}

function identityInstruction(context) {
  if (!context?.ok) return "";
  const profile = context.profile || {};
  const lines = [
    `Bağlı Lumos kullanıcısı: ${profile.name || "ad yüklenmedi"}.`,
    `Hesap sağlayıcısı: ${profile.provider || "bilinmiyor"}; bağlı: ${profile.connected === true ? "evet" : "hayır"}.`,
    `Kişisel hafıza durumu: ${context.memory?.status || "unavailable"}.`,
    "Paket seviyesi kimliği değiştirmez; yalnız özellik ve limitleri belirler.",
    "Profil veya hafıza yoksa kullanıcıyı tanıyormuş gibi uydurma.",
  ];
  if (context.memory?.status === "loaded" && context.memory.items.length) {
    lines.push("Yalnız izinli hafıza özetleri:", ...context.memory.items.map((item) => `- ${item}`));
  }
  return lines.join("\n");
}

export function hostedGeminiKey() {
  return String(process.env.LUMOS_GOOGLE_GEMINI_API_KEY || "").trim();
}

export function hostedOpenAIKey() {
  return String(process.env.OPENAI_API_KEY || "").trim();
}

export function readJsonBody(req) {
  if (req.body && typeof req.body === "object" && !Buffer.isBuffer(req.body)) {
    return req.body;
  }
  if (typeof req.body === "string" && req.body.trim()) {
    return JSON.parse(req.body);
  }
  return {};
}

function cleanHistory(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .slice(-12)
    .map((turn) => ({
      role: turn?.role === "assistant" ? "model" : "user",
      text: String(turn?.content || "").trim().slice(0, 4000),
    }))
    .filter((turn) => turn.text);
}

function isTimeQuestion(message) {
  return /(^|\s)(saat kaç|saat nedir|bugün ayın kaçı|bugünün tarihi|tarih ne)(\s|[?.!]|$)/i.test(
    message,
  );
}

export function localTimeReply(message) {
  if (!isTimeQuestion(message)) return "";
  const now = new Date();
  const time = new Intl.DateTimeFormat("tr-TR", {
    timeZone: "Asia/Famagusta",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(now);
  const date = new Intl.DateTimeFormat("tr-TR", {
    timeZone: "Asia/Famagusta",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(now);
  return `Saat ${time}. Bugün ${date}.`;
}

export function buildGeminiRequest(body, context = null) {
  const message = String(body?.message || "").trim().slice(0, 8000);
  const turns = cleanHistory(body?.history);
  if (!turns.length || turns.at(-1)?.role !== "user" || turns.at(-1)?.text !== message) {
    turns.push({ role: "user", text: message });
  }

  const contents = turns.map((turn, index) => {
    const parts = [{ text: turn.text }];
    if (
      index === turns.length - 1 &&
      turn.role === "user" &&
      typeof body?.imageData === "string" &&
      body.imageData.length <= 380000
    ) {
      parts.push({
        inlineData: {
          mimeType: /^image\//i.test(String(body.photoType || ""))
            ? String(body.photoType)
            : "image/jpeg",
          data: body.imageData,
        },
      });
    }
    return { role: turn.role, parts };
  });

  return {
    systemInstruction: {
      parts: [
        {
          text:
            "Sen Lumos'sun. Kısa, doğal ve yardımcı cevap ver. Kullanıcının dilini kullan. " +
            "İç altyapı adlarını kullanıcıya gösterme. Gerçekte yapmadığın bir cihaz veya dosya işlemini yaptığını söyleme; " +
            "böyle bir işlem istenirse cihaz bağlantısının gerektiğini açıkça belirt.\n" +
            identityInstruction(context),
        },
      ],
    },
    contents,
    generationConfig: {
      temperature: 0.4,
      maxOutputTokens: 1200,
    },
  };
}

export function buildOpenAIRequest(body, context = null) {
  const message = String(body?.message || "").trim().slice(0, 8000);
  const turns = cleanHistory(body?.history);
  if (!turns.length || turns.at(-1)?.role !== "user" || turns.at(-1)?.text !== message) {
    turns.push({ role: "user", text: message });
  }
  const transcript = turns
    .map((turn) => `${turn.role === "model" ? "Lumos" : "Kullanıcı"}: ${turn.text}`)
    .join("\n");
  const imageData = typeof body?.imageData === "string" ? body.imageData : "";
  const mimeType = /^image\//i.test(String(body?.photoType || ""))
    ? String(body.photoType)
    : "image/jpeg";
  const input = imageData && imageData.length <= 380000
    ? [
        {
          role: "user",
          content: [
            { type: "input_text", text: transcript },
            {
              type: "input_image",
              image_url: `data:${mimeType};base64,${imageData}`,
              detail: "auto",
            },
          ],
        },
      ]
    : transcript;

  return {
    model: OPENAI_HOSTED_MODEL,
    instructions:
      "Sen Lumos'sun. Kısa, doğal ve yardımcı cevap ver. Kullanıcının dilini kullan. " +
      "İç altyapı adlarını kullanıcıya gösterme. Gerçekte yapmadığın bir cihaz veya dosya işlemini yaptığını söyleme; " +
      "böyle bir işlem istenirse cihaz bağlantısının gerektiğini açıkça belirt.\n" +
      identityInstruction(context),
    input,
    reasoning: { effort: "none" },
    max_output_tokens: 1200,
    store: false,
  };
}

export function openAIReply(payload) {
  if (!Array.isArray(payload?.output)) return "";
  return payload.output
    .flatMap((item) => (Array.isArray(item?.content) ? item.content : []))
    .map((part) => (part?.type === "output_text" && typeof part.text === "string" ? part.text : ""))
    .join("")
    .trim();
}

export function geminiReply(payload) {
  const parts = payload?.candidates?.[0]?.content?.parts;
  if (!Array.isArray(parts)) return "";
  return parts
    .map((part) => (typeof part?.text === "string" ? part.text : ""))
    .join("")
    .trim();
}
