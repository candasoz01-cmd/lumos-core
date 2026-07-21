<!-- markdownlint-disable MD013 -->

# Lumos Single Reader Gateway v1

Durum: KA-003 sözleşmesi.

Kullanıcı açısından tek muhatap Lumos'tur. Ajanlar kullanıcıya doğrudan rapor vermez; yapılandırılmış olayları Duvar'a yazar. Kullanıcı özetini yalnız aktif Lumos Duvar okuyucusu okuyabilir.

## Akış

1. Ajan, GitHub, CI veya test kaynağı ortak coordination inbox'a olay yazar.
2. Gateway aynı `dedupe_key` değerini tek olay olarak kabul eder ve olayı `task_id` ile ilişkilendirir.
3. Politika olayı `USER`, `TASK` veya `AGENT` rotasına ayırır.
4. Tek token-backed reader lease kullanıcıya dönük olayları `Karar`, `Risk`, `Öneri` ve `Bilgi` başlıklarına toplar.
5. Teslim başarıyla tamamlanınca reader olayları ayrıca acknowledge eder. Okuma tek başına olayı düşürmez.
6. Claim, stale takeover, heartbeat, yönlendirme, okuma ve acknowledge işlemleri audit izine yazılır.

## Kullanıcı rotası

- `DECISION_REQUIRED` ve `RECOMMENDATION` kullanıcıya gider.
- Yalnız `high` veya `critical` seviyeli `RISK` kullanıcıya gider.
- `INFORMATION` ancak `user_relevant=true` olduğunda kullanıcıya gider.
- Diğer olaylar görev veya hedef ajan rotasında sessiz kalır.

## Tek okuyucu sınırı

- Aynı anda yalnız bir süresi dolmamış reader lease bulunabilir.
- Reader token'ının yalnız SHA-256 özeti diskte tutulur.
- Token olmadan kullanıcı özeti, internal rota veya acknowledge okunamaz.
- TTL dolunca yeni Lumos reader stale takeover yapabilir; bu olay audit edilir.

Bu katman kullanıcıya tek Lumos sesi sağlar. Dosya sistemine doğrudan erişebilen ayrıcalıklı bir süreç bu yerel kapıyı atlayabilir; işletim sistemi kimliği ve imzalı servis yetkilendirmesi daha sonraki güvenlik katmanıdır.
