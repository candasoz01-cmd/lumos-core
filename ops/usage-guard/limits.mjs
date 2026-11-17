// Barındırılan yapay zekâ kullanım sayacı — saf mantık (Cloudflare Durable Object içinde çalışır).
//
// Üç sayaç tutulur: kullanıcı/dakika, kullanıcı/gün, tüm kullanıcılar/gün.
// Her sayaç tek satırdır ve pencere değişince aynı satırın üzerine yazılır;
// bu yüzden tablo büyümez ve temizlik silmesi (ücretli yazma sayılır) gerekmez.
// İzin verilen istek 3 satır yazar; reddedilen istek hiç yazmaz.
//
// Durable Object tek iş parçacıklıdır ve SQLite çağrıları eşzamanlıdır:
// okuma ile yazma arasında await yoktur, yani iki istek aynı sayacı yarıştıramaz.

export const DEFAULT_LIMITS = Object.freeze({
  userPerMinute: 10,
  userPerDay: 100,
  globalPerDay: 2000,
});

export const ROWS_WRITTEN_PER_ALLOWED_REQUEST = 3;

function positiveInt(value, fallback) {
  const n = Number(String(value ?? "").trim());
  return Number.isInteger(n) && n > 0 ? n : fallback;
}

export function readLimits(env = {}) {
  return {
    userPerMinute: positiveInt(env.LUMOS_USAGE_USER_PER_MINUTE, DEFAULT_LIMITS.userPerMinute),
    userPerDay: positiveInt(env.LUMOS_USAGE_USER_PER_DAY, DEFAULT_LIMITS.userPerDay),
    globalPerDay: positiveInt(env.LUMOS_USAGE_GLOBAL_PER_DAY, DEFAULT_LIMITS.globalPerDay),
  };
}

// Pencereler UTC'dir; Cloudflare ücretsiz günlük sınırları da 00:00 UTC'de sıfırlanır.
export function windows(nowMs) {
  const iso = new Date(nowMs).toISOString();
  return { minute: iso.slice(0, 16), day: iso.slice(0, 10) };
}

export function ensureSchema(sql) {
  sql.exec(
    "CREATE TABLE IF NOT EXISTS counters (key TEXT PRIMARY KEY, win TEXT NOT NULL, count INTEGER NOT NULL)",
  );
}

function currentCount(sql, key, win) {
  const rows = sql.exec("SELECT win, count FROM counters WHERE key = ?", key).toArray();
  if (!rows.length || rows[0].win !== win) return 0;
  return Number(rows[0].count) || 0;
}

function writeCount(sql, key, win, count) {
  sql.exec(
    "INSERT INTO counters (key, win, count) VALUES (?, ?, ?) " +
      "ON CONFLICT(key) DO UPDATE SET win = excluded.win, count = excluded.count",
    key,
    win,
    count,
  );
}

export function consume(sql, lumosId, limits, nowMs) {
  const { minute, day } = windows(nowMs);
  const counters = [
    { scope: "user_minute", key: `u:m:${lumosId}`, win: minute, limit: limits.userPerMinute },
    { scope: "user_day", key: `u:d:${lumosId}`, win: day, limit: limits.userPerDay },
    { scope: "global_day", key: "g:d", win: day, limit: limits.globalPerDay },
  ];
  const counts = counters.map((c) => currentCount(sql, c.key, c.win));
  for (let i = 0; i < counters.length; i += 1) {
    if (counts[i] >= counters[i].limit) {
      return { allowed: false, scope: counters[i].scope };
    }
  }
  const remaining = {};
  counters.forEach((c, i) => {
    writeCount(sql, c.key, c.win, counts[i] + 1);
    remaining[c.scope] = c.limit - (counts[i] + 1);
  });
  return { allowed: true, remaining };
}
