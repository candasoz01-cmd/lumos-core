const projectMemory = {}

function ensureProject(projectId) {
  if (!projectMemory[projectId]) {
    projectMemory[projectId] = {
      decisions: [],
      style: [],
      structure: [],
      creative: {
        idea: [],
        details: [],
        direction: []
      }
    }
  }
}

function pushLimited(arr, value, limit = 10) {
  const v = String(value || "").trim()
  if (!v) return
  if (!arr.includes(v)) {
    arr.push(v)
    if (arr.length > limit) arr.shift()
  }
}

function detectStateType(text) {
  const t = String(text || "").toLowerCase()

  if (t.includes("stil") || t.includes("sinematik") || t.includes("minimal")) {
    return "style"
  }

  if (t.includes("ilk sahne") || t.includes("sonra") || t.includes("yapı")) {
    return "structure"
  }

  if (t.includes("olsun") || t.includes("yapalım") || t.includes("böyle")) {
    return "decisions"
  }

  return null
}

function saveStateFromMessage(projectId, text) {
  const type = detectStateType(text)
  if (!type) return

  ensureProject(projectId)
  pushLimited(projectMemory[projectId][type], text, 10)
}

function getProjectContext(projectId) {
  ensureProject(projectId)
  return projectMemory[projectId]
}

function updateCreativeMemory(projectId, text) {
  ensureProject(projectId)
  const ctx = projectMemory[projectId]
  const t = String(text || "").toLowerCase().trim()

  if (t.length < 4) return

  if (t.includes("karakter") || t.includes("biri") || t.includes("adam") || t.includes("kadın")) {
    pushLimited(ctx.creative.idea, text, 10)
    return
  }

  if (t.includes("renk") || t.includes("ışık") || t.includes("hava") || t.includes("ortam")) {
    pushLimited(ctx.creative.details, text, 10)
    return
  }

  pushLimited(ctx.creative.direction, text, 10)
}

function buildCreativeContext(projectId) {
  const ctx = getProjectContext(projectId)
  let out = ""

  if (ctx.creative.idea.length) {
    out += "\nFikir:\n- " + ctx.creative.idea.join("\n- ")
  }

  if (ctx.creative.details.length) {
    out += "\nDetay:\n- " + ctx.creative.details.join("\n- ")
  }

  if (ctx.creative.direction.length) {
    out += "\nYön:\n- " + ctx.creative.direction.join("\n- ")
  }

  return out ? "\nYaratıcı hafıza:" + out + "\n" : ""
}

export {
  saveStateFromMessage,
  getProjectContext,
  updateCreativeMemory,
  buildCreativeContext
}
