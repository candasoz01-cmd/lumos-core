/**
 * GET /posts?order=feed için panel yardımcıları (vanilla).
 * Taban: window.LUMOS_POSTS_API_BASE veya localStorage lumos_posts_api_base → yoksa http://127.0.0.1:3000
 * Oturum içinde tek kez çözümlenir (resolvePostsApiBase); feed/trash/restore/delete aynı tabanı kullanır.
 */
(function (global) {
  "use strict";

  var DEFAULT_BASE = "http://127.0.0.1:3000";

  /** İlk okumada donar; sayfa yenilenene veya resetPostsApiBaseForSession çağrılana kadar değişmez. */
  var _sessionPostsApiBase = null;

  function resolvePostsApiBase() {
    if (_sessionPostsApiBase !== null) return _sessionPostsApiBase;
    try {
      if (global.LUMOS_POSTS_API_BASE && String(global.LUMOS_POSTS_API_BASE).trim()) {
        _sessionPostsApiBase = String(global.LUMOS_POSTS_API_BASE).replace(/\/$/, "");
        return _sessionPostsApiBase;
      }
      var ls = global.localStorage && global.localStorage.getItem("lumos_posts_api_base");
      if (ls && String(ls).trim()) {
        _sessionPostsApiBase = String(ls).replace(/\/$/, "");
        return _sessionPostsApiBase;
      }
    } catch (_) {}
    _sessionPostsApiBase = DEFAULT_BASE;
    return _sessionPostsApiBase;
  }

  function getBase() {
    return resolvePostsApiBase();
  }

  /** Konsol: liste/trash/feed aksiyonlarının aynı tabana gittiğini doğrula */
  function logFeedApiBaseTriplet() {
    var b = resolvePostsApiBase();
    console.log("EMPTY_TRASH_BASE", b);
    console.log("TRASH_LIST_BASE", b);
    console.log("FEED_ACTION_BASE", b);
    return b;
  }

  /** Geliştirici: localStorage / LUMOS_POSTS_API_BASE değişince yeniden çözümle (sayfa yenileme alternatifi). */
  function resetPostsApiBaseForSession() {
    _sessionPostsApiBase = null;
    return resolvePostsApiBase();
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

  function postJson(path, body) {
    console.log("POST PATH:", path);
    console.log("POST BODY:", body || {});
    console.log("[FeedApi] POST", path, body || {});
    var init = feedFetchInit();
    var headers = {};
    if (init.headers) {
      for (var k in init.headers) headers[k] = init.headers[k];
    }
    headers["Content-Type"] = "application/json";
    return fetch(getBase() + path, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(body || {}),
    })
      .then(function (r) {
      var status = r.status;
      if (!r.ok) {
        return r
          .json()
          .catch(function () {
            return {};
          })
          .then(function (errBody) {
            console.log("RESPONSE STATUS:", status);
            console.log("RESPONSE BODY:", errBody || {});
            var msg = errBody && errBody.error ? String(errBody.error) : "HTTP " + r.status;
            console.log("[FeedApi] POST error", path, r.status, errBody || {});
            console.error("[FeedApi] POST catchable error", { path: path, status: status, body: errBody || {} });
            throw new Error(msg);
          });
      }
      return r
        .json()
        .catch(function () {
          return {};
        })
        .then(function (data) {
          console.log("RESPONSE STATUS:", status);
          console.log("RESPONSE BODY:", data || {});
          console.log("[FeedApi] POST ok", path, data || {});
          return data;
        });
      })
      .catch(function (err) {
      console.error("[FeedApi] postJson catch", {
        path: path,
        error: (err && err.message) || String(err),
      });
      throw err;
    });
  }

  function deleteJson(path) {
    console.log("[FeedApi] DELETE", path);
    var init = feedFetchInit();
    var headers = {};
    if (init.headers) {
      for (var k in init.headers) headers[k] = init.headers[k];
    }
    return fetch(getBase() + path, {
      method: "DELETE",
      headers: headers,
    })
      .then(function (r) {
        if (!r.ok) {
          return r
            .json()
            .catch(function () {
              return {};
            })
            .then(function (errBody) {
              var msg = errBody && errBody.error ? String(errBody.error) : "HTTP " + r.status;
              throw new Error(msg);
            });
        }
        return r.json().catch(function () {
          return {};
        });
      });
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

  function formatCreatedAtReadable(iso) {
    if (iso == null || iso === "") return "—";
    var d = new Date(iso instanceof Date ? iso : iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    try {
      return d.toLocaleString("tr-TR", { dateStyle: "medium", timeStyle: "short" });
    } catch (_) {
      return d.toISOString().replace("T", " ").replace(/\.\d{3}Z$/, "").replace("Z", "");
    }
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

  function numOrNull(v) {
    if (v == null || v === "") return null;
    var n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  function numOrZero(v) {
    var n = Number(v);
    return Number.isFinite(n) ? n : 0;
  }

  /**
   * Backend tek gerçeklik: GET yanıtındaki rating alanları (camelCase veya snake_case).
   * Tüm feed/ranked ekranları yalnızca bu çıktı ile kart çizer; raw obje doğrudan kullanılmaz.
   */
  function normalizePostForPanel(raw) {
    if (!raw || typeof raw !== "object") {
      return {
        id: "",
        content: "",
        username: "",
        ratingAvg: null,
        ratingCount: 0,
        highRatingCount: 0,
        lowRatingCount: 0,
        createdAt: "",
      };
    }
    var ra = raw.ratingAvg != null ? raw.ratingAvg : raw.rating_avg;
    var rc = raw.ratingCount != null ? raw.ratingCount : raw.rating_count;
    var hi = raw.highRatingCount != null ? raw.highRatingCount : raw.high_rating_count;
    var lo = raw.lowRatingCount != null ? raw.lowRatingCount : raw.low_rating_count;
    var createdAtRaw = raw.createdAt != null ? raw.createdAt : raw.created_at;
    var createdAt =
      createdAtRaw instanceof Date
        ? createdAtRaw.toISOString()
        : createdAtRaw != null
          ? String(createdAtRaw)
          : "";
    var user = raw.user;
    var usernameFromUser =
      user && typeof user === "object" && user.username != null ? String(user.username) : "";
    var username =
      usernameFromUser ||
      (raw.username != null ? String(raw.username) : "") ||
      (raw.user_username != null ? String(raw.user_username) : "");
    return {
      id: raw.id != null ? String(raw.id) : "",
      content: raw.content != null ? String(raw.content) : "",
      username: username,
      ratingAvg: ra != null && ra !== "" ? numOrNull(ra) : null,
      ratingCount: numOrZero(rc),
      highRatingCount: numOrZero(hi),
      lowRatingCount: numOrZero(lo),
      createdAt: createdAt,
    };
  }

  function pickPostCardProps(post) {
    return normalizePostForPanel(post);
  }

  function formatMeta(p) {
    var n = p.ratingCount || 0;
    var avg = p.ratingAvg != null && !Number.isNaN(Number(p.ratingAvg)) ? Number(p.ratingAvg).toFixed(1) : null;
    var left = avg != null ? avg + " (" + n + " oy)" : "— (" + n + " oy)";
    return left + " · " + formatRelativeTime(p.createdAt);
  }

  global.LumosFeedApi = {
    getBase: getBase,
    resolvePostsApiBase: resolvePostsApiBase,
    logFeedApiBaseTriplet: logFeedApiBaseTriplet,
    resetPostsApiBaseForSession: resetPostsApiBaseForSession,
    escapeHtml: escapeHtml,
    formatCreatedAtReadable: formatCreatedAtReadable,
    formatRelativeTime: formatRelativeTime,
    pickPostCardProps: pickPostCardProps,
    normalizePostForPanel: normalizePostForPanel,
    formatMeta: formatMeta,
    /** Feed sekmesi: GET /posts?order=feed. Rated High / Low: ayrıca ratedHighUrl / ratedLowUrl (app.js sekme başına tek GET). */
    feedUrl: function (limit, offset) {
      var lim = limit == null || limit === "" ? 20 : Number(limit);
      if (!Number.isFinite(lim) || lim < 1) lim = 20;
      lim = Math.min(100, Math.max(1, Math.floor(lim)));
      var q = "/posts?order=feed&limit=" + lim;
      if (offset != null && offset !== "") {
        var off = Number(offset);
        if (Number.isFinite(off) && off >= 0) q += "&offset=" + Math.floor(off);
      }
      return getBase() + q;
    },
    /** Doğrudan panel listesi için kullanılmaz (health / harici çağrılar için tutulabilir). */
    ratedHighUrl: function (limit) {
      var lim = limit == null || limit === "" ? 20 : Number(limit);
      if (!Number.isFinite(lim) || lim < 1) lim = 20;
      lim = Math.min(100, Math.max(1, Math.floor(lim)));
      return getBase() + "/posts/rated-high?limit=" + lim;
    },
    ratedLowUrl: function (limit) {
      var lim = limit == null || limit === "" ? 20 : Number(limit);
      if (!Number.isFinite(lim) || lim < 1) lim = 20;
      lim = Math.min(100, Math.max(1, Math.floor(lim)));
      return getBase() + "/posts/rated-low?limit=" + lim;
    },
    rateHigh: function (postId) {
      return postJson("/posts/" + encodeURIComponent(String(postId || "")) + "/rate-high", {});
    },
    rateLow: function (postId) {
      return postJson("/posts/" + encodeURIComponent(String(postId || "")) + "/rate-low", {});
    },
    moveToTrash: function (postId) {
      return postJson("/posts/" + encodeURIComponent(String(postId || "")) + "/trash", {});
    },
    trashPost: function (postId) {
      return postJson("/posts/" + encodeURIComponent(String(postId || "")) + "/trash", {});
    },
    restorePost: function (postId) {
      return postJson("/posts/" + encodeURIComponent(String(postId || "")) + "/restore", {});
    },
    permanentDeletePost: function (postId) {
      return deleteJson("/posts/" + encodeURIComponent(String(postId || "")));
    },
    emptyTrash: function () {
      var init = feedFetchInit();
      var headers = {};
      if (init.headers) {
        for (var k in init.headers) headers[k] = init.headers[k];
      }
      var url = getBase() + "/posts/trash";
      return fetch(url, {
        method: "DELETE",
        headers: headers,
      })
        .then(function (r) {
          return r.text().then(function (text) {
            var body = {};
            try {
              body = text && String(text).trim() ? JSON.parse(text) : {};
            } catch (e2) {
              body = { _raw: text };
            }
            if (!r.ok) {
              var msg =
                body && body.error
                  ? String(body.error)
                  : "HTTP " + r.status + (text ? " " + text : "");
              throw new Error(msg);
            }
            return body;
          });
        });
    },
    /** GET /posts/trash — Silinenler doğrulama / liste */
    getTrashList: function () {
      var init = feedFetchInit();
      return fetch(getBase() + "/posts/trash", init).then(function (r) {
        if (!r.ok) {
          return r
            .json()
            .catch(function () {
              return {};
            })
            .then(function (body) {
              var msg = body && body.error ? String(body.error) : "HTTP " + r.status;
              throw new Error(msg);
            });
        }
        return r.json();
      });
    },
    feedFetchInit: feedFetchInit,
  };
})(typeof window !== "undefined" ? window : globalThis);
