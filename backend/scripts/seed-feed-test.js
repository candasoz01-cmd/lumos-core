#!/usr/bin/env node
/**
 * Gerçek test: Kullanıcı oluştur → Post oluştur → GET /posts?order=feed (+ Bearer)
 * Kullanım: node scripts/seed-feed-test.js [BASE_URL]
 * Örnek:   node scripts/seed-feed-test.js http://localhost:3000
 */
const BASE = process.argv[2] || "http://localhost:3000";

async function request(method, path, body, extraHeaders) {
  const url = `${BASE}${path}`;
  const opts = {
    method,
    headers: { "Content-Type": "application/json", ...(extraHeaders || {}) },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) throw new Error(`${res.status} ${path}: ${JSON.stringify(data)}`);
  return data;
}

async function main() {
  console.log("BASE_URL:", BASE);

  // 1) Kullanıcı oluştur
  const username = "test-user-" + Date.now();
  const user = await request("POST", "/users", { username });
  console.log("1) POST /users →", user.id, user.username);

  // 2) Post oluştur
  const post = await request("POST", "/posts", {
    content: "Test gönderi – feed denemesi " + new Date().toISOString(),
    userId: user.id,
  });
  console.log("2) POST /posts →", post.id, post.content?.slice(0, 40) + "...");

  // 3) Feed al
  const feed = await request("GET", "/posts?order=feed&limit=50", undefined, {
    Authorization: `Bearer ${user.ratingToken}`,
  });
  console.log("3) GET /posts?order=feed →", feed.length, "gönderi");
  const ours = feed.find((p) => p.id === post.id);
  if (ours) console.log("   Yeni gönderi feed'de:", ours.id, ours.feedScore != null ? "feedScore:" + ours.feedScore : "");
  else console.log("   (Yeni gönderi listede görünmüyor olabilir)");

  console.log("Bitti.");
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
