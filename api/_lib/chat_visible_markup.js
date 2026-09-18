/** Display-time chat body formatting. Unsupported TextReference tags unfold to alt or inner text. */

function altFromAttrs(attrs) {
  const match =
    /\balt\s*=\s*(?:"([^"]*)"|'([^']*)'|&quot;([^&]*)&quot;|\{\s*"([^"]*)"\s*\}|\{\s*'([^']*)'\s*\})/i.exec(
      attrs || "",
    );
  if (!match) return "";
  return match[1] || match[2] || match[3] || match[4] || match[5] || "";
}

export function stripUnsupportedChatMarkup(text) {
  if (text == null) return "";
  const tag =
    /(?:<|&lt;)TextReference\b([\s\S]*?)(?:\s*\/\s*(?:>|&gt;)|(?:>|&gt;)([\s\S]*?)(?:<\/|&lt;\/)TextReference\s*(?:>|&gt;))/gi;
  return String(text).replace(tag, (_full, attrs, body) => {
    const alt = altFromAttrs(attrs);
    const inner = body != null ? String(body).trim() : "";
    return alt || inner;
  });
}
