const crypto = require("crypto");
const express = require("express");
const helmet = require("helmet");
const { PrismaClient, Prisma } = require("@prisma/client");

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
// MIT; güvenlik başlıkları. CSP kapalı (JSON API); CORS ile uyum için CORP cross-origin.
app.use(
  helmet({
    contentSecurityPolicy: false,
    crossOriginResourcePolicy: { policy: "cross-origin" },
  })
);
app.use(express.json());
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  if (req.method === "OPTIONS") return res.sendStatus(204);
  next();
});

const PORT = process.env.PORT || 3000;

/** Sağlık kontrolü: sunucu ayaktaysa 200. "Backend temel ayakta" = aşağıdaki checkpoint'lerin hepsi 200 dönmeli. */
const HEALTH_CHECKPOINTS = ["/posts/feed", "/posts/rated-high", "/posts/rated-low"];
app.get("/health", (req, res) => {
  res.json({ status: "ok" });
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
  if (ratingAvg == null) return -1000000 + recency;

  const qualityScore = ratingAvg * FEED_AVG_MULTIPLIER;
  const volumeScore = Math.log(ratingCount + 1);
  const sentimentScore = highRatingCount * 0.6 - lowRatingCount * 0.8;
  const freshBonus = ageInHours < FEED_FRESH_HOURS ? FEED_FRESH_BOOST : 0;
  const timeDecay = ageInHours * FEED_TIME_DECAY_PER_H;

  return qualityScore + volumeScore + sentimentScore + freshBonus + recency - timeDecay;
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

// --- Posts: rated-high (yüksek ortalama) ---
app.get("/posts/rated-high", async (req, res) => {
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
});

// --- Posts: rated-low (1–2★ yoğunluğu) ---
app.get("/posts/rated-low", async (req, res) => {
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
});

// --- Posts: feed (skor: ortalama + oy sayısı + tazelik − yaş çürümesi) ---
app.get("/posts/feed", async (req, res) => {
  try {
    const limit = Math.min(100, Math.max(1, parseInt(String(req.query.limit || "50"), 10) || 50));
    const posts = await prisma.post.findMany({
      where: { deletedAt: null },
      include: postUserInclude,
    });
    const statsMap = await getRatingStatsMap(posts.map((p) => p.id));
    const now = Date.now();
    const rows = posts.map((p) => {
      const base = serializePost(p, statsMap);
      const st = statsMap.get(p.id) || emptyRatingStats;
      const feedScore = computeFeedScore(p, st, now);
      return { ...base, feedScore };
    });
    rows.sort((a, b) => b.feedScore - a.feedScore);
    res.json(rows.slice(0, limit));
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
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
    const sortedPosts = [...filteredPosts].sort((a, b) => {
      if (rawOrderValue === "feed") {
        const aStats = statsMap.get(a.id) || emptyRatingStats;
        const bStats = statsMap.get(b.id) || emptyRatingStats;
        const aScore = computePostsOrderFeedScore(
          { ...a, createdAt: a.createdAt || new Date(nowMs).toISOString() },
          aStats,
          nowMs
        );
        const bScore = computePostsOrderFeedScore(
          { ...b, createdAt: b.createdAt || new Date(nowMs).toISOString() },
          bStats,
          nowMs
        );
        return bScore - aScore;
      }
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
    let pagedPosts = sortedPosts;
    if (offset) pagedPosts = pagedPosts.slice(offset);
    if (limit) pagedPosts = pagedPosts.slice(0, limit);
    const list = pagedPosts.map((p) => {
      const serialized = serializePost(p, statsMap);
      if (!shouldUseFields) return serialized;
      const out = {};
      if (normalizedRequestedFields.includes("id")) out.id = serialized.id;
      if (normalizedRequestedFields.includes("content")) out.content = serialized.content;
      if (normalizedRequestedFields.includes("createdAt")) out.createdAt = serialized.createdAt;
      if (normalizedRequestedFields.includes("user")) out.user = serialized.user;
      if (normalizedRequestedFields.includes("ratingAvg")) out.ratingAvg = serialized.ratingAvg;
      if (normalizedRequestedFields.includes("ratingCount")) out.ratingCount = serialized.ratingCount;
      return out;
    });
    res.json(list);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// --- Soft delete / trash / restore ---
app.delete("/posts/:id", async (req, res) => {
  try {
    const post = await prisma.post.updateMany({
      where: { id: req.params.id, deletedAt: null },
      data: { deletedAt: new Date() },
    });
    if (post.count === 0) return res.status(404).json({ error: "post not found or already deleted" });
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

app.patch("/posts/:id/restore", async (req, res) => {
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

app.listen(PORT, "0.0.0.0", () => console.log(`Server running at http://localhost:${PORT}`));
