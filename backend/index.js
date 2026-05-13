import crypto from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import helmet from "helmet";
import OpenAI from "openai";
import { PrismaClient, Prisma } from "@prisma/client";
import { LUMOS_CHAT_INSTRUCTIONS } from "./lumosInstructions.js";

/** Panel /chat: geçmiş boyutu ve içerik tavanı (token maliyetini sınırlar). */
const PANEL_CHAT_HISTORY_MAX_MESSAGES = 12;
const PANEL_CHAT_MAX_CONTENT_CHARS = 6000;

/**
 * İsteğe bağlı JSON gövdesindeki küçük görsel (base64) üst tavanı — ham bayt (decode sonrası).
 * Daha büyük dosyalarda panel yalnızca photo* metadata gönderir; görsel analiz yoktur.
 */
const PANEL_CHAT_IMAGE_INLINE_MAX_BYTES = 256 * 1024;

/**
 * @param {Record<string, unknown>} body
 * @returns {{
 *   photoAttached: boolean;
 *   photoName: string;
 *   photoType: string;
 *   photoSize: number | null;
 *   imageDataBase64: string | null;
 * }}
 */
function parsePanelChatPhotoFields(body) {
  const photoAttached = body?.photoAttached === true;
  const photoName =
    typeof body?.photoName === "string" ? body.photoName.slice(0, 2048) : "";
  const photoType =
    typeof body?.photoType === "string" ? body.photoType.slice(0, 256) : "";
  const rawSize = body?.photoSize;
  const photoSize =
    typeof rawSize === "number" && Number.isFinite(rawSize) && rawSize >= 0
      ? Math.min(Math.floor(rawSize), 1e12)
      : null;
  let imageDataBase64 = null;
  const raw = body?.imageData;
  if (typeof raw === "string") {
    let b64 = raw.trim();
    const dataUrl = /^data:image\/[^;]+;base64,(.+)$/is.exec(b64);
    if (dataUrl) b64 = dataUrl[1];
    b64 = b64.replace(/\s+/g, "");
    if (b64.length > 0) {
      try {
        const buf = Buffer.from(b64, "base64");
        if (buf.length > 0 && buf.length <= PANEL_CHAT_IMAGE_INLINE_MAX_BYTES) {
          imageDataBase64 = b64;
        }
      } catch {
        /* geçersiz base64 — yok say */
      }
    }
  }
  return { photoAttached, photoName, photoType, photoSize, imageDataBase64 };
}

/** Metin sohbeti: Responses API ile kullanılan model. */
const PANEL_CHAT_TEXT_MODEL = "gpt-5.5";
/**
 * gpt-5.5 bu uçta görsel (input_image) kabul etmediği için yalnızca fotoğraflı turlarda gpt-4o kullanılır.
 */
const PANEL_CHAT_VISION_MODEL = "gpt-4o";

/** Panel fotoğrafı: vision yok / hata / boş yanıtta dönülen sabit metin (istemci ile eşleşmeli). */
const REPLY_PHOTO_NO_VISION = "Fotoğraf eklendi; görsel analiz henüz aktif değil.";

/** POST /chat fotoğraf dalı sonucu; yalnızca bellek (GET /status ile okunur). */
let visionLastStatus = "not-tested";

const PANEL_CHAT_VISION_EMPTY_TEXT_PROMPT =
  "Bu görseli kısa yanıtla analiz et: önce ön plandaki ana konu, sonra arka plan bağlamı; teknik cihaz/parça ise netlik ve belirsizlikleri açıkça belirt; gerekirse bir sonraki faydalı çekim öner.";

/**
 * Panel fotoğrafı için data URL (Responses API input_image.image_url).
 * @param {string} photoType
 * @param {string} imageDataBase64
 */
function panelChatImageDataUrl(photoType, imageDataBase64) {
  const raw = String(photoType || "image/jpeg")
    .toLowerCase()
    .trim()
    .slice(0, 256);
  const mime = raw.startsWith("image/") ? raw : "image/jpeg";
  return `data:${mime};base64,${imageDataBase64}`;
}

/**
 * @param {string} currentText zaten trimlenmiş kullanıcı metni
 * @param {string} photoType
 * @param {string} imageDataBase64 saf base64
 */
function buildPanelChatVisionUserContent(currentText, photoType, imageDataBase64) {
  let textForModel = currentText;
  if (textForModel.length > PANEL_CHAT_MAX_CONTENT_CHARS) {
    textForModel = textForModel.slice(0, PANEL_CHAT_MAX_CONTENT_CHARS);
  }
  if (textForModel.length === 0) {
    textForModel = PANEL_CHAT_VISION_EMPTY_TEXT_PROMPT;
  }
  const imageUrl = panelChatImageDataUrl(photoType, imageDataBase64);
  return [
    { type: "input_text", text: textForModel },
    { type: "input_image", image_url: imageUrl },
  ];
}

/**
 * İstemciden gelen history dizisini güvenli biçimde { role, content } listesine indirger.
 * @param {unknown} raw
 * @returns {{ role: 'user' | 'assistant', content: string }[]}
 */
function normalizePanelChatHistory(raw) {
  if (!Array.isArray(raw)) return [];
  const cleaned = [];
  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const role = item.role;
    if (role !== "user" && role !== "assistant") continue;
    const c = item.content;
    if (typeof c !== "string") continue;
    const trimmed = c.trim();
    if (!trimmed) continue;
    const content =
      trimmed.length > PANEL_CHAT_MAX_CONTENT_CHARS
        ? trimmed.slice(0, PANEL_CHAT_MAX_CONTENT_CHARS)
        : trimmed;
    cleaned.push({ role, content });
  }
  if (cleaned.length > PANEL_CHAT_HISTORY_MAX_MESSAGES) {
    return cleaned.slice(-PANEL_CHAT_HISTORY_MAX_MESSAGES);
  }
  return cleaned;
}

/** OpenAI istemcisi; yalnızca OPENAI_API_KEY tanımlıyken oluşturulur. */
let openaiClient;
function getOpenAI() {
  const key = process.env.OPENAI_API_KEY;
  if (key == null || String(key).trim() === "") return null;
  if (!openaiClient) openaiClient = new OpenAI({ apiKey: key });
  return openaiClient;
}

const prisma = new PrismaClient();

/** Aynı user+post için kısa pencerede çok fazla yazmayı sınırlar (bellek içi, süreç bazlı) */
const RATING_BURST_WINDOW_MS = Number(process.env.RATING_BURST_WINDOW_MS || 10000);
const RATING_BURST_MAX = Math.max(1, Number(process.env.RATING_BURST_MAX || 3));
const ratingBurstTimestamps = new Map();

function ratingBurstKey(userId, postId) {
  return `${userId}:${postId}`;
}

function checkRatingBurst(userId, postId) {
  const key = ratingBurstKey(userId, postId);
  const now = Date.now();
  const cutoff = now - RATING_BURST_WINDOW_MS;
  const ts = (ratingBurstTimestamps.get(key) || []).filter((t) => t > cutoff);
  return ts.length < RATING_BURST_MAX;
}

