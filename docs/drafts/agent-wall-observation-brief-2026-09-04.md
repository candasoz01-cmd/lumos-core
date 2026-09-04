# Agent Wall gözlem katmanı — iş paketi (tasarım, kod yok)

| Alan | Değer |
| --- | --- |
| Durum | AÇIK — üçüncü paralel iş; bu dosya yalnızca kapsam |
| Kod yazma | Bu dilimde **yok** |
| Bekleme | `#807` Wall `claim_cli list` / `waiting_on` maskesi hâlâ draft; gözlem katmanı o PR'ı parçalamaz |
| Üst ilişki | [task-claim-v1.md](../contracts/task-claim-v1.md); CONSTITUTION §3 dosya sahipliği |

## Neden

Wall bugün çakışmayı **önler** (claim, `waiting_on`, kapsam). METR sınıfı sapma: ajan doğru claim ile başlar, sonra hız, hedef veya dosya kümesi sapar ve kimse görmez. Başarı ölçütü hâlâ: ajan adı söylemeden iş doğru kişiye gider ve ezilmez — gözlem o ölçütü kanıtlar.

## Tasarımda cevaplanacak sorular (koddan önce)

1. **Anormal çağrı oranı** — hangi olay (claim heartbeat, git yazma, `gh`, ağ)? pencere ve eşik kimin politikası?
2. **Beklenmeyen hedef** — repo/host/PR allowlist dışı erişim nasıl fail-closed kayda düşer?
3. **Claim dışı dosya dokunuşu** — worktree `git status` / path vs claim `scopes`; false positive (generated, lockfile)?
4. **Ajan başına bütçe** — token/araç çağrısı; aşım `waiting_on` mi, kesme mi?
5. **Sessiz sapma** — heartbeat var, iş yok; veya kapsam dar, diff geniş.

Çıktı bir ADR adayı veya `task-claim-v1` eki olmalı; yeni kanonik belge açılmadan önce dört belgeye sığıp sığmadığı sorulur.

## Dokunulmayacaklar

- `#807` dalı ve eski worktree
- `#829` `panel_tasks_server.py` / Origin testi / `TECHNICAL_DEBT.md` satırı
- TD-24 Faz-2 `src/panel_tasks_auth` (Cursor claim)

## Teslim

En fazla bir tasarım notu + açık karar listesi. Uygulama ayrı claim, `#807` merge veya maske sözleşmesi netleşince.
