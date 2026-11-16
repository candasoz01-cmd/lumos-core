// Barındırılan yapay zekâ (sohbet, mobil sohbet, gerçek zamanlı ses) erişim kapısı.
//
// Amaç: Google ile giriş yapabilen her hesabın OpenAI/Gemini maliyeti
// üretmesini önlemek. Yalnız LUMOS_HOSTED_AI_ALLOWED_IDS içinde açıkça
// listelenen Lumos ID'leri model çağrısı yapabilir. Liste tanımsız veya boşsa
// hiçbir oturum model çağıramaz (fail-closed). Herkese açma modu yoktur.
//
// Bu dosya kota veya harcama sayacı DEĞİLDİR. Sunucusuz ortamda paylaşılan
// depolama olmadan güvenilir kullanıcı başı kota yazılamaz; o iş ayrı PR'dır.

export function hostedAiAllowedIds(env = process.env) {
  return new Set(
    String(env.LUMOS_HOSTED_AI_ALLOWED_IDS || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
  );
}

export function isHostedAiAllowed(lumosId, env = process.env) {
  const id = String(lumosId || "").trim();
  if (!id) return false;
  return hostedAiAllowedIds(env).has(id);
}

export const HOSTED_AI_NOT_ENABLED = {
  error: "hosted_ai_not_enabled",
  errorKind: "access_denied",
  message: "Bu hesap için barındırılan yapay zekâ erişimi henüz açılmadı.",
};
