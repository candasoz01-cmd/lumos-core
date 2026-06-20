/**
 * Panel görev REST API bağlayıcısı (POST /tasks, /tasks/complete, /tasks/delete).
 * fetchImpl: (url, opts) => Promise<Response> — örn. app.js içindeki fetchWithTimeout ile sarılmış.
 */
(function (global) {
  "use strict";

  function joinBase(base, path) {
    var b = String(base || "").replace(/\/$/, "");
    var p = path.charAt(0) === "/" ? path : "/" + path;
    return b + p;
  }

  function LumosTasksApiAdapter(options) {
    var o = options || {};
    this.baseUrl = String(o.baseUrl || "").replace(/\/$/, "");
    this.fetchImpl = o.fetchImpl || (typeof fetch !== "undefined" ? fetch.bind(global) : null);
  }

  LumosTasksApiAdapter.prototype._post = function (path, body) {
    if (!this.fetchImpl) return Promise.reject(new Error("fetch yok"));
    var url = joinBase(this.baseUrl, path);
    return this.fetchImpl(url, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(body != null ? body : {}),
    }).then(function (r) {
      return r.text().then(function (txt) {
        var j = null;
        if (txt) {
          try {
            j = JSON.parse(txt);
          } catch (_) {
            j = { _raw: txt };
          }
        }
        return { ok: r.ok, status: r.status, body: j };
      });
    });
  };

  LumosTasksApiAdapter.prototype.postTasksCreate = function (payload) {
    return this._post("/tasks", payload);
  };
  LumosTasksApiAdapter.prototype.postTasksComplete = function (payload) {
    return this._post("/tasks/complete", payload);
  };
  LumosTasksApiAdapter.prototype.postTasksDelete = function (payload) {
    return this._post("/tasks/delete", payload);
  };

  global.LumosTasksApiAdapter = LumosTasksApiAdapter;
})(typeof window !== "undefined" ? window : globalThis);
