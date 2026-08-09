// ADR-021 S4c — WhatsApp bağlantı enumerasyonu (salt-okunur).
// credential ≠ bağlantı: her telefon numarası ayrı bağlantı satırıdır ve
// credential'a vault_ref REFERANSI ile bağlanır (kopya yok). connection_id
// kalıcı iç kimliktir: lumos kullanıcısı + WABA + numara üçlüsünden
// deterministik türetilir; Graph çağrıları arasında değişmez.
// Kurucu sınırı (2026-08-09): enumeration 0/eksik dönerse satır UYDURULMAZ —
// boşluk `gaps` alanında görünür raporlanır.
import { createHmac } from "node:crypto";

import { authSecret } from "./lumos_session.js";
import { metaGraphVersion } from "./meta_oauth.js";

function clean(value) {
  return String(value || "").trim().slice(0, 256);
}

export function pagesConnectionId(lumosId, pageId) {
  if (!clean(lumosId) || !clean(pageId)) return "";
  const digest = createHmac("sha256", authSecret())
    .update(`meta-connection-v1:${lumosId}:pages:${pageId}`)
    .digest("base64url")
    .slice(0, 22);
  return `conn_page_${digest}`;
}

/**
 * Pages credential'ı için yönetilen Sayfa listesini çıkarır (me/accounts,
 * salt-okunur). Boş sonuç satır uydurmaz; `gaps`'te raporlanır.
 */
export async function enumeratePages(lumosId, credential, fetchImpl = fetch) {
  const payload = await graphGet(
    graphUrl("me/accounts", "id,name"),
    credential.accessToken,
    fetchImpl,
  );
  const items = Array.isArray(payload?.data) ? payload.data.slice(0, 50) : [];
  const pages = [];
  const gaps = [];
  if (items.length === 0) gaps.push({ reason: "pages_empty" });
  for (const item of items) {
    const pageId = clean(item?.id);
    if (!pageId) continue;
    pages.push({
      connection_id: pagesConnectionId(lumosId, pageId),
      provider: "pages",
      page_id: pageId,
      page_name: clean(item?.name),
    });
  }
  return { pages, gaps };
}

export function whatsappConnectionId(lumosId, wabaId, phoneNumberId) {
  if (!clean(lumosId) || !clean(wabaId) || !clean(phoneNumberId)) return "";
  const digest = createHmac("sha256", authSecret())
    .update(`meta-connection-v1:${lumosId}:whatsapp:${wabaId}:${phoneNumberId}`)
    .digest("base64url")
    .slice(0, 22);
  return `conn_wa_${digest}`;
}

function graphUrl(path, fields) {
  const version = metaGraphVersion();
  if (!version) throw new Error("meta_graph_version_not_configured");
  return `https://graph.facebook.com/${version}/${path}?${new URLSearchParams({ fields, limit: "50" })}`;
}

async function graphGet(url, accessToken, fetchImpl) {
  const response = await fetchImpl(url, {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}`, Accept: "application/json" },
    signal: AbortSignal.timeout(7000),
  });
  if (!response.ok) throw new Error("meta_graph_http_error");
  return response.json();
}

/**
 * Tek WhatsApp credential'ı için WABA → telefon numarası ağacını çıkarır.
 * Dönen `numbers` boş olabilir; boşluk nedenleri `gaps`'te raporlanır.
 */
export async function enumerateWhatsappNumbers(lumosId, credential, fetchImpl = fetch) {
  const businessesPayload = await graphGet(
    graphUrl("me/businesses", "id,name,owned_whatsapp_business_accounts{id,name}"),
    credential.accessToken,
    fetchImpl,
  );
  const businesses = Array.isArray(businessesPayload?.data) ? businessesPayload.data.slice(0, 50) : [];

  const wabas = [];
  for (const business of businesses) {
    const owned = business?.owned_whatsapp_business_accounts;
    for (const waba of Array.isArray(owned?.data) ? owned.data.slice(0, 50) : []) {
      if (clean(waba?.id)) {
        wabas.push({
          waba_id: clean(waba.id),
          waba_name: clean(waba.name),
          business_id: clean(business?.id),
          business_name: clean(business?.name),
        });
      }
    }
  }

  const numbers = [];
  const gaps = [];
  if (businesses.length === 0) gaps.push({ reason: "businesses_empty" });
  if (businesses.length > 0 && wabas.length === 0) gaps.push({ reason: "wabas_empty" });

  for (const waba of wabas) {
    const phonesPayload = await graphGet(
      graphUrl(`${waba.waba_id}/phone_numbers`, "id,display_phone_number,verified_name"),
      credential.accessToken,
      fetchImpl,
    );
    const phones = Array.isArray(phonesPayload?.data) ? phonesPayload.data.slice(0, 50) : [];
    if (phones.length === 0) {
      gaps.push({ reason: "phone_numbers_empty", waba_id: waba.waba_id });
      continue;
    }
    for (const phone of phones) {
      const phoneNumberId = clean(phone?.id);
      if (!phoneNumberId) continue;
      numbers.push({
        connection_id: whatsappConnectionId(lumosId, waba.waba_id, phoneNumberId),
        provider: "whatsapp",
        business_id: waba.business_id,
        business_name: waba.business_name,
        waba_id: waba.waba_id,
        waba_name: waba.waba_name,
        phone_number_id: phoneNumberId,
        display_phone_number: clean(phone?.display_phone_number),
        verified_name: clean(phone?.verified_name),
      });
    }
  }
  return { numbers, gaps };
}
