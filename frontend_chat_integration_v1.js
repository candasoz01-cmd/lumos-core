
import { getProjectContext } from "./lumos_state_integration_v1.js"

function updateCreativeMemory(projectId, text) {
  const ctx = getProjectContext(projectId)

  if (!ctx) return

  if (!ctx.creative) ctx.creative = {
    idea: [],
    details: [],
    direction: []
  }

  const t = text.toLowerCase()

  if (t.length < 4) return

  if (t.includes("karakter") || t.includes("biri") || t.includes("adam") || t.includes("kadın")) {
    ctx.creative.idea.push(text)
  } else if (t.includes("renk") || t.includes("ışık") || t.includes("hava") || t.includes("ortam")) {
    ctx.creative.details.push(text)
  } else {
    ctx.creative.direction.push(text)
  }
}

function buildCreativeContext(projectId) {
  const ctx = getProjectContext(projectId)
  if (!ctx || !ctx.creative) return ""

  let out = "\nYaratıcı hafıza:\n"

  if (ctx.creative.idea.length)
    out += "- Fikir:\n  - " + ctx.creative.idea.join("\n  - ")

  if (ctx.creative.details.length)
    out += "\n- Detay:\n  - " + ctx.creative.details.join("\n  - ")

  if (ctx.creative.direction.length)
    out += "\n- Yön:\n  - " + ctx.creative.direction.join("\n  - ")

  return out + "\n"
}

export { updateCreativeMemory, buildCreativeContext }
