/** ADR-021 S1 — vault çoklu-credential adapter testleri (credential ≠ bağlantı). */
import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import {
  listMetaCredentials,
  resolveMetaCredentialByRef,
} from "../api/_lib/meta_vault.js";

beforeEach(() => {
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_URL = "https://vault.example/api";
  process.env.LUMOS_CREDENTIAL_VAULT_WRITE_TOKEN = "test-vault-token";
});

function fetchStub(handler) {
  return async (url, options) => {
    const body = JSON.parse(options.body);
    const payload = handler(body, url, options);
    return { ok: true, json: async () => payload };
  };
}

test("listMetaCredentials returns secretless metadata rows", async () => {
  let seen;
  const rows = await listMetaCredentials("lumos-1", "whatsapp", fetchStub((body) => {
    seen = body;
    return {
      ok: true,
      credentials: [
        { vault_ref: "vr-1", provider: "whatsapp", provider_account_id: "acc-1",
          expires_at: 123, auth_mode: "facebook_login" },
        { vault_ref: "vr-2", provider: "whatsapp", provider_account_id: "acc-2",
          expires_at: 456, auth_mode: "facebook_login",
          credential: { access_token: "LEAK" } },
        { vault_ref: "", provider: "whatsapp", provider_account_id: "gecersiz" },
      ],
    };
  }));
  assert.equal(seen.operation, "credential.list");
  assert.equal(seen.owner_lumos_id, "lumos-1");
  assert.equal(seen.provider, "whatsapp");
  assert.equal(rows.length, 2); // geçersiz satır elenir
  assert.deepEqual(rows[0], {
    vaultRef: "vr-1", provider: "whatsapp", providerAccountId: "acc-1",
    expiresAt: 123, authMode: "facebook_login",
  });
  // secret sızıntısı yok: dönen satırlar yalnız metadata alanları taşır
  for (const row of rows) {
    assert.equal(Object.hasOwn(row, "accessToken"), false);
    assert.equal(JSON.stringify(row).includes("LEAK"), false);
  }
});

test("listMetaCredentials omits provider filter when not given", async () => {
  let seen;
  await listMetaCredentials("lumos-1", undefined, fetchStub((body) => {
    seen = body;
    return { ok: true, credentials: [] };
  }));
  assert.equal(Object.hasOwn(seen, "provider"), false);
});

test("resolveMetaCredentialByRef resolves account-scoped by vault_ref", async () => {
  let seen;
  const cred = await resolveMetaCredentialByRef("lumos-1", "vr-2", fetchStub((body) => {
    seen = body;
    return {
      ok: true,
      vault_ref: "vr-2",
      provider_account_id: "acc-2",
      credential: { access_token: "tok", token_type: "bearer",
                    expires_at: 999, auth_mode: "facebook_login" },
    };
  }));
  assert.equal(seen.operation, "credential.resolve");
  assert.equal(seen.vault_ref, "vr-2");
  assert.equal(cred.providerAccountId, "acc-2");
  assert.equal(cred.vaultRef, "vr-2");
  assert.equal(cred.expiresAt, 999);
});

test("resolveMetaCredentialByRef rejects ref mismatch and missing fields", async () => {
  await assert.rejects(
    () => resolveMetaCredentialByRef("lumos-1", "vr-2", fetchStub(() => ({
      ok: true, vault_ref: "BASKA", provider_account_id: "acc-2",
      credential: { access_token: "tok" },
    }))),
    /meta_vault_resolve_ref_mismatch/,
  );
  await assert.rejects(
    () => resolveMetaCredentialByRef("lumos-1", "vr-2", fetchStub(() => ({
      ok: true, vault_ref: "vr-2", provider_account_id: "",
      credential: { access_token: "tok" },
    }))),
    /meta_vault_credential_missing/,
  );
  await assert.rejects(() => resolveMetaCredentialByRef("lumos-1", "  "),
    /meta_vault_ref_required/);
});
