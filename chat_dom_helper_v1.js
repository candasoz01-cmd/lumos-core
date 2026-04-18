function appendMessage(role, text) {
  const chatEl = document.querySelector("#chat")
  if (!chatEl) return

  const el = document.createElement("div")
  el.className = role
  el.innerText = text

  chatEl.appendChild(el)
  chatEl.scrollTop = chatEl.scrollHeight
}

function appendSystemMessage(text) {
  const chatEl = document.querySelector("#chat")
  if (!chatEl) return

  const el = document.createElement("div")
  el.className = "system"
  el.innerText = text

  chatEl.appendChild(el)
  chatEl.scrollTop = chatEl.scrollHeight
}

export { appendMessage, appendSystemMessage }
