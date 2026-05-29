# DigitalOcean SSH Erişim Kurtarma Notu

**Durum:** Plan / not (henüz SSH dış erişimi doğrulanmadı)

**Sınırlar:** Bu belge yalnızca dokümantasyon/not altyapısıdır. Mevcut çalışan koda, API’ye, veritabanına veya UI’ya dokunulmaz.

---

## Durum

- project-lumos droplet aktif.
- Public IP: 157.230.110.1
- Mac Terminal’den SSH denemesi port 22 timeout veriyor.
- DigitalOcean Web Console kararsız şekilde "All configured authentication methods failed" hatası verebiliyor.
- Root password reset sonrası Web Console üzerinden root erişimi bir kez sağlandı.
- SSH dış erişimi hâlâ doğrulanmadı.

---

## Amaç

- Droplet silinmeden, rebuild/destroy yapılmadan SSH erişimini geri kazanmak.
- Önce servis ve firewall kontrolü yapılacak.
- Veri kaybı riski olan işlemler yapılmayacak.

---

## Kurallar

- Destroy yok.
- Rebuild yok.
- Restore base image yok.
- Snapshot alınmadan riskli sistem değişikliği yok.
- Önce mevcut servis durumu okunacak.
- Sadece SSH erişimini geri getirecek minimum değişiklik yapılacak.

---

## Bir sonraki manuel işlem

DigitalOcean Web Console veya erişilebilir root shell içinde şu kontroller yapılacak:

```bash
systemctl status ssh --no-pager
systemctl enable --now ssh
ss -tlnp | grep ':22'
ufw status
iptables -S
cloud-init status
```

---

## Beklenen sonuç

- ssh servisi active/running olmalı.
- 22 portu LISTEN durumunda olmalı.
- ufw aktifse 22/tcp izinli olmalı.
- Dışarıdan Mac Terminal ile `ssh root@157.230.110.1` bağlantısı test edilmeli.

---

## Mac tarafı test komutu

```bash
ssh -i ~/.ssh/id_ed25519 -o ConnectTimeout=10 root@157.230.110.1
```

---

## Not

- `~/.ssh/id_ed25519.pub` mevcut ve lumos-core etiketiyle görünüyor.
- `id_rsa.pub` mevcut değil; bu normal.
- Public key DigitalOcean hesabına eklenmiş olsa bile mevcut droplet içine otomatik eklenmiş olmayabilir.
- Gerekirse root shell içinde `/root/.ssh/authorized_keys` kontrol edilecek.
