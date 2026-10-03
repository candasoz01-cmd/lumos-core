import assert from "node:assert/strict";
import test from "node:test";
import startHandler from "../api/auth/google/start.js";
import callbackHandler from "../api/auth/google/callback.js";
import readinessHandler from "../api/auth/readiness.js";
import {
  MOBILE_OAUTH_COOKIE,
  allowedRedirectUris,
  makeState,
  redirectUri,
  sealSession,
} from "../api/_lib/lumos_session.js";

const MOBILE_CALLBACK = "https://welockai.com/auth/google/callback";
const WEB_CALLBACK = "https://app.example.test/auth/google/callback";
const ENV_KEYS = [
  "LUMOS_AUTH_STATE_SECRET",
  "LUMOS_GOOGLE_WEB_CLIENT_ID",
  "LUMOS_GOOGLE_WEB_CLIENT_SECRET",
  "LUMOS_GOOGLE_WEB_REDIRECT_URI",
  "LUMOS_GOOGLE_WEB_REDIRECT_URIS",
];

function makeRes() {
  return {
    statusCode: 0,
    headers: {},
    body: "",
    setHeader(key, value) {
      this.headers[key.toLowerCase()] = value;
    },
    end(payload = "") {
      this.body = String(payload);
      return this;
    },
  };
}

async function withEnv(values, fn) {
  const saved = Object.fromEntries(ENV_KEYS.map((key) => [key, process.env[key]]));
  for (const key of ENV_KEYS) delete process.env[key];
  Object.assign(process.env, values);
  try {
    return await fn();
  } finally {
    for (const key of ENV_KEYS) {
      if (saved[key] === undefined) delete process.env[key];
      else process.env[key] = saved[key];
    }
  }
}

const BOTH_HOSTS = {
  LUMOS_GOOGLE_WEB_REDIRECT_URI: WEB_CALLBACK,
  LUMOS_GOOGLE_WEB_REDIRECT_URIS: `${MOBILE_CALLBACK}, ${WEB_CALLBACK}`,
};

test("without a redirect list the single configured callback is used for every host", async () => {
  await withEnv({ LUMOS_GOOGLE_WEB_REDIRECT_URI: WEB_CALLBACK }, () => {
    assert.equal(redirectUri({ headers: { host: "welockai.com" } }), WEB_CALLBACK);
    assert.equal(redirectUri(), WEB_CALLBACK);
  });
  await withEnv({}, () => {
    assert.equal(redirectUri({ headers: { host: "app.example.test" } }), MOBILE_CALLBACK);
  });
});

test("each allowed host gets its own callback; unknown hosts fall back", async () => {
  await withEnv(BOTH_HOSTS, () => {
    assert.equal(redirectUri({ headers: { host: "welockai.com" } }), MOBILE_CALLBACK);
    assert.equal(redirectUri({ headers: { host: "App.Example.Test" } }), WEB_CALLBACK);
    assert.equal(
      redirectUri({ headers: { host: "internal.vercel.app", "x-forwarded-host": "welockai.com" } }),
      MOBILE_CALLBACK,
    );
    assert.equal(redirectUri({ headers: { host: "attacker.example" } }), WEB_CALLBACK);
    assert.equal(redirectUri({ headers: {} }), WEB_CALLBACK);
  });
});

test("redirect list ignores entries that are not https OAuth callbacks", async () => {
  await withEnv(
    {
      LUMOS_GOOGLE_WEB_REDIRECT_URIS: [
        "http://welockai.com/auth/google/callback",
        "https://welockai.com/elsewhere",
        "https://welockai.com/auth/google/callback?next=x",
        "https://user:pw@welockai.com/auth/google/callback",
        "not a url",
        WEB_CALLBACK,
      ].join(","),
    },
    () => {
      assert.deepEqual(allowedRedirectUris(), [WEB_CALLBACK]);
      assert.equal(redirectUri({ headers: { host: "welockai.com" } }), MOBILE_CALLBACK);
    },
  );
});

test("start sends Google the callback of the host the login started on", async () => {
  await withEnv(
    {
      ...BOTH_HOSTS,
      LUMOS_AUTH_STATE_SECRET: "test-only-secret-32-characters-minimum",
      LUMOS_GOOGLE_WEB_CLIENT_ID: "google-client",
    },
    async () => {
      for (const [host, expected] of [
        ["welockai.com", MOBILE_CALLBACK],
        ["app.example.test", WEB_CALLBACK],
      ]) {
        const res = makeRes();
        await startHandler(
          {
            method: "GET",
            url: "/api/auth/google/start?mobile=1&app_state=mobile_state_12345678901234567890",
            headers: { host },
          },
          res,
        );
        assert.equal(res.statusCode, 302);
        const location = new URL(res.headers.location);
        assert.equal(location.searchParams.get("redirect_uri"), expected);
      }
    },
  );
});

test("mobile login on the mobile host returns to the app with a matching token exchange", async () => {
  await withEnv(
    {
      ...BOTH_HOSTS,
      LUMOS_AUTH_STATE_SECRET: "test-only-secret-32-characters-minimum",
      LUMOS_GOOGLE_WEB_CLIENT_ID: "google-client",
      LUMOS_GOOGLE_WEB_CLIENT_SECRET: "google-secret",
    },
    async () => {
      const originalFetch = globalThis.fetch;
      let exchangedRedirect = "";
      globalThis.fetch = async (url, options = {}) => {
        if (String(url).includes("oauth2.googleapis.com/token")) {
          exchangedRedirect = new URLSearchParams(String(options.body)).get("redirect_uri");
          return { ok: true, async json() { return { access_token: "temporary-access" }; } };
        }
        return {
          ok: true,
          async json() {
            return { sub: "google-subject-one", name: "Ada Lovelace", email: "ada@example.test" };
          },
        };
      };
      const oauthState = makeState();
      const appState = "mobile_state_12345678901234567890";
      const mobileFlow = sealSession({
        kind: "mobile_oauth",
        app_state: appState,
        oauth_state: oauthState,
        exp: Math.floor(Date.now() / 1000) + 60,
      });
      const res = makeRes();
      try {
        await callbackHandler(
          {
            method: "GET",
            url: `/api/auth/google/callback?code=test-code&state=${encodeURIComponent(oauthState)}`,
            headers: {
              host: "welockai.com",
              cookie: `lumos_oauth_state=${oauthState}; ${MOBILE_OAUTH_COOKIE}=${mobileFlow}`,
            },
          },
          res,
        );
      } finally {
        globalThis.fetch = originalFetch;
      }
      assert.equal(res.statusCode, 302);
      assert.equal(new URL(res.headers.location).protocol, "lumos:");
      assert.equal(exchangedRedirect, MOBILE_CALLBACK);
    },
  );
});

test("readiness reports the callback selected for the requesting host", async () => {
  await withEnv(BOTH_HOSTS, async () => {
    const res = makeRes();
    await readinessHandler({ method: "GET", headers: { host: "welockai.com" } }, res);
    const payload = JSON.parse(res.body);
    assert.equal(payload.redirect_uri, MOBILE_CALLBACK);
    assert.deepEqual(payload.redirect_uris, [MOBILE_CALLBACK, WEB_CALLBACK]);
  });
});
