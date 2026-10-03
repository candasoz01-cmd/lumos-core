/**
 * Tek dosyalık oturum sürümü. Çıkış sürümü artırır; eski sv reddedilir.
 * Birden fazla sunucu kopyası bu dosyayı paylaşmaz.
 */
import fs from "node:fs";
import path from "node:path";

export function sessionEpochPath() {
  const configured = String(process.env.LUMOS_SESSION_EPOCH_PATH || "").trim();
  if (configured) return configured;
  return path.join(process.cwd(), ".lumos", "session_epoch.json");
}

function readStore() {
  try {
    const raw = fs.readFileSync(sessionEpochPath(), "utf8");
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return parsed;
  } catch {
    return {};
  }
}

export function currentEpoch(lumosId) {
  const id = String(lumosId || "").trim();
  if (!id) return 0;
  const value = Number(readStore()[id] || 0);
  return Number.isSafeInteger(value) && value >= 0 ? value : 0;
}

export function bumpEpoch(lumosId) {
  const id = String(lumosId || "").trim();
  if (!id) return 0;
  const store = readStore();
  const next = currentEpoch(id) + 1;
  store[id] = next;
  const file = sessionEpochPath();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(store));
  return next;
}

export function sessionEpochAllows(claims, lumosId) {
  if (!claims || typeof claims !== "object") return false;
  const id = String(lumosId || claims.lumos_id || "").trim();
  if (!id) return false;
  const raw = claims.sv;
  const sv = raw == null || raw === "" ? 0 : Number(raw);
  if (!Number.isSafeInteger(sv) || sv < 0) return false;
  return sv >= currentEpoch(id);
}
