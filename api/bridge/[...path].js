/**
 * Vercel serverless proxy: /api/bridge/* → BRIDGE_UPSTREAM_URL/*
 * Phase 1: panel POST /api/bridge/task; Phase 2: GET /api/bridge/last-result,
 * POST /api/bridge/controlled, POST /api/bridge/transcribe (multipart/raw).
 * Caller auth + path allowlist are enforced before the bridge secret is injected.
 */

import { timingSafeEqual } from "node:crypto";
import { hostedSessionClaims } from "../_lib/hosted_lumos.js";
import { sessionLumosId } from "../_lib/lumos_session.js";
import { captureError, captureSecurityEvent } from "../_lib/observability.js";

const ROUTE = "bridge_proxy";

export const config = {
  api: {
    bodyParser: false,
  },
};

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

const PROXY_AUTH_HEADER = "x-lumos-bridge-auth";
const PROXY_AUTH_COOKIE = "lumos_bridge_proxy_auth";
const ALLOWED_BRIDGE_PATHS = new Set([
  "task",
  "chat",
  "health",
  "status",
  "last-result",
  "controlled",
  "transcribe",
  "panel/upload",
]);

const PROXY_UNAVAILABLE = {
  ok: false,
  error: "bridge_proxy_unconfigured",
  message:
    "Panel bağlantısı yapılandırılmamış. Köprü ve pano işlemleri bu ortamda devre dışı; cihaz yöneticinizden bağlantı anahtarını tanımlamasını isteyin.",
};

const PROXY_AUTH_UNAVAILABLE = {
  ok: false,
  error: "bridge_proxy_auth_unconfigured",
  message:
    "Panel köprü yetkisi yapılandırılmamış. Bu ortamda köprü proxy kapalı.",
};

const PROXY_SECRET_UNAVAILABLE = {
  ok: false,
  error: "bridge_proxy_secret_unconfigured",
  message:
    "Köprü secret yapılandırılmamış. Bu ortamda köprü proxy kapalı.",
};

const PROXY_FORBIDDEN = {
  ok: false,
  error: "bridge_proxy_forbidden",
  message: "Bu köprü yolu desteklenmiyor.",
};

