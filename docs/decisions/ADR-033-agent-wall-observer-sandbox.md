<!-- markdownlint-disable MD013 -->

# ADR-033 — Agent Wall Observer: sandbox yürütme bağlamı

| Alan | Değer |
|------|-------|
| Karar durumu | **Accepted (2026-09-05)** — kurucu |
| Uygulama durumu | Sözleşme v0 yazıldı; runtime sandbox **yok** (ayrı dilim) |
| Tarih | 2026-09-05 |
| Kapsam muhasebesi | **KARAR** + **SÖZLEŞME**; KOD / CANLI yok |
| Üst ilişki | [agent-wall-observation-v1](../contracts/agent-wall-observation-v1.md); [agent-wall-observer-sandbox-v0](../contracts/agent-wall-observer-sandbox-v0.md); #831 observation design; #832 Faz-1 uygulama (merge adayı değil) |
| Merge kapısı | Security / execution-context. Standing low-risk hattı **uygun değil** |
| STOP | #832’ye yeni Git yönlendirme yaması **yok** |

---

## 1. Karar kaydı (kurucu metin)

> **Founder decision: A — sandbox.**  
> #832’ye yeni Git yönlendirme yamaları eklenmeyecek. Observer’ın Git çağrıları gerçek bir düşük-yetkili sandbox içinde çalıştırılacak. Sandbox; operatör kimlik bilgilerine, yazma yetkilerine ve gereksiz ağ erişimine sahip olmayacak. Observer hiçbir durumda izlediği ajanlardan daha fazla yetkiyle çalışmayacak. Mevcut `d5248e26` bu mimari karar uygulanana kadar merge adayı değildir. B/C/D reddedilmedi; fallback seçenekleri olarak kayıtta kalır.

## 2. Bağlam

#832 (Agent Wall observer Faz-1) observation-only ve runtime wire’sızdır. Buna rağmen Git’i claim worktree’sinde çalıştırmak, depo çözümleme/okuma modelindeki yönlendirme katmanlarını (gitfile, `commondir`, objects, nested `alternates`, …) ve `filter.*.clean` execution path’ini açar. Kod içi enumerate-jail yakınsamadı; Security/Bugbot head `d5248e26` üzerinde High residual bıraktı.

## 3. Seçenekler

| ID | Seçenek | Sonuç |
|----|---------|--------|
| A | Gerçek düşük-yetkili sandbox | **Kabul** |
| B | Trusted repo only | Fallback — Wall amacını daraltır |
| C | Index/stat (Git’siz) | Fallback — Git davranışını yeniden yazmak |
| D | Residual risk kabul + merge | Fallback — erken |

## 4. Sonuçlar

1. Birincil sınır: **sandbox yetenek tablosu** (`agent-wall-observer-sandbox-v0` §3).
2. #832 `d5248e26` merge adayı **değil** ta ki sandbox MVP kabul ölçütleri yeşil.
3. Yeni Git yönlendirme yaması politikası: **yasak** (A yürürlükteyken).
4. B/C/D kayıtta fallback kalır; sessizce “kabul ettik” denmez.
5. `worktree` + `gitdir` + `commondir` + “MUST NOT run with operator privileges” docs-only contract: #832 temiz kapanışından **sonra** ayrı PR (bu ADR’nin uygulama sırası §6).

## 5. Bilinçli yapılmayan

- Bu ADR ile runtime kod, wire, control, deploy yok.
- Guard “sandbox yazım dizini” sözleşmesiyle karıştırılmaz.
- Canonical / anayasa metni bu dilimde değişmez.

## 6. Sonraki dilimler

1. Docs-only: bu ADR + sandbox-v0 (bu PR).
2. Sandbox MVP uygulama + kanıt testleri.
3. #832 adapt (yama yok) → exact-head tekrar → insan merge.
4. Docs-only: untrusted execution context (`worktree`/`gitdir`/`commondir`, operator root, MUST NOT operator privileges).
5. Sonra küçük draft’lar (#833 → #834 → #835) review/ready.
