# 🚀 Panduan Integrasi WebSocket + Telegram Bot
## BPOM Lubuklinggau Chatbot

---

## 📁 File Baru yang Ditambahkan

```
bpom_chatbot/
├── app.py                          ← TIDAK DIUBAH (tetap berfungsi)
├── app_websocket.py                ← Backend baru (jalankan ini)
├── requirements_ws.txt             ← Dependency tambahan
├── templates/
│   ├── index.html                  ← TIDAK DIUBAH
│   └── dashboard.html              ← Dashboard admin BARU
└── static/
    ├── css/
    │   ├── style.css               ← TIDAK DIUBAH
    │   └── dashboard.css           ← Styling dashboard BARU
    └── js/
        ├── chat.js                 ← TIDAK DIUBAH
        └── chat_ws_patch.js        ← Patch WebSocket BARU
```

---

## 🔧 Langkah 1: Install Dependency Tambahan

```bash
pip install flask-socketio==5.3.6 eventlet==0.35.2
# Untuk Telegram:
pip install requests==2.31.0
```

Atau buat file `requirements_ws.txt`:
```
Flask==3.0.3
Werkzeug==3.0.3
flask-socketio==5.3.6
eventlet==0.35.2
requests==2.31.0
```

Lalu:
```bash
pip install -r requirements_ws.txt
```

---

## 🔧 Langkah 2: Aktifkan WebSocket di index.html

Tambahkan dua baris di bagian bawah `index.html`, SEBELUM `</body>`:

```html
<!-- Tambahkan ini setelah <script src="...chat.js"></script> -->
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<script src="{{ url_for('static', filename='js/chat_ws_patch.js') }}"></script>
```

> ⚠️ JANGAN hapus `<script src="...chat.js">` — chat_ws_patch.js bergantung padanya.

---

## 🤖 Langkah 3: Buat Telegram Bot

1. Buka Telegram, cari **@BotFather**
2. Kirim `/newbot`
3. Ikuti instruksi → dapatkan **BOT_TOKEN** (format: `1234567890:AAxxxxxx`)
4. Simpan token ini dengan aman

---

## 🌐 Langkah 4: Setup Webhook Telegram

Telegram memerlukan URL **HTTPS publik**. Untuk development lokal:

### Opsi A: Menggunakan ngrok (disarankan untuk lokal)

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 5000
# Salin URL https, contoh: https://abc123.ngrok.io
```

### Opsi B: Server VPS/Cloud (produksi)
Gunakan URL server Anda, pastikan HTTPS aktif.

### Daftarkan Webhook ke Telegram

```bash
# Ganti TOKEN dan URL_PUBLIK sesuai milik Anda
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://<URL_PUBLIK>/webhook/telegram",
    "secret_token": "bpom_secret_2024"
  }'
```

Respon sukses:
```json
{"ok": true, "result": true, "description": "Webhook was set"}
```

### Verifikasi Webhook

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

---

## ▶️ Langkah 5: Jalankan Aplikasi

### Windows (CMD):
```cmd
set TELEGRAM_BOT_TOKEN=1234567890:AAxxxxxx
set TELEGRAM_WEBHOOK_SECRET=bpom_secret_2024
python app_websocket.py
```

### Mac / Linux:
```bash
export TELEGRAM_BOT_TOKEN="1234567890:AAxxxxxx"
export TELEGRAM_WEBHOOK_SECRET="bpom_secret_2024"
python app_websocket.py
```

### Output yang diharapkan:
```
============================================================
  BPOM Lubuklinggau — WebSocket + Telegram Edition
  Chatbot  : http://127.0.0.1:5000
  Dashboard: http://127.0.0.1:5000/dashboard
  Setup TG : http://127.0.0.1:5000/setup/telegram
============================================================
```

---

## 📊 Akses Dashboard Admin

Buka browser: **http://127.0.0.1:5000/dashboard**

### Fitur Dashboard:
| Fitur | Keterangan |
|-------|-----------|
| 📊 Statistik real-time | Total sesi, pesan, sumber |
| 🔄 Pembaruan otomatis | Sesi baru muncul tanpa reload |
| 🌐 Filter Web/Telegram | Pisahkan sumber pesan |
| 💬 Riwayat percakapan | Lihat semua pesan per sesi |
| 👨‍💼 Balasan manual | Admin dapat membalas langsung |
| 🔔 Notifikasi toast | Alert pesan masuk baru |
| ✈️ Sinkronisasi Telegram | Balasan terkirim ke Telegram |

---

## 🔄 Cara Kerja Sistem

```
Pengguna Web                    Server Flask                  Telegram
    │                               │                              │
    │──── WebSocket (chat) ────────►│                              │
    │                               │─── get_bot_response() ───────│
    │◄─── bot_reply (WS) ──────────│                              │
    │                               │                              │
    │                            Dashboard◄── new_web_message ─────│
    │                               │                              │
    │                               │◄──── Update Telegram ────────│
    │                               │─── send_telegram_message() ──►
    │                               │                              │
    │◄─── admin_reply (WS) ────────│◄── Dashboard reply ──────────│
```

---

## 🛠️ Konfigurasi Tambahan

### Menggunakan .env file (disarankan):

Install `python-dotenv`:
```bash
pip install python-dotenv
```

Buat file `.env` di root proyek:
```env
TELEGRAM_BOT_TOKEN=1234567890:AAxxxxxx
TELEGRAM_WEBHOOK_SECRET=ganti_dengan_string_acak_anda
FLASK_SECRET_KEY=bpom_lubuklinggau_secret_2024
```

Tambahkan di awal `app_websocket.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

### Untuk produksi (Redis sebagai message broker):
```bash
pip install redis flask-socketio[redis]
```

Ubah di `app_websocket.py`:
```python
socketio = SocketIO(app, message_queue="redis://localhost:6379")
```

---

## ❓ Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `ModuleNotFoundError: flask_socketio` | `pip install flask-socketio` |
| WebSocket tidak connect | Periksa port 5000 tidak diblokir firewall |
| Telegram webhook gagal | Pastikan URL HTTPS dan dapat diakses publik |
| Pesan tidak muncul di dashboard | Refresh halaman, periksa konsol browser |
| `eventlet` error di Windows | Coba ganti `async_mode="threading"` di app_websocket.py |

---

## 📞 Kontak BPOM Lubuklinggau

- 📍 Jl. Yos Sudarso No. 12, Lubuklinggau, Sumatera Selatan
- ☎️ (0733) 325678
- 📧 bpom.lubuklinggau@pom.go.id
- ☎️ Hotline: **1500533**
