/**
 * Operatör kaydı. Kullanıcı HTTP JSON'una eklenmez.
 * Ham ileti metni yazılmaz.
 */
import fs from "node:fs";
import path from "node:path";

const FIELDS = [
  "provider",
  "model",
  "region",
  "retention_policy",
  "contract_verified",
  "data_classes_sent",
  "outcome",
  "reason",
];

export function buildOperatorWallRecord(input = {}) {
  const record = {
    audience: "operator",
    at: new Date().toISOString(),
  };
  for (const key of FIELDS) {
    if (input[key] !== undefined) record[key] = input[key];
  }
  record.contract_verified = input.contract_verified === true;
  record.data_classes_sent = Array.isArray(input.data_classes_sent)
    ? input.data_classes_sent.map((item) => String(item))
    : [];
  return record;
}

export function appendOperatorWall(record) {
  const file = String(process.env.LUMOS_OPERATOR_WALL_PATH || "").trim();
  if (!file || !record) return record;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, `${JSON.stringify(record)}\n`);
  return record;
}
