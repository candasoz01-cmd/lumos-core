import {
  saveStateFromMessage,
  updateCreativeMemory,
  buildCreativeContext,
  getProjectContext
} from "./lumos_state_integration_v1.js"

function handleUserMessage(projectId, userText) {
  saveStateFromMessage(projectId, userText)
}

function buildPrompt(projectId, userText) {
  const ctx = getProjectContext(projectId)
  let contextBlock = ""

  if (ctx.decisions.length) {
    contextBlock += "\nKararlar:\n- " + ctx.decisions.join("\n- ")
  }

  if (ctx.style.length) {
    contextBlock += "\nStil:\n- " + ctx.style.join("\n- ")
  }

  if (ctx.structure.length) {
    contextBlock += "\nYapı:\n- " + ctx.structure.join("\n- ")
  }

  return contextBlock + "\n\nKullanıcı: " + userText
}

function shouldTriggerCreativeFlow(text) {
  const triggers = [
    "çizgi film",
    "hikaye",
    "senaryo",
    "tasarla",
    "hayal",
    "kur",
    "yazalım"
  ]

  return triggers.some(t => String(text || "").toLowerCase().includes(t))
}

function shouldUseFastMode(text) {
  const fastTriggers = [
    "yap",
    "oluştur",
    "ver",
    "hızlı",
    "direkt",
    "kısa",
    "sil",
    "düzenle",
    "aç"
  ]

  return fastTriggers.some(t => String(text || "").toLowerCase().includes(t))
}

function buildCreativeSystemPrompt(userText) {
  return `
Kullanıcı yaratıcı bir şey kurmak istiyor.

Kurallar:
- Kullanıcının yerine üretme
- Tek seferde bir soru sor
- Kullanıcıyı düşündür
- Eksik yerleri kendin doldurma

İlk soru:
Aklına ilk gelen şeyi söyle.

Kullanıcı:
${userText}
`
}

function buildFastPrompt(userText) {
  return `
Kullanıcı hızlı sonuç istiyor.

Kurallar:
- Kısa cevap ver
- Soru sorma
- Direkt yönlendir veya üret
- Gereksiz açıklama yapma

Kullanıcı:
${userText}
`
}

function buildSystemTone(mode) {
  if (mode === "fast") {
    return `
Ton:
- Kısa
- Net
- Direkt
- Gereksiz kelime yok
`
  }

  if (mode === "creative") {
    return `
Ton:
- Yavaşlat
- Düşündür
- Tek soru sor
- Kullanıcıyı üretime yaklaştır
- Onun yerine üretme
`
  }

  return `
Ton:
- Normal
- Dengeli
- Kısa ve anlaşılır
`
}

async function sendChat(projectId, userText) {
  handleUserMessage(projectId, userText)

  let mode = "normal"
  if (shouldUseFastMode(userText)) mode = "fast"
  else if (shouldTriggerCreativeFlow(userText)) mode = "creative"

  if (mode === "creative") {
    updateCreativeMemory(projectId, userText)
  }

  const toneBlock = buildSystemTone(mode)
  let finalPrompt = toneBlock + "\n" + buildPrompt(projectId, userText)

  if (mode === "creative") {
    finalPrompt = toneBlock + "\n" + buildCreativeSystemPrompt(userText) + buildCreativeContext(projectId)
  }

  if (mode === "fast") {
    finalPrompt = toneBlock + "\n" + buildFastPrompt(userText)
  }

  const res = await fetch("http://127.0.0.1:8766/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: finalPrompt })
  })

  const data = await res.json()
  return data.reply || data.error || "Cevap gelmedi."
}

export {
  sendChat,
  shouldTriggerCreativeFlow,
  shouldUseFastMode
}
