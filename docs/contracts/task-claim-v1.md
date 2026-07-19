<!-- markdownlint-disable MD013 -->

# Lumos Board Task Claim v1

Durum: KA-002 sözleşmesi.

Lumos Board yalnız durum panosu değildir. Yazma işi başlamadan önce sahipliği atomik olarak ayıran görev alma kapısıdır.

## Zorunlu claim alanları

- `claim_id` ve `task_id`
- `repo`, `branch` ve `worktree`
- `owner`
- repo-relative dosya veya dizin kapsamları
- `status`, `started_at`, `heartbeat_at` ve `expires_at`

## Kurallar

1. Aynı repo içindeki aktif aynı görev kimliği `DUPLICATE_TASK` üretir.
2. Eşit veya üst-alt dizin ilişkili kapsamlar `SCOPE_CONFLICT` üretir.
3. Claim kontrolü ve kayıt tek işletim sistemi dosya kilidi altında yapılır.
4. Çakışan iş doğrudan başlayamaz; reddedilir, `QUEUED` olur veya mevcut sahibin alt görevi olarak bağlanır.
5. Alt görev kapsamı parent claim içinde kalır ve yalnız parent sahibi tarafından devredilir.
6. Heartbeat lease süresini uzatır. TTL dolunca aktif claim `EXPIRED` olur ve kapsam yeniden alınabilir.
7. Release, heartbeat ve PR eşleme yalnız kayıt sahibi tarafından yapılır.
8. Manual override için görev, eski owner, yeni owner, gerekçe ve süreye bağlı HMAC-SHA256 imzalı approval token zorunludur.
9. Approver fail-closed registry allowlist'inde etkin ve süresi geçmemiş olmalı; eski veya yeni owner kendini onaylayamaz.
10. Override audit kaydı approver kimliği, approval kimliği, doğrulama yöntemi, doğrulama zamanı ve gerekçeyi içerir.
11. Acquire, queue, heartbeat, expiry, release, override ve PR eşleme olayları append-only audit kaydına yazılır.
12. Bozuk claim veya approver registry verisi fail-closed davranır; güvenilmeyen durumun üstüne yazılmaz.

## Kalıcılık

- `claims.json`: atomik olarak değiştirilen güncel projection.
- `claim_events.jsonl`: append-only denetim izi.
- `claims.lock`: süreçler arası atomiklik kilidi.

CLI ortak çalışma ağacını Git common directory üzerinden bulur. `LUMOS_BOARD_DIR` veya `--store` ile açık bir ortak konum da verilebilir.

Override doğrulamasında CLI `LUMOS_OVERRIDE_APPROVER_REGISTRY` ve `LUMOS_OVERRIDE_APPROVAL_SECRET` ortam değişkenlerini ister. CLI approval token üretmez; token yalnız güvenilen approval servisi tarafından oluşturulur.

Bu sözleşme görev sonucunun başka ajana, insana veya güvenlik akışına yönlendirilmesini tanımlamaz. Bilgi yönlendirme ayrı bir sonraki dilimdir.
