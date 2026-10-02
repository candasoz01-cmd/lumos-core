/**
 * Ülke kodu → çağrı profili. Hukuk motoru değildir.
 * Boş ülke global_safe kullanır. Kayıtta olmayan açık ülke kodu çağrıyı kapatır.
 */

export const RESTRICTED_DATA_CLASSES = Object.freeze([
  "email",
  "phone",
  "government_id",
  "credential",
]);

export const GLOBAL_SAFE_PROFILE = Object.freeze({
  id: "global_safe",
  allowed_regions: Object.freeze(["unspecified"]),
  allowed_providers: Object.freeze(["openai", "google"]),
  max_retention_days: null,
  restricted_data_classes: RESTRICTED_DATA_CLASSES,
  fail_closed: false,
  source: "repo-default",
  legal_status: "not_a_legal_determination",
});

/** Yer tutucu. Gerçek ülke mevzuatı değildir. */
export const COUNTRY_POLICIES = Object.freeze({
  XX: Object.freeze({
    id: "XX",
    allowed_regions: Object.freeze(["eu"]),
    allowed_providers: Object.freeze(["openai"]),
    max_retention_days: 0,
    restricted_data_classes: RESTRICTED_DATA_CLASSES,
    fail_closed: false,
    source: "test_and_config_placeholder",
    legal_status: "not_a_legal_determination",
  }),
});

export function resolveCountryPolicy(country) {
  if (country == null) return GLOBAL_SAFE_PROFILE;
  const code = String(country).trim().toUpperCase();
  if (!code) return GLOBAL_SAFE_PROFILE;
  if (COUNTRY_POLICIES[code]) return COUNTRY_POLICIES[code];
  return {
    id: code,
    allowed_regions: [],
    allowed_providers: [],
    max_retention_days: 0,
    restricted_data_classes: RESTRICTED_DATA_CLASSES,
    fail_closed: true,
    reason: "unknown_country",
    source: "fail-closed",
    legal_status: "not_a_legal_determination",
  };
}
