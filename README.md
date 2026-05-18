# 🏥 Chatbot BPOM Lubuklinggau

Aplikasi chatbot interaktif untuk layanan informasi BPOM Lubuklinggau,
dengan tampilan mirip Shopee Chat — modern, responsif, dan mudah digunakan.

---

## 📁 Struktur Proyek

```
bpom_chatbot/
├── app.py                  ← Backend Flask (server utama)
├── requirements.txt        ← Daftar library Python
├── README.md
├── templates/
│   └── index.html          ← Halaman utama (frontend)
└── static/
    ├── css/
    │   └── style.css       ← Styling UI
    └── js/
        └── chat.js         ← Logika chat frontend
```

---

## 🚀 Cara Menjalankan di VS Code

### 1. Pastikan Python sudah terinstall
```bash
python --version
# atau
python3 --version
```

### 2. Buka folder proyek di VS Code
```
File → Open Folder → pilih folder bpom_chatbot
```

### 3. Buka Terminal di VS Code
```
Terminal → New Terminal
```

### 4. (Opsional) Buat Virtual Environment
```bash
python -m venv venv

# Aktivasi di Windows:
venv\Scripts\activate

# Aktivasi di Mac/Linux:
source venv/bin/activate
```

### 5. Install dependencies
```bash
pip install -r requirements.txt
```

### 6. Jalankan aplikasi
```bash
python app.py
```

### 7. Buka browser
```
http://127.0.0.1:5000
```

---

## ✨ Fitur Chatbot

| Fitur | Keterangan |
|-------|-----------|
| 💬 Chat Interaktif | Kirim pesan teks bebas |
| 🔘 Quick Reply | Tombol pilihan cepat seperti Shopee |
| 📋 Info Card | Kartu info kontak BPOM |
| 📱 Responsif | Tampilan optimal di desktop & mobile |
| 🔄 Reset Chat | Mulai percakapan ulang |
| 🧭 Sidebar Nav | Navigasi cepat ke topik |
| ⌨️ Typing Indicator | Animasi mengetik natural |

## 💬 Topik yang Bisa Ditanyakan

- **registrasi** — Prosedur pendaftaran produk
- **sertifikasi** — Sertifikasi CPOB/CPOTB/CPPB
- **cek produk** — Cara verifikasi produk BPOM
- **pengaduan** — Lapor produk ilegal/palsu
- **kontak** — Info kontak BPOM Lubuklinggau
- **tips** — Tips keamanan konsumen
- **regulasi** — Peraturan pangan, obat, kosmetik

---

## 🛠️ Teknologi

- **Backend:** Python + Flask
- **Frontend:** HTML5 + CSS3 + Vanilla JavaScript
- **Font:** Plus Jakarta Sans + Sora (Google Fonts)
- **No database required** — Data tersimpan di session & kode

---

## 📞 Kontak BPOM Lubuklinggau

- 📍 Jl. Yos Sudarso No. 12, Lubuklinggau, Sumatera Selatan
- ☎️ (0733) 325678
- 📧 bpom.lubuklinggau@pom.go.id  
- ⏰ Senin–Jumat: 08.00–16.00 WIB
- ☎️ Hotline Nasional: **1500533**
