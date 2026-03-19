/**
 * GET /posts?order=feed için panel yardımcıları (vanilla).
 * Taban: window.LUMOS_POSTS_API_BASE veya localStorage lumos_posts_api_base → yoksa http://127.0.0.1:3000
 */
(function (global) {
  "use strict";

  var DEFAULT_BASE = "http://127.0.0.1:3000";

  function getBase() {
    try {
      if (global.LUMOS_POSTS_API_BASE && String(global.LUMOS_POSTS_API_BASE).trim())
        return String(global.LUMOS_POSTS_API_BASE).replace(/\/$/, "");
      var ls = global.localStorage && global.localStorage.getItem("lumos_posts_api_base");
      if (ls && String(ls).trim()) return String(ls).replace(/\/$/, "");
    } catch (_) {}
    return DEFAULT_BASE;
  }

  /** ratingToken (Bearer) — window.LUMOS_AUTH_TOKEN veya localStorage lumos_rating_token / lumos_auth_token */
  function getAuthToken() {
    try {
      if (global.LUMOS_AUTH_TOKEN != null && String(global.LUMOS_AUTH_TOKEN).trim())
        return String(global.LUMOS_AUTH_TOKEN).trim();
      var ls =
        global.localStorage &&
        (global.localStorage.getItem("lumos_rating_token") ||
          global.localStorage.getItem("lumos_auth_token"));
      if (ls && String(ls).trim()) return String(ls).trim();
    } catch (_) {}
    return "";
  }

  function feedFetchInit() {
    var token = getAuthToken();
    if (!token) return {};
    return { headers: { Authorization: "Bearer " + token } };
  }

  function escapeHtml(s) {
    if (s == null) return "";
    var t = String(s);
    return t
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatRelativeTime(iso) {
    var t = new Date(iso).getTime();
    if (Number.isNaN(t)) return "—";
    var sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
    if (sec < 60) return "Az önce";
    var min = Math.floor(sec / 60);
    if (min < 60) return min + " dakika önce";
    var h = Math.floor(min / 60);
    if (h < 24) return h + " saat önce";
    var d = Math.floor(h / 24);
    if (d < 30) return d + " gün önce";
    var mo = Math.floor(d / 30);
    if (mo < 12) return mo + " ay önce";
    return Math.floor(d / 365) + " yıl önce";
  }

  function pickPostCardProps(post) {
    if (!post || typeof post !== "object") {
      return { content: "", ratingAvg: null, ratingCount: 0, createdAt: "" };
    }
    var createdAt =
      post.createdAt instanceof Date
        ? post.createdAt.toISOString()
        : post.createdAt != null
          ? String(post.createdAt)
          : "";
    return {
      content: post.content != null ? String(post.content) : "",
      ratingAvg:
        post.ratingAvg != null && post.ratingAvg !== "" ? Number(post.ratingAvg) : null,
      ratingCount: Number(post.ratingCount) || 0,
      createdAt: createdAt,
    };
  }

  function formatMeta(p) {
    var n = p.ratingCount || 0;
    var avg = p.ratingAvg != null && !Number.isNaN(Number(p.ratingAvg)) ? Number(p.ratingAvg).toFixed(1) : null;
    var left = avg != null ? avg + " (" + n + " oy)" : "— (" + n + " oy)";
    return left + " · " + formatRelativeTime(p.createdAt);
  }

  global.LumosFeedApi = {
    getBase: getBase,
    escapeHtml: escapeHtml,
    formatRelativeTime: formatRelativeTime,
    pickPostCardProps: pickPostCardProps,
    formatMeta: formatMeta,
    feedUrl: function (limit, offset) {
      var lim = limit == null || limit === "" ? 50 : Number(limit);
      if (!Number.isFinite(lim) || lim < 1) lim = 50;
      lim = Math.min(100, Math.max(1, Math.floor(lim)));
      var q = "/posts?order=feed&limit=" + lim;
      if (offset != null && offset !== "") {
        var off = Number(offset);
        if (Number.isFinite(off) && off >= 0) q += "&offset=" + Math.floor(off);
      }
      return getBase() + q;
    },
    feedFetchInit: feedFetchInit,
  };
})(typeof window !== "undefined" ? window : globalThis);
