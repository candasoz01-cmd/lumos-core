import { sendChat, shouldTriggerCreativeFlow, shouldUseFastMode } from "./frontend_chat_hook_v1.js"
import { appendMessage, appendSystemMessage } from "./chat_dom_helper_v1.js"

const projectId = "default"

function detectMode(text) {
  if (shouldUseFastMode(text)) return "fast"
  if (shouldTriggerCreativeFlow(text)) return "creative"
  return "normal"
}

async function onUserSend(text) {
  const mode = detectMode(text)

  if (mode === "fast") appendSystemMessage("Hızlı mod")
  if (mode === "creative") appendSystemMessage("Yaratıcı mod")

  appendMessage("user", text)

  const reply = await sendChat(projectId, text)

  appendMessage("assistant", reply)
}

export { onUserSend }
