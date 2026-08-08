export class RawBodyTooLargeError extends Error {
  constructor() {
    super("raw_body_too_large");
  }
}

function asBuffer(value) {
  if (Buffer.isBuffer(value)) return value;
  if (value instanceof Uint8Array) return Buffer.from(value);
  if (typeof value === "string") return Buffer.from(value, "utf8");
  return null;
}

function bounded(chunks, chunk, size, maxBytes) {
  const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
  const nextSize = size + buffer.length;
  if (nextSize > maxBytes) throw new RawBodyTooLargeError();
  chunks.push(buffer);
  return nextSize;
}

export async function readBoundedRawBody(req, maxBytes) {
  const limit = Number(maxBytes);
  if (!Number.isSafeInteger(limit) || limit < 1) throw new Error("raw_body_limit_invalid");

  const preloaded = asBuffer(req?.body);
  if (preloaded) {
    if (preloaded.length > limit) throw new RawBodyTooLargeError();
    return preloaded;
  }

  const chunks = [];
  let size = 0;
  if (req?.[Symbol.asyncIterator]) {
    for await (const chunk of req) size = bounded(chunks, chunk, size, limit);
    return Buffer.concat(chunks, size);
  }

  if (typeof req?.on === "function") {
    return await new Promise((resolve, reject) => {
      let settled = false;
      req.on("data", (chunk) => {
        if (settled) return;
        try {
          size = bounded(chunks, chunk, size, limit);
        } catch (error) {
          settled = true;
          reject(error);
        }
      });
      req.on("end", () => {
        if (!settled) resolve(Buffer.concat(chunks, size));
      });
      req.on("error", (error) => {
        if (!settled) reject(error);
      });
    });
  }
  return Buffer.alloc(0);
}
