/**
 * Lumos oturum — AES-256-GCM mühürlü HttpOnly çerez.
 * Google access_token saklanmaz; yalnızca kimlik bootstrap iddiaları.
 */
import {
  createCipheriv,
  createDecipheriv,
  createHash,
  createHmac,
  randomBytes,
  timingSafeEqual,
} from "node:crypto";

const COOKIE = "lumos_session";
const STATE_COOKIE = "lumos_oauth_state";
const BRIDGE_COOKIE = "lumos_bridge_proxy_auth";
const MAX_AGE = 604800;
const STATE_MAX_AGE = 600;

export function authSecret() {
  const secret = (
    process.env.LUMOS_AUTH_STATE_SECRET ||
    process.env.LUMOS_GOOGLE_WEB_CLIENT_SECRET ||
    ""
  );
  if (!secret.trim()) {
    throw new Error("lumos_auth_secret_unconfigured");
  }
  return secret;
}

function identitySecret() {
  return process.env.LUMOS_ID_SECRET || authSecret();
}

/**
 * Sağlayıcı kimliğini dışarı sızdırmadan, tekrar girişlerde değişmeyen Lumos ID üretir.
 * sid oturumu; lumos_id kullanıcıyı temsil eder. Bu iki alan birbirinin yerine kullanılmaz.
 */
export function lumosIdForProviderIdentity(provider, subject) {
  const cleanProvider = String(provider || "").trim().toLowerCase();
  const cleanSubject = String(subject || "").trim();
  if (!cleanProvider || !cleanSubject) return "";
  const digest = createHmac("sha256", identitySecret())
    .update(`lumos-id-v1:${cleanProvider}:${cleanSubject}`)
    .digest("base64url")
    .slice(0, 24);
  return `lumos_${digest}`;
}

export function sessionLumosId(claims) {
  const existing = String(claims?.lumos_id || "").trim();
  if (existing) return existing;
  return lumosIdForProviderIdentity(claims?.provider, claims?.sub);
}

function keyBytes() {
  return createHash("sha256").update(authSecret()).digest();
}

export function makeState() {
  const n = randomBytes(12).toString("base64url");
  const ts = String(Math.floor(Date.now() / 1000));
  const sig = createHmac("sha256", authSecret())
    .update(`${n}.${ts}`)
    .digest("hex")
    .slice(0, 24);
  return `${n}.${ts}.${sig}`;
}

export function verifyState(state, maxAgeSec = 600) {
  const parts = String(state || "").split(".");
  if (parts.length !== 3) return false;
  const [n, ts, sig] = parts;
  const age = Math.floor(Date.now() / 1000) - Number(ts);
  if (!Number.isFinite(age) || age < 0 || age > maxAgeSec) return false;
  const expect = createHmac("sha256", authSecret())
    .update(`${n}.${ts}`)
    .digest("hex")
    .slice(0, 24);
  try {
    return timingSafeEqual(Buffer.from(expect), Buffer.from(sig));
  } catch {
    return false;
  }
}

/** @param {Record<string, unknown>} claims */
export function sealSession(claims) {
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", keyBytes(), iv);
  const pt = Buffer.from(JSON.stringify(claims), "utf8");
  const enc = Buffer.concat([cipher.update(pt), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([iv, tag, enc]).toString("base64url");
}

/** @returns {Record<string, unknown> | null} */
export function openSession(token) {
  try {
    const buf = Buffer.from(String(token || ""), "base64url");
    if (buf.length < 29) return null;
    const iv = buf.subarray(0, 12);
    const tag = buf.subarray(12, 28);
    const enc = buf.subarray(28);
    const decipher = createDecipheriv("aes-256-gcm", keyBytes(), iv);
    decipher.setAuthTag(tag);
    const pt = Buffer.concat([decipher.update(enc), decipher.final()]);
    const claims = JSON.parse(pt.toString("utf8"));
    if (!claims || typeof claims !== "object") return null;
    const exp = Number(claims.exp || 0);
    if (exp && Math.floor(Date.now() / 1000) > exp) return null;
    return claims;
  } catch {
    return null;
  }
}

export function sessionCookieHeader(sealed) {
  return `${COOKIE}=${sealed}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${MAX_AGE}`;
}

export function stateCookieHeader(state) {
  return `${STATE_COOKIE}=${state}; Path=/auth/google; HttpOnly; Secure; SameSite=Lax; Max-Age=${STATE_MAX_AGE}`;
}

export function clearStateCookieHeader() {
  return `${STATE_COOKIE}=; Path=/auth/google; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;
}

export function stateMatchesCookie(state, cookieState) {
  const actual = Buffer.from(String(state || ""));
  const expected = Buffer.from(String(cookieState || ""));
  return (
    actual.length > 0 &&
    actual.length === expected.length &&
    timingSafeEqual(actual, expected)
  );
}

export function clearSessionCookieHeader() {
  return `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;
}

export function bridgeProxyCookieHeader(token) {
  return `${BRIDGE_COOKIE}=${token}; Path=/api/bridge; HttpOnly; Secure; SameSite=Lax; Max-Age=${MAX_AGE}`;
}

export function clearBridgeProxyCookieHeader() {
  return `${BRIDGE_COOKIE}=; Path=/api/bridge; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;
}

export function readCookie(req, name = COOKIE) {
  const raw = req.headers?.cookie || req.headers?.Cookie || "";
  const parts = String(raw).split(";");
  for (const part of parts) {
    const [k, ...rest] = part.trim().split("=");
    if (k === name) return rest.join("=");
  }
  return "";
}

export function redirectUri() {
  return (
    process.env.LUMOS_GOOGLE_WEB_REDIRECT_URI ||
    "https://welockai.com/auth/google/callback"
  ).trim();
}

export { BRIDGE_COOKIE, COOKIE, MAX_AGE, STATE_COOKIE, STATE_MAX_AGE };
