import { createHash } from "node:crypto";

const LARK_TEXT_LIMIT = 4_000;

export function parseLarkTextMessage(event) {
  const message = event?.message;
  if (!message || message.message_type !== "text") return null;
  if (event?.sender?.sender_type && event.sender.sender_type !== "user") return null;

  let content;
  try {
    content = JSON.parse(message.content || "{}");
  } catch {
    return null;
  }

  const text = typeof content?.text === "string" ? content.text.trim() : "";
  const chatId = typeof message.chat_id === "string" ? message.chat_id.trim() : "";
  const messageId = typeof message.message_id === "string" ? message.message_id.trim() : "";
  const senderId =
    typeof event?.sender?.sender_id?.open_id === "string"
      ? event.sender.sender_id.open_id.trim()
      : "";
  if (!text || !chatId || !messageId) return null;

  return { chatId, messageId, senderId, text };
}

export function createSafetyIdentifier(senderId) {
  const value = typeof senderId === "string" ? senderId.trim() : "";
  if (!value) return undefined;
  return createHash("sha256").update(`lark:${value}`).digest("hex");
}

export function normalizeLumosReply(value) {
  const text = typeof value === "string" ? value.trim() : "";
  if (!text) return "Şu anda yanıt oluşturamadım.";
  if (text.length <= LARK_TEXT_LIMIT) return text;
  return `${text.slice(0, LARK_TEXT_LIMIT - 1).trimEnd()}…`;
}

export function createMessageDeduper({ ttlMs = 10 * 60 * 1000, now = Date.now } = {}) {
  const seen = new Map();

  return function isDuplicate(messageId) {
    const current = now();
    for (const [id, expiresAt] of seen) {
      if (expiresAt <= current) seen.delete(id);
    }
    if (seen.has(messageId)) return true;
    seen.set(messageId, current + ttlMs);
    return false;
  };
}