function recordRatingBurst(userId, postId) {
  const key = ratingBurstKey(userId, postId);
  const now = Date.now();
  const cutoff = now - RATING_BURST_WINDOW_MS;
  let ts = (ratingBurstTimestamps.get(key) || []).filter((t) => t > cutoff);
  ts.push(now);
  ratingBurstTimestamps.set(key, ts);
}
const app = express();
app.get("/", (req, res) => {
  res.send("Lumos backend running");
});
// MIT; güvenlik başlıkları. CSP kapalı (JSON API); CORS ile uyum için CORP cross-origin.
app.use(
  helmet({
    contentSecurityPolicy: false,
    crossOriginResourcePolicy: { policy: "cross-origin" },
  })
);
/** CORS önce: gövde ayrıştırma hatası (ör. 413) yanıtlarında da ACAO gelsin; tarayıcı bunu aksi halde “CORS” sanır. */
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Kando-Token");
  if (req.method === "OPTIONS") return res.sendStatus(204);
  next();
});
/** Panel /chat: inline base64 (~256 KiB ham) + JSON sarmalayıcı; varsayılan 100kb altında 413 + sahte CORS. */
app.use(express.json({ limit: process.env.JSON_BODY_LIMIT || "1mb" }));

/** Sohbet köprüsü: Vercel UI’dan canlı bağlantı; OpenAI Responses API ile yanıt. */
app.post("/chat", async (req, res) => {
  try {
    const body = req.body && typeof req.body === "object" ? req.body : {};
    const photo = parsePanelChatPhotoFields(body);
    const message = body?.message;
    const currentText =
      typeof message === "string" ? message.trim() : String(message ?? "").trim();

    if (!currentText && !photo.photoAttached) {
      return res.status(400).json({ error: "message required" });
    }

    if (photo.photoAttached) {
      const mimeOk = String(photo.photoType || "")
        .toLowerCase()
        .startsWith("image/");
      if (mimeOk && photo.imageDataBase64) {
        const client = getOpenAI();
        if (!client) {
          visionLastStatus = "fallback";
          return res.json({ reply: REPLY_PHOTO_NO_VISION });
        }
        const historyMessages = normalizePanelChatHistory(body?.history);
        const visionUserContent = buildPanelChatVisionUserContent(
          currentText,
          photo.photoType,
          photo.imageDataBase64
        );
        const input =
          historyMessages.length === 0
            ? [{ role: "user", content: visionUserContent }]
            : [
                ...historyMessages.map((m) => ({ role: m.role, content: m.content })),
                { role: "user", content: visionUserContent },
              ];
        try {
          const response = await client.responses.create({
            model: PANEL_CHAT_VISION_MODEL,
            instructions: LUMOS_CHAT_INSTRUCTIONS,
            input,
          });
          const reply = response.output_text ?? "";
          const trimmed = String(reply).trim();
          if (trimmed && trimmed !== REPLY_PHOTO_NO_VISION) {
            visionLastStatus = "success";
          } else {
            visionLastStatus = "fallback";
          }
          return res.json({ reply });
        } catch {
          visionLastStatus = "error";
          return res.json({ reply: REPLY_PHOTO_NO_VISION });
        }
      }
      visionLastStatus = "fallback";
      return res.json({ reply: REPLY_PHOTO_NO_VISION });
    }

    const client = getOpenAI();
    if (!client) {
      return res.status(503).json({ error: "OPENAI_API_KEY missing" });
    }
    if (!currentText) {
      return res.status(400).json({ error: "message required" });
    }
    const historyMessages = normalizePanelChatHistory(body?.history);
    let userContent = currentText;
    if (userContent.length > PANEL_CHAT_MAX_CONTENT_CHARS) {
      userContent = userContent.slice(0, PANEL_CHAT_MAX_CONTENT_CHARS);
    }
    const input =
      historyMessages.length === 0
        ? userContent
        : [
            ...historyMessages.map((m) => ({ role: m.role, content: m.content })),
            { role: "user", content: userContent },
          ];
    const response = await client.responses.create({
      model: PANEL_CHAT_TEXT_MODEL,
      instructions: LUMOS_CHAT_INSTRUCTIONS,
      input,
    });
    const reply = response.output_text ?? "";
    res.json({ reply });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

const PORT = process.env.PORT || 8765;

/** Sağlık kontrolü: sunucu ayaktaysa 200. "Backend temel ayakta" = aşağıdaki checkpoint'lerin hepsi 200 dönmeli. */
const HEALTH_CHECKPOINTS = ["/posts?order=feed&limit=1", "/posts/rated-high", "/posts/rated-low"];
app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

/**
 * Panel "Sistem Durumu" için yan-etkisiz JSON. Anahtar sırrı dönmez (yalnızca var/yok).
 * `chat`: OpenAI anahtarı olsa da olmasa da "ok" — /chat rotası her zaman tanımlıdır (erişilebilirlik sinyali).
 */
app.get("/status", (req, res) => {
  const keyPresent =
    typeof process.env.OPENAI_API_KEY === "string"
    && process.env.OPENAI_API_KEY.trim().length > 0;
  res.json({
    health: "ok",
    chat: "ok",
    openaiKey: keyPresent ? "var" : "yok",
    visionConfigured: keyPresent,
    visionLastStatus,
    buildCommit:
      process.env.RENDER_GIT_COMMIT
      || process.env.VERCEL_GIT_COMMIT_SHA
      || process.env.GITHUB_SHA
      || null,
  });
});

const postUserInclude = {
  user: { select: { username: true } },
};

const emptyRatingStats = {
  ratingCount: 0,
  ratingAvg: null,
  lowRatingCount: 0,
  highRatingCount: 0,
};

/** @param {string[]} postIds */
async function getRatingStatsMap(postIds) {
  const map = new Map();
  if (postIds.length === 0) return map;
  const rows = await prisma.$queryRaw`
    SELECT
      "postId",
      COUNT(*) AS "ratingCount",
      AVG("value") AS "ratingAvg",
      SUM(CASE WHEN "value" IN (1, 2) THEN 1 ELSE 0 END) AS "lowRatingCount",
      SUM(CASE WHEN "value" IN (4, 5) THEN 1 ELSE 0 END) AS "highRatingCount"
    FROM "Rating"
    WHERE "postId" IN (${Prisma.join(postIds)})
    GROUP BY "postId"
  `;
  for (const r of rows) {
    map.set(r.postId, {
      ratingCount: Number(r.ratingCount),
      ratingAvg: r.ratingAvg != null ? Math.round(Number(r.ratingAvg) * 10) / 10 : null,
      lowRatingCount: Number(r.lowRatingCount),
      highRatingCount: Number(r.highRatingCount),
    });
  }
  return map;
}

function serializePost(p, statsMap) {
  const stats = statsMap.get(p.id) || emptyRatingStats;
  return { ...p, ...stats };
}

/** feedScore = taban + taze bonus − (yaşSaat × çarpan); avg zayıf, decay güçlü → daha “canlı” */
const FEED_AVG_MULTIPLIER = Number(process.env.FEED_AVG_MULTIPLIER || 1.2);
const FEED_TIME_DECAY_PER_H = Number(
  process.env.FEED_TIME_DECAY_PER_H || process.env.FEED_AGE_PENALTY_PER_H || 0.4
);
const FEED_FRESH_BOOST = Number(process.env.FEED_FRESH_BOOST || 3);
const FEED_FRESH_HOURS = Number(process.env.FEED_FRESH_HOURS || 2);

function computeFeedScore(post, stats, nowMs = Date.now()) {
  const ageInHours = Math.max(0, (nowMs - new Date(post.createdAt).getTime()) / 3600000);
  const avg = stats.ratingAvg != null ? stats.ratingAvg : 3;
  const base = avg * FEED_AVG_MULTIPLIER + Math.log(stats.ratingCount + 1);
  const freshBonus = ageInHours < FEED_FRESH_HOURS ? FEED_FRESH_BOOST : 0;
  const timeDecay = ageInHours * FEED_TIME_DECAY_PER_H;
  const score = base + freshBonus - timeDecay;
  return Math.round(score * 100) / 100;
}

function computePostsOrderFeedScore(post, stats, nowMs = Date.now()) {
  const ratingAvg = stats.ratingAvg;
  const ratingCount = stats.ratingCount ?? 0;
  const highRatingCount = stats.highRatingCount ?? 0;
  const lowRatingCount = stats.lowRatingCount ?? 0;
  const ageInHours = Math.max(0, (nowMs - new Date(post.createdAt).getTime()) / 3600000);
  const recency = 1 / (1 + ageInHours / 24);
  const safeRatingAvg = ratingAvg == null ? 3 : ratingAvg;

  const trustMultiplier =
    ratingCount <= 0
      ? 0.05
      : ratingCount === 1
      ? 0.2
      : ratingCount === 2
      ? 0.5
      : ratingCount === 3
      ? 0.7
      : ratingCount >= 5
      ? 1.0
      : 0.85;

  const volumeScore = Math.log(ratingCount + 1) * 2.2;
  const sentimentBalance = (highRatingCount - lowRatingCount) / Math.max(1, ratingCount);
  const sentimentScore = sentimentBalance * 5.5;
  let qualityScore = safeRatingAvg * 18 + volumeScore + sentimentScore;
  if (ratingCount === 0) qualityScore *= 0.1;

  const recencyBonus = recency * 6;
  const rawFreshBonus = ageInHours < FEED_FRESH_HOURS ? FEED_FRESH_BOOST * 0.8 : 0;
  const rawExplorationBonus = ratingCount < 2 ? 2.2 + recency * 1.6 : 0.4;
  let limitedFreshBonus = rawFreshBonus;
  let limitedExplorationBonus = rawExplorationBonus;
  if (ratingCount === 0) {
    limitedFreshBonus = Math.min(limitedFreshBonus, 1.5);
    limitedExplorationBonus = Math.min(limitedExplorationBonus, 1.5);
  } else if (ratingCount === 1) {
    limitedFreshBonus = Math.min(limitedFreshBonus, 2);
    limitedExplorationBonus = Math.min(limitedExplorationBonus, 2);
  }

  const timeDecay =
    FEED_TIME_DECAY_PER_H * (Math.log1p(ageInHours) * 2.1 + ageInHours * 0.08);

  let feedScore =
    qualityScore * trustMultiplier +
    recencyBonus +
    limitedFreshBonus +
    limitedExplorationBonus -
    timeDecay;
  if (ratingCount === 0) {
    feedScore = Math.max(feedScore, 0.01);
  }
  return feedScore;
}

/**
 * Feed skoru, kaliteyi güven katsayısı ile çarparak düşük oy hacimli postları doğal olarak geri iter.
 * ratingCount < 2 içerikler keşif amaçlı tutulur; bonusları sınırlıdır ve ana sıralamayı domine edemez.
 * Yaş etkisi log-eğrisiyle yumuşatılır; böylece kaliteli ama eski içerikler tamamen gömülmez.
 * Sonuçta feed, güvenilir içerik ağırlıklı kalırken kontrollü bir keşif bandı da korunur.
 */

function computePostsOrderFeedScoreBreakdown(post, stats, nowMs = Date.now()) {
  const ratingAvg = stats.ratingAvg;
  const ratingCount = stats.ratingCount ?? 0;
  const highRatingCount = stats.highRatingCount ?? 0;
  const lowRatingCount = stats.lowRatingCount ?? 0;
  const ageInHours = Math.max(0, (nowMs - new Date(post.createdAt).getTime()) / 3600000);
  const recency = 1 / (1 + ageInHours / 24);
  const safeRatingAvg = ratingAvg == null ? 3 : ratingAvg;

  const trustMultiplier =
    ratingCount <= 0
      ? 0.05
      : ratingCount === 1
      ? 0.2
      : ratingCount === 2
      ? 0.5
      : ratingCount === 3
      ? 0.7
      : ratingCount >= 5
      ? 1.0
      : 0.85;

  const volumeScore = Math.log(ratingCount + 1) * 2.2;
  const sentimentBalance = (highRatingCount - lowRatingCount) / Math.max(1, ratingCount);
  const sentimentScore = sentimentBalance * 5.5;
  let qualityScore = safeRatingAvg * 18 + volumeScore + sentimentScore;
  if (ratingCount === 0) qualityScore *= 0.1;

  const recencyBonus = recency * 6;
  const rawFreshBonus = ageInHours < FEED_FRESH_HOURS ? FEED_FRESH_BOOST * 0.8 : 0;
  const rawExplorationBonus = ratingCount < 2 ? 2.2 + recency * 1.6 : 0.4;
  let limitedFreshBonus = rawFreshBonus;
  let limitedExplorationBonus = rawExplorationBonus;
  if (ratingCount === 0) {
    limitedFreshBonus = Math.min(limitedFreshBonus, 1.5);
    limitedExplorationBonus = Math.min(limitedExplorationBonus, 1.5);
  } else if (ratingCount === 1) {
    limitedFreshBonus = Math.min(limitedFreshBonus, 2);
    limitedExplorationBonus = Math.min(limitedExplorationBonus, 2);
  }

  const timeDecay =
    FEED_TIME_DECAY_PER_H * (Math.log1p(ageInHours) * 2.1 + ageInHours * 0.08);
  const qualityWithTrust = qualityScore * trustMultiplier;
  const recencyScore = recencyBonus + limitedFreshBonus - timeDecay;
  let baseFinal = qualityWithTrust + recencyBonus + limitedFreshBonus + limitedExplorationBonus - timeDecay;
  if (ratingCount === 0) baseFinal *= 0.05;

  return {
    quality: qualityWithTrust,
    volume: volumeScore + sentimentScore,
    recency: recencyScore,
    exploration: limitedExplorationBonus,
    baseFinal,
  };
}

function computeColdStartBoost(post, stats, nowMs = Date.now()) {
  const ratingCount = stats.ratingCount ?? 0;
  if (ratingCount !== 0) return 0;
  const ageInHours = Math.max(0, (nowMs - new Date(post.createdAt).getTime()) / 3600000);
  const coldStartWindowHours = 1.5;
  if (ageInHours > coldStartWindowHours) return 0;
  const freshnessRatio = 1 - ageInHours / coldStartWindowHours;
  return Math.max(0, freshnessRatio) * 0.9;
}

function applyAuthorDiversity(feedItems, windowSize = 15) {
  const safeWindow = Math.max(1, windowSize);
  const head = feedItems.slice(0, safeWindow);
  const tail = feedItems.slice(safeWindow);
  const selected = [];
  const pool = [...head];
  while (pool.length > 0) {
    let bestIdx = 0;
    let bestAdjusted = -Infinity;
    for (let i = 0; i < pool.length; i++) {
      const item = pool[i];
      const authorId = item.post.userId || item.post.user?.username || item.post.id;
      const last = selected[selected.length - 1];
      const prev = selected[selected.length - 2];
      const lastAuthor = last ? last.post.userId || last.post.user?.username || last.post.id : null;
      const prevAuthor = prev ? prev.post.userId || prev.post.user?.username || prev.post.id : null;
      const ageMs = new Date(item.post.createdAt).getTime();
      let penalty = 0;
      if (lastAuthor && authorId === lastAuthor) penalty += 1.8;
      if (prevAuthor && authorId === prevAuthor) penalty += 0.9;
      if (last && lastAuthor && authorId === lastAuthor) {
        const lastAgeMs = new Date(last.post.createdAt).getTime();
        const deltaMinutes = Math.abs(ageMs - lastAgeMs) / 60000;
        if (deltaMinutes < 45) penalty += 0.5;
      }
      const adjusted = item.score - penalty;
      if (adjusted > bestAdjusted) {
        bestAdjusted = adjusted;
        bestIdx = i;
      }
    }
    selected.push(pool.splice(bestIdx, 1)[0]);
  }
  return [...selected, ...tail];
}

function composeFeedItems(trustedItems, lowTrustItems, windowSize = 20, trustedRatio = 0.85) {
  const limit = Math.max(1, windowSize);
  const explorationSlot = Math.max(1, Math.floor(limit * 0.15));
  const trustedQuota = limit - explorationSlot;
  const lowTrustQuota = explorationSlot;

  let finalResult = [
    ...trustedItems.slice(0, trustedQuota),
    ...lowTrustItems.slice(0, lowTrustQuota),
  ];

  if (finalResult.length < limit) {
    const missingTrusted = Math.max(0, trustedQuota - trustedItems.length);
    const missingLowTrust = Math.max(0, lowTrustQuota - lowTrustItems.length);

    if (missingTrusted > 0) {
      finalResult = [
        ...finalResult,
        ...lowTrustItems.slice(lowTrustQuota, lowTrustQuota + missingTrusted),
      ];
    }
    if (missingLowTrust > 0) {
      finalResult = [
        ...finalResult,
        ...trustedItems.slice(trustedQuota, trustedQuota + missingLowTrust),
      ];
    }

    if (finalResult.length < limit) {
      finalResult = [
        ...finalResult,
        ...trustedItems.slice(trustedQuota + missingLowTrust),
        ...lowTrustItems.slice(lowTrustQuota + missingTrusted),
      ].slice(0, limit);
    }
  }

  return finalResult;
}

/** Küçük kişiselleştirme skoru; explorationBonus'tan her zaman küçük (exploration>0 iken oranla sınırlı). */
function computePersonalBoost(post, stats, tasteProfile, nowMs = Date.now()) {
  if (!tasteProfile || stats.ratingAvg == null) return 0;
  const {
    tasteAvg,
    tasteRatingCountAvg,
    tasteSentiment,
    tasteEngagementAgeH,
    userRatingEntropy,
    userMeanRating,
    meanInterRatingHours,
  } = tasteProfile;
  const ratingCount = stats.ratingCount ?? 0;
  const ageInHours = Math.max(0, (nowMs - new Date(post.createdAt).getTime()) / 3600000);
  const recency = 1 / (1 + ageInHours / 24);
  const explorationBonus = ratingCount <= 1 ? recency * 1.2 : 0;

  const avgDiff = Math.abs(stats.ratingAvg - tasteAvg);
  const logP = Math.log(ratingCount + 1);
  const logT = Math.log(Math.max(0, tasteRatingCountAvg) + 1);
  const countDiff = Math.abs(logP - logT);

  const postSent = (stats.highRatingCount ?? 0) - (stats.lowRatingCount ?? 0);
  const sentDiff = Math.abs(postSent - tasteSentiment) / (10 + Math.abs(tasteSentiment));

  const logAgeP = Math.log(1 + ageInHours);
  const logAgeT = Math.log(1 + Math.max(0, tasteEngagementAgeH));
  const agePatternDiff = Math.abs(logAgeP - logAgeT) / 2.5;
  const agePatternWeight =
    0.4 * Math.min(1, 24 / ((meanInterRatingHours ?? 24) + 24));

  const personalBoostScale = Number(process.env.FEED_PERSONAL_BOOST_SCALE || 300);
  const personalBoostCap = Number(process.env.FEED_PERSONAL_BOOST_CAP || 230);

  let dist =
    3 * (avgDiff / 1.5) * (avgDiff / 1.5) +
    (countDiff / 3) * (countDiff / 3) +
    sentDiff * sentDiff * 0.45 +
    agePatternDiff * agePatternDiff * agePatternWeight;
  const ent = userRatingEntropy ?? 1;
  const focus = 0.85 + Math.min(0.35, Math.max(0, 1.61 - ent) * 0.25);
  dist *= focus;
  const leniency = Math.max(0, Math.min(1, ((userMeanRating ?? 3) - 2) / 3));
  dist /= 1 + leniency * 0.1;

  const sim = Math.exp(-dist);
  const rawBoost = sim * personalBoostScale;
  const explorationCap =
    explorationBonus > 0 ? explorationBonus * 90 + personalBoostCap * 0.35 : personalBoostCap;
  const qualityScore = stats.ratingAvg * 100;
  const qualityCapRatio = Number(process.env.FEED_PERSONAL_QUALITY_CAP_RATIO || 0.3);
  let boost = Math.min(rawBoost, explorationCap);
  boost = Math.min(boost, qualityScore * qualityCapRatio);
  return boost;
}

/** Basit CF: aynı postlara 4–5 veren kullanıcıların diğer yüksek oylarına küçük skor; personalBoost'tan düşük, kalite tavanı ile sınırlı. */
/** Komşu sinyali; taban skordaki volumeScore (ln(count+1)×40) ile yarışabilmeli — çok düşükse CF pratikte görünmez. */
const FEED_COLLAB_SCALE = Number(process.env.FEED_COLLAB_SCALE || 22);
const FEED_COLLAB_NEIGHBOR_CAP = Math.max(8, Number(process.env.FEED_COLLAB_NEIGHBOR_CAP || 40));
const FEED_COLLAB_ANCHOR_CAP = Math.max(5, Number(process.env.FEED_COLLAB_ANCHOR_CAP || 25));

async function loadCollaborativePostWeights(userId, candidatePostIds) {
  const out = new Map();
  if (candidatePostIds.length === 0) return out;

  const myRatings = await prisma.rating.findMany({
    where: { userId, value: { gte: 4 } },
    select: { postId: true, value: true },
    orderBy: { createdAt: "desc" },
    take: FEED_COLLAB_ANCHOR_CAP,
  });
  if (myRatings.length === 0) return out;

  const anchorIds = [...new Set(myRatings.map((r) => r.postId))];
  const anchorStrength = new Map();
  for (const r of myRatings) {
    const w = (r.value - 3) / 2;
    anchorStrength.set(r.postId, (anchorStrength.get(r.postId) || 0) + w);
  }

  const anchorNeighborRatings = await prisma.rating.findMany({
    where: { postId: { in: anchorIds }, userId: { not: userId }, value: { gte: 4 } },
    select: { userId: true, postId: true, value: true },
  });
  const matchWByUser = new Map();
  for (const r of anchorNeighborRatings) {
    const aw = anchorStrength.get(r.postId) || 0;
    const add = ((r.value - 3) / 2) * aw;
    matchWByUser.set(r.userId, (matchWByUser.get(r.userId) || 0) + add);
  }
  const neighborIds = [...matchWByUser.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, FEED_COLLAB_NEIGHBOR_CAP)
    .map(([uid]) => uid);
  if (neighborIds.length === 0) return out;

  const myAnyPostIds = (
    await prisma.rating.findMany({
      where: { userId },
      select: { postId: true },
      distinct: ["postId"],
    })
  ).map((r) => r.postId);
  const myRated = new Set(myAnyPostIds);

  const candSet = new Set(candidatePostIds);
  const neighborHigh = await prisma.rating.findMany({
    where: {
      userId: { in: neighborIds },
      value: { gte: 4 },
      postId: { in: candidatePostIds },
    },
    select: { postId: true, value: true, userId: true },
  });

  for (const r of neighborHigh) {
    if (myRated.has(r.postId)) continue;
    if (!candSet.has(r.postId)) continue;
    const nw = matchWByUser.get(r.userId) || 0;
    const valW = (r.value - 3) / 2;
    const add = nw * valW * FEED_COLLAB_SCALE;
    out.set(r.postId, (out.get(r.postId) || 0) + add);
  }

  return out;
}

function computeCollaborativeBoost(post, stats, collabMap, personalBoost) {
  if (!collabMap || stats.ratingAvg == null) return 0;
  const raw = collabMap.get(post.id);
  if (raw == null || raw <= 0) return 0;

  const qualityScore = stats.ratingAvg * 100;
  const qualityCapRatio = Number(process.env.FEED_PERSONAL_QUALITY_CAP_RATIO || 0.3);

  const headroom = Math.max(0, qualityScore * qualityCapRatio - personalBoost);
  if (headroom <= 0) return 0;

  const vsPersonal =
    personalBoost > 0 ? personalBoost * 0.45 : qualityScore * qualityCapRatio * 0.2;
  return Math.round(Math.min(raw, vsPersonal, headroom) * 1000) / 1000;
}

async function loadUserFeedTasteProfile(userId) {
  const ratings = await prisma.rating.findMany({
    where: { userId },
    select: { postId: true, value: true, createdAt: true },
    orderBy: { createdAt: "asc" },
  });
  if (ratings.length === 0) return null;
  const uniqueIds = [...new Set(ratings.map((r) => r.postId))];
  const posts = await prisma.post.findMany({
    where: { id: { in: uniqueIds }, deletedAt: null },
    select: { id: true, createdAt: true },
  });
  const postById = new Map(posts.map((p) => [p.id, p]));
  if (postById.size === 0) return null;
  const aliveIds = posts.map((p) => p.id);
  const statsMap = await getRatingStatsMap(aliveIds);

  const hist = [0, 0, 0, 0, 0];
  const times = [];
  let wSum = 0;
  let sumAvg = 0;
  let sumCnt = 0;
  let sumSent = 0;
  let sumEngAge = 0;

  for (const r of ratings) {
    const p = postById.get(r.postId);
    if (!p) continue;
    times.push(new Date(r.createdAt).getTime());
    const vi = r.value - 1;
    if (vi >= 0 && vi < 5) hist[vi] += 1;

    const st = statsMap.get(r.postId);
    if (!st || st.ratingAvg == null) continue;
    const affinity = Math.max(0, (r.value - 2) / 3);
    if (affinity <= 0) continue;
    sumAvg += affinity * st.ratingAvg;
    sumCnt += affinity * st.ratingCount;
    sumSent += affinity * ((st.highRatingCount ?? 0) - (st.lowRatingCount ?? 0));
    sumEngAge +=
      affinity *
      Math.max(0, (new Date(r.createdAt).getTime() - new Date(p.createdAt).getTime()) / 3600000);
    wSum += affinity;
  }

  if (wSum === 0) return null;

  const totalH = hist.reduce((a, b) => a + b, 0);
  let entropy = 0;
  if (totalH > 0) {
    for (const c of hist) {
      if (c === 0) continue;
      const pp = c / totalH;
      entropy -= pp * Math.log(pp + 1e-12);
    }
  }

  let meanInterRatingHours = 0;
  if (times.length >= 2) {
    times.sort((a, b) => a - b);
    let gapSum = 0;
    for (let i = 1; i < times.length; i++) gapSum += (times[i] - times[i - 1]) / 3600000;
    meanInterRatingHours = gapSum / (times.length - 1);
  }

  return {
    tasteAvg: sumAvg / wSum,
    tasteRatingCountAvg: sumCnt / wSum,
    tasteSentiment: sumSent / wSum,
    tasteEngagementAgeH: sumEngAge / wSum,
    userMeanRating:
      totalH > 0
        ? (hist[0] + 2 * hist[1] + 3 * hist[2] + 4 * hist[3] + 5 * hist[4]) / totalH
        : 3,
    userRatingEntropy: entropy,
    meanInterRatingHours,
  };
}

async function postsWithRatings(where, orderBy) {
  const posts = await prisma.post.findMany({
    where,
    include: postUserInclude,
    orderBy,
  });
  const ids = posts.map((p) => p.id);
  const statsMap = await getRatingStatsMap(ids);
  return posts.map((p) => serializePost(p, statsMap));
}

/** rated-high / rated-low: sırayı koruyarak post + rating özetleri */
async function orderedPostsWithRatingStats(postIds) {
  const posts = await prisma.post.findMany({
    where: { id: { in: postIds }, deletedAt: null },
    include: postUserInclude,
  });
  const statsMap = await getRatingStatsMap(postIds);
  const byId = new Map(posts.map((p) => [p.id, p]));
  return postIds.map((id) => byId.get(id)).filter(Boolean).map((p) => serializePost(p, statsMap));
}

// --- Users ---
app.post("/users", async (req, res) => {
  try {
    const { username } = req.body;
    if (!username) return res.status(400).json({ error: "username required" });
    const ratingToken = crypto.randomBytes(32).toString("hex");
    const user = await prisma.user.create({ data: { username, ratingToken } });
    res.status(201).json(user);
  } catch (e) {
    if (e.code === "P2002") return res.status(409).json({ error: "username taken" });
    res.status(500).json({ error: e.message });
  }
});

// --- Posts: create ---
app.post("/posts", async (req, res) => {
  try {
    const { content, userId, username } = req.body;
    let normalizedContent = content;
    if (typeof normalizedContent === "string") normalizedContent = normalizedContent.trim();
    if (!normalizedContent) return res.status(400).json({ error: "content required" });
    let normalizedUsername = username;
    if (typeof normalizedUsername === "string") normalizedUsername = normalizedUsername.trim();
    if (normalizedUsername === "") normalizedUsername = undefined;
    const hasUserId = userId !== undefined && userId !== null && userId !== "";
    if (!hasUserId && !normalizedUsername) {
      return res.status(400).json({ error: "userId or username required" });
    }

    let user;
    if (hasUserId) {
      user = await prisma.user.findUnique({ where: { id: userId } });
      if (!user) return res.status(400).json({ error: "invalid userId" });
    } else {
      user = await prisma.user.findUnique({ where: { username: normalizedUsername } });
      if (!user) {
        const ratingToken = crypto.randomBytes(32).toString("hex");
        try {
          user = await prisma.user.create({ data: { username: normalizedUsername, ratingToken } });
        } catch (e) {
          if (e.code === "P2002") {
            user = await prisma.user.findUnique({ where: { username: normalizedUsername } });
          }
          if (!user) throw e;
        }
      }
    }

    const post = await prisma.post.create({
      data: { content: normalizedContent, userId: user.id },
      include: postUserInclude,
    });
    const statsMap = await getRatingStatsMap([post.id]);
    res.status(201).json(serializePost(post, statsMap));
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

async function handleRatedHigh(req, res) {
  try {
    const minVotes = Math.max(1, parseInt(String(req.query.minVotes || "1"), 10) || 1);
    const limit = Math.min(100, Math.max(1, parseInt(String(req.query.limit || "50"), 10) || 50));

    const rows = await prisma.$queryRaw`
      SELECT r."postId",
        COUNT(*) AS "ratingCount",
        AVG(r."value") AS "ratingAvg"
      FROM "Rating" r
      INNER JOIN "Post" p ON p.id = r."postId" AND p."deletedAt" IS NULL
      GROUP BY r."postId"
      HAVING COUNT(*) >= ${minVotes}
      ORDER BY AVG(r."value") DESC, COUNT(*) DESC
      LIMIT ${limit}
    `;

    const postIds = rows.map((r) => r.postId);
    if (postIds.length === 0) return res.json([]);
    res.json(await orderedPostsWithRatingStats(postIds));
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}

// --- Posts: rated-high (yüksek ortalama) ---
app.get("/posts/rated-high", handleRatedHigh);
// Alias: farklı yazım kullanan istemcilerde 404 olmasın.
app.get("/posts/rated_high", handleRatedHigh);

async function handleRatedLow(req, res) {
  try {
    const minVotes = Math.max(2, parseInt(String(req.query.minVotes || "2"), 10) || 2);
    const limit = Math.min(100, Math.max(1, parseInt(String(req.query.limit || "50"), 10) || 50));

    const rows = await prisma.$queryRaw`
      SELECT
        r."postId",
        COUNT(*) AS "ratingCount",
        SUM(CASE WHEN r."value" IN (1, 2) THEN 1 ELSE 0 END) AS "lowRatingCount"
      FROM "Rating" r
      INNER JOIN "Post" p ON p.id = r."postId" AND p."deletedAt" IS NULL
      GROUP BY r."postId"
      HAVING COUNT(*) >= ${minVotes}
      ORDER BY
        (CAST(SUM(CASE WHEN r."value" IN (1, 2) THEN 1 ELSE 0 END) AS REAL) / COUNT(*)) DESC,
        SUM(CASE WHEN r."value" IN (1, 2) THEN 1 ELSE 0 END) DESC
      LIMIT ${limit}
    `;

    const postIds = rows.map((r) => r.postId);
    if (postIds.length === 0) return res.json([]);
    res.json(await orderedPostsWithRatingStats(postIds));
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}

// --- Posts: rated-low (1–2★ yoğunluğu) ---
app.get("/posts/rated-low", handleRatedLow);
// Alias: farklı yazım kullanan istemcilerde 404 olmasın.
app.get("/posts/rated_low", handleRatedLow);

// --- Posts: feed (deprecated → GET /posts?order=feed) ---
app.get("/posts/feed", (req, res) => {
  res.status(410).json({ error: "deprecated", message: "use /posts?order=feed" });
});

// --- Posts: list (silinmemişler, createdAt desc) ---
app.get("/posts", async (req, res) => {
  try {
    const rawLimit = req.query.limit;
    const rawLimitValue = Array.isArray(rawLimit) ? rawLimit[0] : rawLimit;
    let limit;
    if (rawLimitValue !== undefined) {
      const n = Number(rawLimitValue);
      if (Number.isFinite(n) && Number.isInteger(n) && n >= 0) limit = n;
    }
    const rawOffset = req.query.offset;
    const rawOffsetValue = Array.isArray(rawOffset) ? rawOffset[0] : rawOffset;
    let offset;
    if (rawOffsetValue !== undefined) {
      const n = Number(rawOffsetValue);
      if (Number.isFinite(n) && Number.isInteger(n) && n >= 0) offset = n;
    }
    const rawOrder = req.query.order;
    const rawOrderValue = Array.isArray(rawOrder) ? rawOrder[0] : rawOrder;
    const rawDebug = req.query.debug;
    const rawDebugValue = Array.isArray(rawDebug) ? rawDebug[0] : rawDebug;
    const shouldIncludeFeedDebugScores = rawOrderValue === "feed" && String(rawDebugValue) === "1";
    const rawUsername = req.query.username;
    const rawUsernameValue = Array.isArray(rawUsername) ? rawUsername[0] : rawUsername;
    let normalizedUsername = rawUsernameValue;
    if (typeof normalizedUsername === "string") normalizedUsername = normalizedUsername.trim();
    if (normalizedUsername === "") normalizedUsername = undefined;

    const rawFields = req.query.fields;
    const rawFieldsValue = Array.isArray(rawFields) ? rawFields[0] : rawFields;
    const allowedFields = new Set(["id", "content", "createdAt", "user", "ratingAvg", "ratingCount"]);
    const requestedFields =
      typeof rawFieldsValue === "string"
        ? rawFieldsValue
            .split(",")
            .map((s) => s.trim())
            .filter((s) => allowedFields.has(s))
        : null;
    const normalizedRequestedFields = requestedFields && requestedFields.length > 0 ? requestedFields : null;

    const rawMinRating = req.query.minRating;
    const rawMinRatingValue = Array.isArray(rawMinRating) ? rawMinRating[0] : rawMinRating;
    let minRating;
    if (rawMinRatingValue !== undefined) {
      const n = Number(rawMinRatingValue);
      if (Number.isFinite(n)) minRating = n;
    }

    let where = { deletedAt: null };
    if (normalizedUsername) {
      const user = await prisma.user.findUnique({ where: { username: normalizedUsername } });
      if (!user) return res.json([]);
      where = { ...where, userId: user.id };
    }
    const shouldUseFields = normalizedRequestedFields !== null;
    const posts = await prisma.post.findMany({
      where,
      ...(shouldUseFields
        ? {
            select: {
              id: true,
              ...(normalizedRequestedFields.includes("content") ? { content: true } : {}),
              ...(normalizedRequestedFields.includes("createdAt") ? { createdAt: true } : {}),
              ...(normalizedRequestedFields.includes("user") ? { user: postUserInclude.user } : {}),
            },
          }
        : { include: postUserInclude }),
    });
    const statsMap = await getRatingStatsMap(posts.map((p) => p.id));
    const filteredPosts =
      minRating === undefined
        ? posts
        : posts.filter((p) => {
            const st = statsMap.get(p.id) || emptyRatingStats;
            return st.ratingAvg != null && st.ratingAvg >= minRating;
          });
    const nowMs = Date.now();
    let feedTasteProfile = null;
    let feedAuthUserId = null;
    /** Oylanmış postlara tekrar “taste” boost’u vermeyelim; aksi halde CF komşu önerisi (henüz oylanmamış) ile yarışamaz. */
    let feedRatedPostIds = new Set();
    if (rawOrderValue === "feed") {
      const auth = req.headers.authorization;
      if (auth && typeof auth === "string" && auth.startsWith("Bearer ")) {
        const token = auth.slice(7).trim();
        if (token) {
          const authUser = await prisma.user.findUnique({ where: { ratingToken: token } });
          if (authUser) {
            feedAuthUserId = authUser.id;
            feedTasteProfile = await loadUserFeedTasteProfile(authUser.id);
            const ratedRows = await prisma.rating.findMany({
              where: { userId: authUser.id },
              select: { postId: true },
              distinct: ["postId"],
            });
            feedRatedPostIds = new Set(ratedRows.map((r) => r.postId));
          }
        }
      }
    }
    let collabMap = null;
    if (rawOrderValue === "feed" && feedAuthUserId) {
      collabMap = await loadCollaborativePostWeights(
        feedAuthUserId,
        filteredPosts.map((p) => p.id)
      );
    }
    let sortedPosts;
    if (rawOrderValue === "feed") {
      const trustedMinRatingCount = 2;
      const feedWindowSize = Math.max(1, limit ?? 20);
      const feedItems = filteredPosts.map((p) => {
        const stats = statsMap.get(p.id) || emptyRatingStats;
        const normalizedPost = {
          ...p,
          createdAt: p.createdAt || new Date(nowMs).toISOString(),
        };
        let score = computePostsOrderFeedScore(normalizedPost, stats, nowMs);
        const personal =
          feedTasteProfile && !feedRatedPostIds.has(p.id)
            ? computePersonalBoost(normalizedPost, stats, feedTasteProfile, nowMs)
            : 0;
        score += personal;
        if (collabMap && collabMap.size > 0) {
          score += computeCollaborativeBoost(normalizedPost, stats, collabMap, personal);
        }
        const coldStartBoost = computeColdStartBoost(normalizedPost, stats, nowMs);
        return {
          post: p,
          score,
          ratingCount: stats.ratingCount ?? 0,
          coldStartBoost,
        };
      });
      const compareFeedItems = (a, b) => {
        const aSortScore = a.score + (a.ratingCount < trustedMinRatingCount ? a.coldStartBoost : 0);
        const bSortScore = b.score + (b.ratingCount < trustedMinRatingCount ? b.coldStartBoost : 0);
        if (bSortScore !== aSortScore) return bSortScore - aSortScore;
        return new Date(b.post.createdAt).getTime() - new Date(a.post.createdAt).getTime();
      };
      const sortedFeedItems = feedItems.sort(compareFeedItems);
      const trustedItems = applyAuthorDiversity(
        sortedFeedItems.filter((x) => x.ratingCount >= trustedMinRatingCount),
        Math.min(feedWindowSize, 15)
      );
      const lowTrustItems = sortedFeedItems.filter((x) => x.ratingCount < trustedMinRatingCount);
      const orderedItems = composeFeedItems(trustedItems, lowTrustItems, feedWindowSize, 0.85);
      sortedPosts = orderedItems.map((x) => x.post);
    } else {
      sortedPosts = [...filteredPosts].sort((a, b) => {
        if (rawOrderValue === "ratingAvg:desc") {
        const aStats = statsMap.get(a.id) || emptyRatingStats;
        const bStats = statsMap.get(b.id) || emptyRatingStats;
        return (bStats.ratingAvg ?? -1) - (aStats.ratingAvg ?? -1);
        }
        const aCreatedAt = new Date(a.createdAt).getTime();
        const bCreatedAt = new Date(b.createdAt).getTime();
        if (rawOrderValue === "asc") return aCreatedAt - bCreatedAt;
        return bCreatedAt - aCreatedAt;
      });
    }
    let pagedPosts = sortedPosts;
    if (offset) pagedPosts = pagedPosts.slice(offset);
    if (limit) pagedPosts = pagedPosts.slice(0, limit);
    const list = pagedPosts.map((p) => {
      const serialized = serializePost(p, statsMap);
      const stats = statsMap.get(p.id) || emptyRatingStats;
      const normalizedPost = {
        ...p,
        createdAt: p.createdAt || new Date(nowMs).toISOString(),
      };
      const scoreBreakdown = shouldIncludeFeedDebugScores
        ? computePostsOrderFeedScoreBreakdown(normalizedPost, stats, nowMs)
        : null;
      const personalScore =
        shouldIncludeFeedDebugScores && feedTasteProfile && !feedRatedPostIds.has(p.id)
          ? computePersonalBoost(normalizedPost, stats, feedTasteProfile, nowMs)
          : 0;
      const collaborativeScore =
        shouldIncludeFeedDebugScores && collabMap && collabMap.size > 0
          ? computeCollaborativeBoost(normalizedPost, stats, collabMap, personalScore)
          : 0;
      if (!shouldUseFields) {
        if (!shouldIncludeFeedDebugScores) return serialized;
        return {
          ...serialized,
          _scoreQuality: Math.round(scoreBreakdown.quality * 1000) / 1000,
          _scoreVolume: Math.round(scoreBreakdown.volume * 1000) / 1000,
          _scoreRecency: Math.round(scoreBreakdown.recency * 1000) / 1000,
          _scoreExploration: Math.round(scoreBreakdown.exploration * 1000) / 1000,
          _scorePersonal: Math.round(personalScore * 1000) / 1000,
          _scoreCollaborative: Math.round(collaborativeScore * 1000) / 1000,
          _scoreFinal:
            Math.round((scoreBreakdown.baseFinal + personalScore + collaborativeScore) * 1000) / 1000,
        };
      }
      const out = {};
      if (normalizedRequestedFields.includes("id")) out.id = serialized.id;
      if (normalizedRequestedFields.includes("content")) out.content = serialized.content;
      if (normalizedRequestedFields.includes("createdAt")) out.createdAt = serialized.createdAt;
      if (normalizedRequestedFields.includes("user")) out.user = serialized.user;
      if (normalizedRequestedFields.includes("ratingAvg")) out.ratingAvg = serialized.ratingAvg;
      if (normalizedRequestedFields.includes("ratingCount")) out.ratingCount = serialized.ratingCount;
      if (shouldIncludeFeedDebugScores) {
        out._scoreQuality = Math.round(scoreBreakdown.quality * 1000) / 1000;
        out._scoreVolume = Math.round(scoreBreakdown.volume * 1000) / 1000;
        out._scoreRecency = Math.round(scoreBreakdown.recency * 1000) / 1000;
        out._scoreExploration = Math.round(scoreBreakdown.exploration * 1000) / 1000;
        out._scorePersonal = Math.round(personalScore * 1000) / 1000;
        out._scoreCollaborative = Math.round(collaborativeScore * 1000) / 1000;
        out._scoreFinal =
          Math.round((scoreBreakdown.baseFinal + personalScore + collaborativeScore) * 1000) / 1000;
      }
      return out;
    });
    res.json(list);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// --- Soft delete / trash / restore ---
app.delete("/posts/trash", async (req, res) => {
  try {
    const deleted = await prisma.post.deleteMany({
      where: { deletedAt: { not: null } },
    });
    res.json({ ok: true, deletedCount: deleted.count });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.delete("/posts/:id", async (req, res) => {
  try {
    // "trash" yanlışlıkla :id olarak yakalanırsa (route sırası / eski süreç) toplu boşalt ile aynı davranış
    if (String(req.params.id) === "trash") {
      const deleted = await prisma.post.deleteMany({
        where: { deletedAt: { not: null } },
      });
      return res.json({ ok: true, deletedCount: deleted.count });
    }
    // Permanent delete sadece trash/deleted postlar için geçerli.
    const deleted = await prisma.post.deleteMany({
      where: { id: req.params.id, deletedAt: { not: null } },
    });
    if (deleted.count === 0) {
      return res.status(404).json({ error: "post not found in trash" });
    }
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get("/posts/trash", async (req, res) => {
  try {
    const list = await postsWithRatings({ deletedAt: { not: null } }, { deletedAt: "desc" });
    res.json(list);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

async function restorePostHandler(req, res) {
  try {
    const post = await prisma.post.updateMany({
      where: { id: req.params.id, deletedAt: { not: null } },
      data: { deletedAt: null },
    });
    if (post.count === 0) return res.status(404).json({ error: "post not found or not deleted" });
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}

app.post("/posts/:id/restore", restorePostHandler);
app.patch("/posts/:id/restore", restorePostHandler);

async function createPanelRatingActor() {
  const suffix = crypto.randomBytes(6).toString("hex");
  const username = `panel_rater_${Date.now()}_${suffix}`;
  const ratingToken = crypto.randomBytes(32).toString("hex");
  return prisma.user.create({
    data: { username, ratingToken },
    select: { id: true },
  });
}

async function createQuickRating(req, res, value) {
  const postId = req.params.id;
  if (!Number.isInteger(value) || value < 1 || value > 5) {
    return res.status(400).json({ error: "invalid rating value" });
  }
  const post = await prisma.post.findFirst({ where: { id: postId, deletedAt: null } });
  if (!post) return res.status(404).json({ error: "post not found" });
  const actor = await createPanelRatingActor();
  await prisma.rating.create({
    data: {
      userId: actor.id,
      postId,
      value,
    },
  });
  const statsMap = await getRatingStatsMap([postId]);
  const stats = statsMap.get(postId) || emptyRatingStats;
  return res.json({ ok: true, ...stats });
}

app.post("/posts/:id/rate-high", async (req, res) => {
  try {
    return await createQuickRating(req, res, 5);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
});

app.post("/posts/:id/rate-low", async (req, res) => {
  try {
    return await createQuickRating(req, res, 1);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
});

app.post("/posts/:id/trash", async (req, res) => {
  try {
    const existing = await prisma.post.findUnique({
      where: { id: req.params.id },
      include: postUserInclude,
    });
    if (!existing) return res.status(404).json({ error: "post not found" });
    if (existing.deletedAt != null) {
      return res.status(409).json({ error: "post already in trash" });
    }
    const updated = await prisma.post.update({
      where: { id: req.params.id },
      data: { deletedAt: new Date() },
      include: postUserInclude,
    });
    const statsMap = await getRatingStatsMap([updated.id]);
    return res.json({
      ok: true,
      post: serializePost(updated, statsMap),
    });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
});

// --- Rate post (1–5); Bearer <ratingToken>; body’de userId yok ---
const RATE_ENDPOINT_COOLDOWN_MS = Number(process.env.RATE_ENDPOINT_COOLDOWN_MS || 5000);
const RATE_ENDPOINT_VELOCITY_WINDOW_MS = Number(
  process.env.RATE_ENDPOINT_VELOCITY_WINDOW_MS || 10000
);
const RATE_ENDPOINT_VELOCITY_MAX = Number(process.env.RATE_ENDPOINT_VELOCITY_MAX || 5);

app.post("/posts/:id/rate", async (req, res) => {
  try {
    const body = req.body || {};
    if (body.userId != null) {
      return res.status(400).json({
        error: "userId in body is not accepted; use Authorization: Bearer <ratingToken> from POST /users",
      });
    }
    const auth = req.headers.authorization;
    if (!auth || typeof auth !== "string" || !auth.startsWith("Bearer ")) {
      return res.status(401).json({ error: "Authorization: Bearer <ratingToken> required" });
    }
    const token = auth.slice(7).trim();
    if (!token) return res.status(401).json({ error: "missing Bearer token" });

    const { value } = body;
    const postId = req.params.id;
    const v = Number(value);

    if (!Number.isInteger(v) || v < 1 || v > 5) {
      return res.status(400).json({ error: "value must be integer 1–5" });
    }

    const post = await prisma.post.findFirst({
      where: { id: postId, deletedAt: null },
    });
    if (!post) return res.status(404).json({ error: "post not found" });

    const user = await prisma.user.findUnique({ where: { ratingToken: token } });
    if (!user || !user.ratingToken) return res.status(401).json({ error: "invalid or expired rating token" });

    const userId = user.id;
    const windowStart = new Date(Date.now() - RATE_ENDPOINT_VELOCITY_WINDOW_MS);
    const recentRatingsCount = await prisma.rating.count({
      where: {
        postId,
        createdAt: {
          gte: windowStart,
        },
      },
    });
    if (recentRatingsCount >= RATE_ENDPOINT_VELOCITY_MAX) {
      return res.status(429).json({ error: "Rate limit exceeded" });
    }

    const lastRating = await prisma.rating.findFirst({
      where: {
        userId,
        postId,
      },
      orderBy: {
        createdAt: "desc",
      },
    });

    if (lastRating) {
      const diff = Date.now() - new Date(lastRating.createdAt).getTime();
      if (diff < RATE_ENDPOINT_COOLDOWN_MS) {
        return res.status(429).json({ error: "Too fast" });
      }
    }

    if (!checkRatingBurst(user.id, postId)) {
      return res.status(429).json({
        error: "too many rating updates for this post; try again later",
      });
    }

    let rating = await prisma.rating.findFirst({
      where: { userId: user.id, postId },
      orderBy: { createdAt: "desc" },
    });
    if (rating) {
      rating = await prisma.rating.update({
        where: { id: rating.id },
        data: { value: v },
      });
    } else {
      rating = await prisma.rating.create({
        data: { userId: user.id, postId, value: v },
      });
    }
    recordRatingBurst(user.id, postId);

    const statsMap = await getRatingStatsMap([postId]);
    const stats = statsMap.get(postId) || emptyRatingStats;
    res.json({ rating, ...stats });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

function startServer() {
  return app.listen(PORT, "0.0.0.0", () => console.log(`Server running at http://localhost:${PORT}`));
}

const isMainProcess =
  process.argv[1] &&
  path.resolve(fileURLToPath(import.meta.url)) === path.resolve(process.argv[1]);
if (isMainProcess) startServer();

export {
  app,
  prisma,
  startServer,
  computePersonalBoost,
  loadUserFeedTasteProfile,
  getRatingStatsMap,
};