const PROXY_UNAUTHORIZED = {
  ok: false,
  error: "bridge_proxy_unauthorized",
  message: "Köprü proxy yetkisi eksik veya geçersiz.",
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

function isAllowedBridgePath(segments) {
  return ALLOWED_BRIDGE_PATHS.has(segments.map(String).join("/"));
}

function firstHeader(req, headerName) {
  const needle = headerName.toLowerCase();
  for (const [key, value] of Object.entries(req.headers || {})) {
    if (key.toLowerCase() !== needle || value == null) continue;
    return Array.isArray(value) ? String(value[0] || "") : String(value);
  }
  return "";
}

function cookieValue(rawCookie, name) {
  for (const part of String(rawCookie || "").split(";")) {
    const [rawKey, ...rest] = part.trim().split("=");
    if (rawKey === name) {
      try {
        return decodeURIComponent(rest.join("=") || "");
      } catch {
        return "";
      }
    }
  }
  return "";
}

function requestProxyAuthToken(req) {
  return (
    firstHeader(req, PROXY_AUTH_HEADER).trim() ||
    cookieValue(firstHeader(req, "cookie"), PROXY_AUTH_COOKIE).trim()
  );
}

function safeTokenEqual(actual, expected) {
  const a = Buffer.from(String(actual || ""));
  const b = Buffer.from(String(expected || ""));
  return a.length === b.length && a.length > 0 && timingSafeEqual(a, b);
}

function isProxyCallerAuthorized(req, expectedToken) {
  return safeTokenEqual(requestProxyAuthToken(req), expectedToken);
}

function isAuthenticatedLumosSession(req) {
  const claims = hostedSessionClaims(req);
  if (!claims) return false;
  const lumosId = sessionLumosId(claims);
  if (!lumosId) return false;
  const allowedIds = new Set(
    String(process.env.LUMOS_BRIDGE_ALLOWED_LUMOS_IDS || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
  );
  return allowedIds.has(lumosId);
}

function forwardRequestHeaders(req, secret) {
  const out = {};
  for (const [key, value] of Object.entries(req.headers || {})) {
    const lower = key.toLowerCase();
    if (HOP_BY_HOP.has(lower)) continue;
    if (lower === "x-kando-token") continue;
    if (lower === PROXY_AUTH_HEADER) continue;
    if (lower === "authorization") continue;
    if (lower === "cookie") continue;
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

function bufferFromBodyValue(value) {
  if (value == null) return null;
  if (Buffer.isBuffer(value)) return value;
  if (value instanceof Uint8Array) return Buffer.from(value);
  if (typeof value === "string") return Buffer.from(value, "utf8");
  return null;
}

async function readRawBody(req) {
  if (!req) return Buffer.alloc(0);

  const preloaded = bufferFromBodyValue(req.body);
  if (preloaded && preloaded.length > 0) {
    return preloaded;
  }

  if (typeof req.read === "function") {
    const buffered = [];
    let chunk;
    while ((chunk = req.read()) != null) {
      buffered.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }
    if (buffered.length > 0) {
      return Buffer.concat(buffered);
    }
  }

  if (typeof req.on === "function") {
    const streamed = await new Promise((resolve, reject) => {
      const chunks = [];
      req.on("data", (part) => {
        chunks.push(Buffer.isBuffer(part) ? part : Buffer.from(part));
      });
      req.on("end", () => resolve(Buffer.concat(chunks)));
      req.on("error", reject);
      if (typeof req.resume === "function") {
        req.resume();
      }
    });
    if (streamed.length > 0) {
      return streamed;
    }
  }

  if (req[Symbol.asyncIterator]) {
    const chunks = [];
    for await (const chunk of req) {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }
    return Buffer.concat(chunks);
  }

  return preloaded || Buffer.alloc(0);
}

function applyForwardBody(init, rawBody) {
  if (!rawBody || rawBody.length === 0) {
    return;
  }
  init.body = rawBody;
  // Match declared length to bytes actually forwarded (Vercel may strip stream body).
  init.headers["content-length"] = String(rawBody.length);
}

export {
  applyForwardBody,
  bufferFromBodyValue,
  forwardRequestHeaders,
  isAllowedBridgePath,
  isAuthenticatedLumosSession,
  isProxyCallerAuthorized,
  readRawBody,
};

export default async function handler(req, res) {
  const upstreamBase = normalizeUpstreamBase();
  if (!upstreamBase) {
    await captureError(new Error("bridge_proxy_unconfigured"), {
      route: ROUTE,
      errorCode: "bridge_proxy_unconfigured",
    });
    return res.status(503).json(PROXY_UNAVAILABLE);
  }

  const segments = pathSegments(req.query, req.url);
  if (!isAllowedBridgePath(segments)) {
    // Allowlist dışı yol denemesi — keşif/kötüye kullanım denemesi olabilir.
    await captureSecurityEvent("bridge_proxy_forbidden_path", {
      route: ROUTE,
      path: segments.join("/").slice(0, 64),
    });
    return res.status(404).json(PROXY_FORBIDDEN);
  }

  const proxyAuthToken = String(process.env.LUMOS_BRIDGE_PROXY_AUTH_TOKEN || "").trim();
  if (!proxyAuthToken) {
    await captureError(new Error("bridge_proxy_auth_unconfigured"), {
      route: ROUTE,
      errorCode: "bridge_proxy_auth_unconfigured",
    });
    return res.status(503).json(PROXY_AUTH_UNAVAILABLE);
  }
  if (
    !isProxyCallerAuthorized(req, proxyAuthToken) &&
    !isAuthenticatedLumosSession(req)
  ) {
    // Ne köprü token'ı ne geçerli Lumos oturumu — başarısız erişim denemesi.
    await captureSecurityEvent("bridge_proxy_unauthorized", { route: ROUTE, path: segments.join("/").slice(0, 64) });
    return res.status(401).json(PROXY_UNAUTHORIZED);
  }

  const secret = String(process.env.KANDO_BRIDGE_SECRET || "").trim();
  if (!secret) {
    await captureError(new Error("bridge_proxy_secret_unconfigured"), {
      route: ROUTE,
      errorCode: "bridge_proxy_secret_unconfigured",
    });
    return res.status(503).json(PROXY_SECRET_UNAVAILABLE);
  }

  const targetUrl = `${upstreamBase}/${segments.join("/")}`;
  const method = String(req.method || "GET").toUpperCase();

  const init = {
    method,
    headers: forwardRequestHeaders(req, secret),
  };
  try {
    const upstreamHost = new URL(upstreamBase).hostname.toLowerCase();
    if (/\.ngrok-free\.(app|dev)$/.test(upstreamHost)) {
      init.headers["ngrok-skip-browser-warning"] = "1";
    }
  } catch {
    /* normalizeUpstreamBase sonrası fetch güvenli hata yanıtını üretir */
  }

  if (method !== "GET" && method !== "HEAD") {
    const rawBody = await readRawBody(req);
    applyForwardBody(init, rawBody);
  }

  try {
    const upstreamRes = await fetch(targetUrl, init);
    const body = await upstreamRes.arrayBuffer();
    res.status(upstreamRes.status);
    const fwd = pickForwardResponseHeaders(upstreamRes.headers);
    for (const [key, value] of Object.entries(fwd)) {
      res.setHeader(key, value);
    }
    res.setHeader("Cache-Control", "no-store");
    return res.send(Buffer.from(body));
  } catch (e) {
    await captureError(e, {
      route: ROUTE,
      errorCode: "bridge_upstream_unreachable",
      path: segments.join("/").slice(0, 64),
    });
    return res.status(502).json({
      ok: false,
      error: "bridge_upstream_unreachable",
      message: "İletim tamamlanamadı. Bağlantıyı kontrol edip tekrar dene.",
    });
  }
}
