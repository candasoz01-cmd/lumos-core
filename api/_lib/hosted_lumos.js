import { openSession, readCookie } from "./lumos_session.js";

export const HOSTED_MODEL = "gemini-2.5-flash";

export function hasLumosSession(req) {
  return Boolean(openSession(readCookie(req)));
}

export function hostedGeminiKey() {
  return String(process.env.LUMOS_GOOGLE_GEMINI_API_KEY || "").trim();
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

export function buildGeminiRequest(body) {
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
            "böyle bir işlem istenirse cihaz bağlantısının gerektiğini açıkça belirt.",
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

export function geminiReply(payload) {
  const parts = payload?.candidates?.[0]?.content?.parts;
  if (!Array.isArray(parts)) return "";
  return parts
    .map((part) => (typeof part?.text === "string" ? part.text : ""))
    .join("")
    .trim();
}
