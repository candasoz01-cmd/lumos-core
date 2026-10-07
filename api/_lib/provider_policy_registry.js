/**
 * Sağlayıcı yetenek kaydı.
 * İnsan, sözleşme veya API ile doğrulanmayan alan false/unknown kalır.
 * contract_verified=false bir sağlayıcı hassas veri sınıfı taşıyan çağrıda kullanılamaz.
 */

export const SENSITIVE_DATA_CLASSES = Object.freeze([
  "email",
  "phone",
  "government_id",
  "credential",
]);

const PENDING = "provider verification pending";

function entry(id) {
  return {
    id,
    allowed_regions: ["unspecified"],
    retention_mode: "unknown",
    store_supported: false,
    zero_data_retention_supported: false,
    training_use: "unknown",
    contract_verified: false,
    allowed_data_classes: ["message_text"],
    deletion_api_supported: false,
    source: "repo-default",
    evidence: PENDING,
    unknown: false,
  };
}

export const PROVIDER_POLICIES = Object.freeze({
  openai: Object.freeze(entry("openai")),
  google: Object.freeze(entry("google")),
});

export function unknownProviderPolicy(id) {
  return {
    id: String(id || "unknown"),
    allowed_regions: [],
    retention_mode: "unknown",
    store_supported: false,
    zero_data_retention_supported: false,
    training_use: "unknown",
    contract_verified: false,
    allowed_data_classes: [],
    deletion_api_supported: false,
    source: "unknown",
    evidence: PENDING,
    unknown: true,
  };
}

export function getProviderPolicy(providerId) {
  const id = String(providerId || "").trim().toLowerCase();
  return PROVIDER_POLICIES[id] || unknownProviderPolicy(id);
}

export function providerDeletionAvailable(providerId) {
  return getProviderPolicy(providerId).deletion_api_supported === true;
}
