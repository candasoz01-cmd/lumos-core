/**
 * Vercel serverless proxy: /api/bridge/* → BRIDGE_UPSTREAM_URL/*
 * Phase 1: panel POST /api/bridge/task; Phase 2: GET /api/bridge/last-result,
 * POST /api/bridge/controlled.
 * Token injected server-side for all proxied paths.
 */

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
]);

const PROXY_UNAVAILABLE = {
  ok: false,
  error: "bridge_proxy_unconfigured",
  message:
    "Panel bağlantısı yapılandırılmamış. Köprü ve pano işlemleri bu ortamda devre dışı; cihaz yöneticinizden bağlantı anahtarını tanımlamasını isteyin.",
};

function normalizeUpstreamBase() {
  return String(process.env.BRIDGE_UPSTREAM_URL || "")
    .trim()
    .replace(/\/$/, "");
}

function pathSegments(query, url) {
  const raw = query.path;
  if (Array.isArray(raw)) {
    const segments = raw.map((s) => String(s)).filter(Boolean);
    if (segments.length) return segments;
  } else if (raw != null && raw !== "") {
    return [String(raw)];
  }

  if (url) {
    try {
      const pathname = new URL(url, "http://localhost").pathname;
      const prefix = "/api/bridge/";
      if (pathname.startsWith(prefix)) {
        const rest = pathname.slice(prefix.length);
        if (rest) return rest.split("/").filter(Boolean);
      }
    } catch {
      /* ignore malformed URL */
    }
  }
  return [];
}

function forwardRequestHeaders(req, secret) {
  const out = {};
  for (const [key, value] of Object.entries(req.headers || {})) {
    const lower = key.toLowerCase();
    if (HOP_BY_HOP.has(lower)) continue;
    if (lower === "x-kando-token") continue;
    if (value == null) continue;
    out[key] = Array.isArray(value) ? value.join(", ") : String(value);
  }
  if (secret) {
    out["X-Kando-Token"] = secret;
  }
  return out;
}

function pickForwardResponseHeaders(upstreamHeaders) {
  const out = {};
  upstreamHeaders.forEach((value, key) => {
    if (HOP_BY_HOP.has(key.toLowerCase())) return;
    out[key] = value;
  });
  return out;
}

export default async function handler(req, res) {
  const upstreamBase = normalizeUpstreamBase();
  if (!upstreamBase) {
    return res.status(503).json(PROXY_UNAVAILABLE);
  }

  const segments = pathSegments(req.query, req.url);
  const targetUrl = `${upstreamBase}/${segments.join("/")}`;
  const secret = String(process.env.KANDO_BRIDGE_SECRET || "").trim();
  const method = String(req.method || "GET").toUpperCase();

  const init = {
    method,
    headers: forwardRequestHeaders(req, secret),
  };

  if (method !== "GET" && method !== "HEAD") {
    if (typeof req.body === "string") {
      init.body = req.body;
    } else if (req.body != null && typeof req.body === "object") {
      init.body = JSON.stringify(req.body);
      if (!init.headers["Content-Type"] && !init.headers["content-type"]) {
        init.headers["Content-Type"] = "application/json";
      }
    }
  }

  try {
    const upstreamRes = await fetch(targetUrl, init);
    const body = await upstreamRes.arrayBuffer();
    res.status(upstreamRes.status);
    const fwd = pickForwardResponseHeaders(upstreamRes.headers);
    for (const [key, value] of Object.entries(fwd)) {
      res.setHeader(key, value);
    }
    return res.send(Buffer.from(body));
  } catch {
    return res.status(502).json({
      ok: false,
      error: "bridge_upstream_unreachable",
      message: "İletim tamamlanamadı. Bağlantıyı kontrol edip tekrar dene.",
    });
  }
}
