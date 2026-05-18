# 🚀 CARA SETUP CLOUDFLARE TUNNEL — Bot BPOM 24 Jam Online

## 🎯 Tujuan
Membuat chatbot Telegram BPOM dapat diakses **24 jam** tanpa perlu dashboard admin terbuka.

---

## ✅ Apa yang Sudah Diperbaiki

| Masalah Lama | Setelah Perbaikan |
|---|---|
| Pesan Telegram tidak dibalas jika dashboard ditutup | ✅ Bot auto-reply **langsung**, tanpa butuh dashboard |
| Pesan bebas hanya menunggu admin online | ✅ Bot memproses semua pesan secara otomatis |
| Server tidak siap untuk proxy Cloudflare | ✅ ProxyFix aktif, HTTPS terdeteksi dengan benar |
| `debug=True` tidak cocok untuk produksi | ✅ `debug=False`, stabil untuk 24 jam |

---

## 🔧 Langkah 1: Jalankan Bot (Cara Mudah — Windows)

Klik dua kali file **`start_bpom.bat`**

Script ini otomatis membuka:
- Jendela Flask (server chatbot)
- Jendela Cloudflare Tunnel (terowongan ke internet)

---

## 🔧 Langkah 2: Dapatkan URL Tunnel

Setelah `start_bpom.bat` dijalankan, lihat jendela **"Cloudflare Tunnel"**.
Akan muncul URL seperti:

```
https://abc-random-xyz.trycloudflare.com
```

Salin URL tersebut.

> ⚠️ **Quick Tunnel** (URL sementara) — berubah setiap kali dijalankan ulang.
> Untuk URL **permanen**, lihat Langkah 4 di bawah.

---

## 🔧 Langkah 3: Daftarkan Webhook ke Telegram

Ganti `URL_TUNNEL` dengan URL dari Langkah 2, lalu jalankan perintah ini di CMD:

```cmd
curl -X POST "https://api.telegram.org/bot8741328752:AAGFYg8fJMwnXwF18B_papxkItL_eVSyYJI/setWebhook" ^
  -H "Content-Type: application/json" ^
  -d "{\"url\": \"https://URL_TUNNEL/webhook/telegram\", \"secret_token\": \"bpom_secret_2024\"}"
```

Respon sukses:
```json
{"ok": true, "result": true, "description": "Webhook was set"}
```

Verifikasi:
```cmd
curl "https://api.telegram.org/bot8741328752:AAGFYg8fJMwnXwF18B_papxkItL_eVSyYJI/getWebhookInfo"
```

---

## 🔧 Langkah 4: URL Permanen (Untuk Produksi 24 Jam)

Quick Tunnel menghasilkan URL acak yang berubah. Untuk URL tetap:

### A. Login ke Cloudflare (gratis)
```cmd
cloudflared_exe.exe login
```
(Akan membuka browser, login dengan akun Cloudflare Anda)

### B. Buat Named Tunnel
```cmd
cloudflared_exe.exe tunnel create bpom-bot
```

### C. Buat File Konfigurasi

Buat file `cloudflare-config.yml` di folder yang sama:
```yaml
tunnel: bpom-bot
credentials-file: C:\Users\NAMAUSER\.cloudflared\bpom-bot.json

ingress:
  - service: http://localhost:5000
```

### D. Hubungkan Domain (Opsional)
```cmd
cloudflared_exe.exe tunnel route dns bpom-bot chatbot.domainanda.com
```

### E. Jalankan Named Tunnel
Edit `start_bpom.bat`, ubah baris:
```
set CF_TUNNEL_NAME=bpom-bot
```

Setelah ini, URL tunnel Anda **tidak akan berubah** dan webhook Telegram hanya perlu didaftarkan sekali.

---

## 🔄 Alur Kerja Bot (Setelah Perbaikan)

```
Pengguna Telegram ketik pesan
         │
         ▼
Telegram → webhook → Flask (app_websocket.py)
         │
         ▼
   get_bot_response()   ← LANGSUNG diproses, tanpa tunggu admin
         │
         ▼
Jawaban dikirim kembali ke Telegram
         │
         ▼ (paralel)
Dashboard dinotifikasi (hanya untuk monitoring)
```

Dashboard admin sekarang bersifat **opsional** — hanya untuk memantau percakapan dan membalas manual jika diperlukan.

---

## 🖥️ Cara Jalankan Manual (Tanpa start_bpom.bat)

### Terminal 1 — Flask:
```cmd
set TELEGRAM_BOT_TOKEN=8741328752:AAGFYg8fJMwnXwF18B_papxkItL_eVSyYJI
set TELEGRAM_WEBHOOK_SECRET=bpom_secret_2024
python app_websocket.py
```

### Terminal 2 — Cloudflare Tunnel:
```cmd
cloudflared_exe.exe tunnel --url http://localhost:5000
```

---

## ❓ Troubleshooting

| Masalah | Solusi |
|---|---|
| Bot tidak membalas | Cek `getWebhookInfo` — apakah URL tunnel masih aktif? |
| URL tunnel berubah | Gunakan Named Tunnel (Langkah 4) |
| `allow_unsafe_werkzeug` error | Update flask-socketio: `pip install -U flask-socketio` |
| WebSocket tidak konek di website | Pastikan Cloudflare tidak mem-block WebSocket (aktifkan di dashboard CF) |
| Dashboard tidak muncul sesi | Dashboard hanya monitoring — bot tetap menjawab meski dashboard ditutup |

---

## 📞 Kontak BPOM Lubuklinggau
- ☎️ (0733) 325678
- 📧 bpom.lubuklinggau@pom.go.id
- ☎️ Hotline: **1500533**
