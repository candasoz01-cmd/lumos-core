import test from "node:test";
import assert from "node:assert/strict";
import {
  createMessageDeduper,
  createSafetyIdentifier,
  normalizeLumosReply,
  parseLarkTextMessage,
} from "./larkBotCore.js";

test("metin mesajını güvenli alanlara ayırır", () => {
  assert.deepEqual(
    parseLarkTextMessage({
      sender: { sender_type: "user" },
      message: {
        message_id: "om_1",
        chat_id: "oc_1",
        message_type: "text",
        content: JSON.stringify({ text: "  Merhaba Lumos  " }),
      },
    }),
    { messageId: "om_1", chatId: "oc_1", senderId: "", text: "Merhaba Lumos" }
  );
});

test("gönderen open_id bilgisini ayrı tutar", () => {
  const parsed = parseLarkTextMessage({
    sender: { sender_type: "user", sender_id: { open_id: "ou_private" } },
    message: {
      message_id: "om_1",
      chat_id: "oc_1",
      message_type: "text",
      content: JSON.stringify({ text: "Merhaba" }),
    },
  });

  assert.equal(parsed.senderId, "ou_private");
});

test("gönderen kimliğini sabit ve geri döndürülemez biçimde karmalar", () => {
  const first = createSafetyIdentifier("ou_private");
  const second = createSafetyIdentifier("ou_private");

  assert.equal(first, second);
  assert.equal(first.length, 64);
  assert.notEqual(first, "ou_private");
  assert.equal(createSafetyIdentifier(""), undefined);
});

test("bot ve metin dışı mesajları yok sayar", () => {
  assert.equal(
    parseLarkTextMessage({
      sender: { sender_type: "app" },
      message: {
        message_id: "om_1",
        chat_id: "oc_1",
        message_type: "text",
        content: JSON.stringify({ text: "loop" }),
      },
    }),
    null
  );
  assert.equal(
    parseLarkTextMessage({
      sender: { sender_type: "user" },
      message: { message_id: "om_2", chat_id: "oc_1", message_type: "image", content: "{}" },
    }),
    null
  );
});

test("aynı mesajı TTL içinde tekrar işlemez", () => {
  let current = 1_000;
  const isDuplicate = createMessageDeduper({ ttlMs: 100, now: () => current });
  assert.equal(isDuplicate("om_1"), false);
  assert.equal(isDuplicate("om_1"), true);
  current += 101;
  assert.equal(isDuplicate("om_1"), false);
});

test("boş ve uzun yanıtları Lark sınırına uyarlar", () => {
  assert.equal(normalizeLumosReply(""), "Şu anda yanıt oluşturamadım.");
  const shortened = normalizeLumosReply("a".repeat(5_000));
  assert.equal(shortened.length, 4_000);
  assert.ok(shortened.endsWith("…"));
});
