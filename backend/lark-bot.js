import "dotenv/config";
import * as Lark from "@larksuiteoapi/node-sdk";
import OpenAI from "openai";
import {
  createMessageDeduper,
  createSafetyIdentifier,
  normalizeLumosReply,
  parseLarkTextMessage,
} from "./larkBotCore.js";
import { LUMOS_CHAT_INSTRUCTIONS } from "./lumosInstructions.js";

const appId = String(process.env.LARK_APP_ID || "").trim();
const appSecret = String(process.env.LARK_APP_SECRET || "").trim();
const lumosChatUrl = String(process.env.LUMOS_CHAT_URL || "").trim();
const openaiApiKey = String(process.env.OPENAI_API_KEY || "").trim();
const openaiModel = String(process.env.OPENAI_MODEL || "gpt-5.6-terra").trim();
const requestTimeoutMs = Number(process.env.LARK_LUMOS_TIMEOUT_MS || 25_000);

if (!appId || !appSecret) {
  console.error("LARK_APP_ID ve LARK_APP_SECRET gerekli.");
  process.exit(1);
}
if (!lumosChatUrl && !openaiApiKey) {
  console.error("LUMOS_CHAT_URL veya OPENAI_API_KEY gerekli.");
  process.exit(1);
}

const baseConfig = {
  appId,
  appSecret,
  domain: Lark.Domain.Lark,
};
const client = new Lark.Client(baseConfig);
const wsClient = new Lark.WSClient({
  ...baseConfig,
  loggerLevel: Lark.LoggerLevel.info,
});
const isDuplicate = createMessageDeduper();
const openai = openaiApiKey
  ? new OpenAI({ apiKey: openaiApiKey, timeout: requestTimeoutMs })
  : null;

async function askLumos(message, senderId) {
  if (lumosChatUrl) {
    const response = await fetch(lumosChatUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, locale: "tr" }),
      signal: AbortSignal.timeout(requestTimeoutMs),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(`Lumos chat HTTP ${response.status}`);
    return normalizeLumosReply(payload?.reply);
  }

  const response = await openai.responses.create({
    model: openaiModel,
    instructions: LUMOS_CHAT_INSTRUCTIONS,
    input: message,
    max_output_tokens: 1_200,
    safety_identifier: createSafetyIdentifier(senderId),
    store: false,
  });
  return normalizeLumosReply(response.output_text);
}

async function sendLarkText(chatId, text) {
  await client.im.v1.message.create({
    params: { receive_id_type: "chat_id" },
    data: {
      receive_id: chatId,
      msg_type: "text",
      content: JSON.stringify({ text: normalizeLumosReply(text) }),
    },
  });
}

async function processMessage(event) {
  const incoming = parseLarkTextMessage(event);
  if (!incoming || isDuplicate(incoming.messageId)) return;

  try {
    const reply = await askLumos(incoming.text, incoming.senderId);
    await sendLarkText(incoming.chatId, reply);
  } catch (error) {
    console.error("Lark mesajı işlenemedi:", error?.message || String(error));
    await sendLarkText(incoming.chatId, "Şu anda bağlantı kuramadım. Lütfen biraz sonra tekrar dene.").catch(
      () => {}
    );
  }
}

const eventDispatcher = new Lark.EventDispatcher({}).register({
  "im.message.receive_v1": (event) => {
    void processMessage(event);
  },
});

console.log("Lumos Lark persistent connection başlatılıyor.");
wsClient.start({ eventDispatcher });
