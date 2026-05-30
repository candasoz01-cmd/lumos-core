# DigitalOcean Test Sunucusu Durum Notu (2026-05-30)

Yeni test droplet oluşturuldu.

## Sunucu Bilgileri

- **Public IP:** 167.99.253.148
- **Hostname:** project-lumos-test
- **SSH erişimi:** root kullanıcı, port 443 aktif. Port 22 de açık ama Mac ağında timeout yaşandığı için pratik erişim 443 üzerinden yapılıyor.

## Backend

- **Backend path:** `/opt/lumos/backend`
- **PM2 process:** `lumos-backend`
- **Public health endpoint:** http://167.99.253.148:3000/health
- **Feed endpoint:** http://167.99.253.148:3000/posts?order=feed

## Güvenlik / Ağ

- **UFW aktif:** 22/tcp, 443/tcp, 3000/tcp izinli.

## Veritabanı

- **Prisma SQLite DB:** `backend/.env` içinde `DATABASE_URL="file:./prisma/dev.db"`
- `npx prisma db push` çalıştırıldı, schema senkron.

## Servis Yönetimi

- **PM2 startup aktif:** `pm2-root` systemd servisi enabled/running.

## Notlar

- Eski `project-lumos` droplet silinmedi; şimdilik park/referans durumda tutulacak.
- Bu sunucu test/erişim doğrulama sunucusudur; 512 MB RAM + 1 GB swap ile çalışıyor. Üretim veya ağır servis için ileride 1 GB RAM üstüne resize önerilir.

## Canlı API doğrulama

2026-05-30 tarihinde yeni test sunucusunda backend canlı doğrulandı.

Doğrulananlar:

- PM2 process: `lumos-backend` online
- Public health endpoint çalışıyor: http://167.99.253.148:3000/health
- Prisma SQLite DB schema senkronize edildi: `npx prisma db push`
- Test kullanıcı oluşturuldu: `username=test-user`
- Test post oluşturuldu: "Lumos backend test post"
- Feed endpoint çalıştı: http://167.99.253.148:3000/posts?order=feed
- Feed endpoint test postu döndürdü.

Notlar:

- Root path `/` için `Cannot GET /` dönmesi normal; backend API root route tanımlı değil.
- `/posts/feed` deprecated; doğru kullanım `/posts?order=feed`.
- Eski `EADDRINUSE` logları manuel `npm start` sürecinden kalmıştı; eski node process sonlandırıldı ve backend PM2 üzerinden temiz çalıştırıldı.
