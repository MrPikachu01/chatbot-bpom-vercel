"""
app_websocket.py — BPOM Lubuklinggau Chatbot
WebSocket (Flask-SocketIO) + Telegram Bot API
Jalankan: python app_websocket.py

Install: pip install -r requirements.txt
"""

# ── Threading mode: kompatibel Python 3.8 hingga 3.14+ ──────────────────────
# gevent & eventlet belum stabil di Python 3.13/3.14 — gunakan threading.
ASYNC_MODE = "threading"
print("[SocketIO] Threading mode aktif — kompatibel Python 3.14")
# ────────────────────────────────────────────────────────────────────────────

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
from typing import Union
import uuid
import os
import hmac
import hashlib
import json
import threading

# ── Import semua logika chatbot dari app.py asli ──────────────────────────────
# app.py TIDAK diubah sama sekali; kita re-import modul-nya
import importlib.util, sys

_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
_spec = importlib.util.spec_from_file_location("original_app", _app_path)
_orig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_orig)

BPOM_DATA   = _orig.BPOM_DATA
QUICK_MENUS = _orig.QUICK_MENUS
get_bot_response = _orig.get_bot_response
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = "bpom_lubuklinggau_secret_2024"

# ── ProxyFix: wajib untuk Cloudflare Tunnel ─────────────────────────────────
# Cloudflare Tunnel meneruskan request via proxy — tanpa ini, HTTPS tidak
# terdetekur dengan benar dan session/cookie bisa bermasalah.
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# ── Konfigurasi SocketIO ────────────────────────────────────────────────────
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode=ASYNC_MODE,
    logger=False,
    engineio_logger=False,
    ping_timeout=20,
    ping_interval=10,
)

# ── Konfigurasi Telegram ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN", "8741328752:AAGFYg8fJMwnXwF18B_papxkItL_eVSyYJI")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "bpom_secret_2024")
TELEGRAM_API_BASE       = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ── Penyimpanan in-memory (ganti Redis/DB untuk produksi) ─────────────────────
# Struktur: { session_id: { "messages": [...], "menu": str, "source": "web"|"telegram" } }
active_sessions: dict = {}

# Mapping telegram chat_id → internal session_id
telegram_session_map: dict = {}

# Antrian pesan masuk dari Telegram (untuk di-relay ke dashboard)
telegram_inbox: list = []


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_or_create_session(session_id: str, source: str = "web") -> dict:
    if session_id not in active_sessions:
        active_sessions[session_id] = {
            "id": session_id,
            "source": source,
            "menu": "main",
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
        }
    active_sessions[session_id]["last_active"] = datetime.now().isoformat()
    return active_sessions[session_id]


def save_message(session_id: str, role: str, text: str, source: str = "web"):
    sess = get_or_create_session(session_id, source)
    msg = {
        "id": str(uuid.uuid4()),
        "role": role,           # "user" | "bot" | "admin"
        "text": text,
        "timestamp": datetime.now().strftime("%H:%M"),
        "source": source,       # "web" | "telegram" | "dashboard"
    }
    sess["messages"].append(msg)
    return msg


# ── Reply Keyboard (tombol permanen di bawah chat) ───────────────────────────
MAIN_REPLY_KEYBOARD = {
    "keyboard": [
        [{"text": "Beranda"}],
        [{"text": "Registrasi Produk"}, {"text": "Layanan BPOM"}],
        [{"text": "Pengaduan"},         {"text": "Kontak BPOM"}],
        [{"text": "Cek Produk BPOM"},   {"text": "Tips Keamanan"}],
    ],
    "resize_keyboard": True,
    "persistent": True,
    "input_field_placeholder": "Pilih menu atau ketik pesan..."
}

# Sub-menu Registrasi
REGISTRASI_KEYBOARD = {
    "keyboard": [
        [{"text": "Prosedur Registrasi"}],
        [{"text": "Syarat Registrasi"}, {"text": "Biaya Registrasi"}],
        [{"text": "Hubungi Petugas"},   {"text": "Daftar Online"}],
        [{"text": "<< Menu Utama"}],
    ],
    "resize_keyboard": True, "persistent": True,
}

# Sub-menu Cek Produk
CEK_PRODUK_KEYBOARD = {
    "keyboard": [
        [{"text": "Cara Cek via Aplikasi"}],
        [{"text": "Arti Kode Registrasi"}, {"text": "Produk Berbahaya"}],
        [{"text": "Cek Sekarang Online"},  {"text": "<< Menu Utama"}],
    ],
    "resize_keyboard": True, "persistent": True,
}

# Sub-menu Pengaduan
PENGADUAN_KEYBOARD = {
    "keyboard": [
        [{"text": "Produk Ilegal/Palsu"}],
        [{"text": "Produk Kedaluwarsa"}, {"text": "Efek Samping"}],
        [{"text": "Iklan Menyesatkan"},  {"text": "Pengaduan Lainnya"}],
        [{"text": "Cara Melapor"},       {"text": "Kontak Pengaduan"}],
        [{"text": "<< Menu Utama"}],
    ],
    "resize_keyboard": True, "persistent": True,
}

# Sub-menu Tips Keamanan
TIPS_KEYBOARD = {
    "keyboard": [
        [{"text": "Cek Label Produk"},    {"text": "Cek Tanggal Kedaluwarsa"}],
        [{"text": "Kenali Produk Palsu"}, {"text": "Tips Beli Online"}],
        [{"text": "Tips Obat Aman"},      {"text": "Tips Kosmetik Aman"}],
        [{"text": "<< Menu Utama"}],
    ],
    "resize_keyboard": True, "persistent": True,
}

# Sub-menu Regulasi
REGULASI_KEYBOARD = {
    "keyboard": [
        [{"text": "Regulasi Pangan"},    {"text": "Regulasi Obat"}],
        [{"text": "Regulasi Kosmetik"},  {"text": "Regulasi Alkes"}],
        [{"text": "Download Peraturan"}, {"text": "<< Menu Utama"}],
    ],
    "resize_keyboard": True, "persistent": True,
}

# ── Keyboard Layanan Sertifikasi (harus sebelum MENU_RESPONSES) ──────────────
LAYANAN_KEYBOARD = {
    "keyboard": [
        [{"text": "Sertifikasi CPKB Kosmetik"}],
        [{"text": "Sertifikasi CPOTB Obat Tradisional"}],
        [{"text": "Sertifikasi CDOB Distribusi Obat"}],
        [{"text": "Rekomendasi Notifikasi Kosmetik"}],
        [{"text": "Izin CPPOB Pangan Olahan"}],
        [{"text": "<< Menu Utama"}],
    ],
    "resize_keyboard": True,
    "persistent": True,
}

NL = chr(10)

# Peta teks tombol → (respon, keyboard berikutnya)
MENU_RESPONSES = {
    # ── Menu Utama ────────────────────────────────────────────────────────
    "Registrasi Produk":      ("*Registrasi Produk BPOM*" + NL + NL + "Silakan pilih informasi yang Anda butuhkan:", REGISTRASI_KEYBOARD),
    "Cek Produk BPOM":        ("*Cek Produk BPOM*" + NL + NL + "Pilih informasi yang Anda butuhkan:", CEK_PRODUK_KEYBOARD),
    "Pengaduan":               ("*Layanan Pengaduan BPOM*" + NL + NL + "Silakan pilih jenis pengaduan:", PENGADUAN_KEYBOARD),
    "Tips Keamanan":           ("*Tips Keamanan Konsumen*" + NL + NL + "Pilih topik tips keamanan:", TIPS_KEYBOARD),
    "Kontak BPOM":             ("*Kontak BPOM Lubuklinggau*" + NL + NL + "Alamat: Jl. Yos Sudarso No. 12" + NL + "Telp: (0733) 325678" + NL + "Email: bpom.lubuklinggau@pom.go.id" + NL + "Jam: Senin-Jumat 08.00-16.00 WIB" + NL + NL + "Hotline Nasional: *1500533*" + NL + "WhatsApp: 08121 9999 533", MAIN_REPLY_KEYBOARD),
    "Regulasi":                ("*Regulasi & Peraturan BPOM*" + NL + NL + "Pilih kategori regulasi:", REGULASI_KEYBOARD),
    "<< Menu Utama":           ("*Menu Utama BPOM Lubuklinggau*" + NL + NL + "Silakan pilih layanan:", MAIN_REPLY_KEYBOARD),

    # ── Beranda ────────────────────────────────────────────────────────────
    "Beranda": (
        "*Selamat Datang di Layanan Bot BPOM Lubuklinggau!*" + NL + NL +
        "Halo! Saya asisten virtual resmi BPOM Lubuklinggau." + NL +
        "Saya siap membantu Anda dengan:" + NL + NL +
        "- Registrasi & sertifikasi produk" + NL +
        "- Pengecekan keamanan produk" + NL +
        "- Layanan sertifikasi BPOM" + NL +
        "- Pengaduan produk ilegal/berbahaya" + NL +
        "- Kontak dan informasi BPOM" + NL + NL +
        "Silakan pilih menu di bawah:",
        MAIN_REPLY_KEYBOARD
    ),

    # ── Layanan BPOM ───────────────────────────────────────────────────────
    "Layanan BPOM": (
        "*Layanan Sertifikasi BPOM Lubuklinggau*" + NL + NL +
        "Pilih layanan sertifikasi yang Anda butuhkan:",
        LAYANAN_KEYBOARD
    ),

    # ── Sub-menu item layanan ──────────────────────────────────────────────
    "Sertifikasi CPKB Kosmetik": (
        "*Sertifikasi Cara Pembuatan Kosmetik yang Baik (CPKB)*" + NL + NL +
        "Sertifikasi bagi industri kosmetik memenuhi persyaratan CPKB." + NL + NL +
        "*Prosedur:*" + NL +
        "1. Ajukan permohonan ke kantor BPOM Lubuklinggau" + NL +
        "2. Lengkapi dokumen persyaratan administrasi" + NL +
        "3. Tim BPOM melakukan inspeksi fasilitas produksi" + NL +
        "4. Evaluasi dan tindak lanjut temuan inspeksi" + NL +
        "5. Penerbitan Sertifikat CPKB" + NL + NL +
        "*Persyaratan:*" + NL +
        "- Izin usaha industri kosmetik" + NL +
        "- Fasilitas produksi sesuai standar CPKB" + NL +
        "- Sistem manajemen mutu terdokumentasi" + NL +
        "- Tenaga ahli kosmetologi/farmasi" + NL + NL +
        "Info: (0733) 325678 | bpom.lubuklinggau@pom.go.id",
        LAYANAN_KEYBOARD
    ),
    "Sertifikasi CPOTB Obat Tradisional": (
        "*Sertifikasi Cara Pembuatan Obat Tradisional yang Baik (CPOTB)*" + NL + NL +
        "Sertifikasi CPOTB bagi industri obat tradisional." + NL + NL +
        "*Prosedur:*" + NL +
        "1. Ajukan permohonan ke kantor BPOM Lubuklinggau" + NL +
        "2. Siapkan dokumen izin usaha & sistem manajemen mutu" + NL +
        "3. Tim BPOM melakukan audit fasilitas produksi" + NL +
        "4. Evaluasi sistem pengawasan mutu" + NL +
        "5. Penerbitan Sertifikat CPOTB" + NL + NL +
        "*Persyaratan:*" + NL +
        "- Izin usaha industri obat tradisional/jamu" + NL +
        "- Fasilitas produksi sesuai standar CPOTB" + NL +
        "- Apoteker sebagai penanggung jawab" + NL + NL +
        "Pengaduan: Hotline *1500533* | halobpom@pom.go.id",
        LAYANAN_KEYBOARD
    ),
    "Sertifikasi CDOB Distribusi Obat": (
        "*Sertifikasi Cara Distribusi Obat yang Baik (CDOB)*" + NL + NL +
        "Sertifikasi bagi distributor/pedagang besar farmasi." + NL + NL +
        "*Prosedur:*" + NL +
        "1. Permohonan sertifikasi CDOB ke BPOM" + NL +
        "2. Verifikasi dokumen administrasi" + NL +
        "3. Inspeksi fasilitas distribusi" + NL +
        "4. Evaluasi CAPA (Corrective Action)" + NL +
        "5. Penerbitan Sertifikat CDOB (berlaku 5 tahun)" + NL + NL +
        "*Persyaratan:*" + NL +
        "- Izin Pedagang Besar Farmasi (PBF)" + NL +
        "- Fasilitas penyimpanan sesuai standar" + NL +
        "- Apoteker sebagai penanggung jawab" + NL + NL +
        "Info: (0733) 325678 | bpom.lubuklinggau@pom.go.id",
        LAYANAN_KEYBOARD
    ),
    "Rekomendasi Notifikasi Kosmetik": (
        "*Penerbitan Rekomendasi Notifikasi Kosmetik*" + NL + NL +
        "Rekomendasi bagi pemohon notifikasi kosmetik ke BPOM Pusat." + NL + NL +
        "*Prosedur:*" + NL +
        "1. Daftar di notifikasikosmetik.pom.go.id" + NL +
        "2. Lengkapi data perusahaan dan produk" + NL +
        "3. Ajukan permohonan ke BPOM Lubuklinggau" + NL +
        "4. Verifikasi dokumen oleh petugas" + NL +
        "5. Rekomendasi diterbitkan 3-5 hari kerja" + NL + NL +
        "*Persyaratan:*" + NL +
        "- Badan usaha berbadan hukum" + NL +
        "- Penanggung jawab teknis (Apoteker)" + NL +
        "- Formula/komposisi produk lengkap" + NL + NL +
        "Web: notifikasikosmetik.pom.go.id",
        LAYANAN_KEYBOARD
    ),
    "Izin CPPOB Pangan Olahan": (
        "*Penerbitan Izin Penerapan CPPOB*" + NL + NL +
        "Izin Cara Produksi Pangan Olahan yang Baik bagi industri pangan." + NL + NL +
        "*Prosedur:*" + NL +
        "1. Permohonan izin CPPOB ke BPOM Lubuklinggau" + NL +
        "2. Penilaian dokumen sistem manajemen pangan" + NL +
        "3. Inspeksi sarana produksi pangan" + NL +
        "4. Evaluasi GMP (Good Manufacturing Practice)" + NL +
        "5. Penerbitan izin CPPOB (berlaku 5 tahun)" + NL + NL +
        "*Persyaratan:*" + NL +
        "- Izin usaha industri pangan (SIUP/NIB)" + NL +
        "- Sistem HACCP terdokumentasi" + NL +
        "- Tenaga ahli teknologi pangan" + NL + NL +
        "Info: ereg.pom.go.id | (0733) 325678",
        LAYANAN_KEYBOARD
    ),

    # ── Sub-menu Registrasi ───────────────────────────────────────────────
    "Prosedur Registrasi":     ("*Prosedur Registrasi Produk*" + NL + NL + "1. Daftar akun di e-reg.pom.go.id" + NL + "2. Login dan pilih jenis produk" + NL + "3. Isi data produk & perusahaan" + NL + "4. Upload dokumen persyaratan" + NL + "5. Bayar PNBP sesuai tarif" + NL + "6. Tunggu evaluasi 3-14 hari kerja" + NL + "7. Nomor izin edar diterbitkan", REGISTRASI_KEYBOARD),
    "Syarat Registrasi":       ("*Dokumen Persyaratan Registrasi*" + NL + NL + "Dokumen wajib:" + NL + "- NIB (Nomor Induk Berusaha)" + NL + "- NPWP perusahaan" + NL + "- Sertifikat GMP/CPOTB/CPPB" + NL + "- Hasil uji laboratorium" + NL + "- Desain label produk" + NL + "- Komposisi/formula produk" + NL + NL + "Info lengkap: e-reg.pom.go.id", REGISTRASI_KEYBOARD),
    "Biaya Registrasi":        ("*Biaya Registrasi (PNBP)*" + NL + NL + "Sesuai PP No. 32 Tahun 2017:" + NL + "- Pangan olahan: Rp 100.000-500.000" + NL + "- Kosmetik: Rp 500.000-1.500.000" + NL + "- Obat tradisional: Rp 150.000-1.000.000" + NL + "- Suplemen: Rp 500.000-1.500.000" + NL + "- Obat: Rp 1.000.000-5.000.000" + NL + NL + "Pembayaran via bank persepsi.", REGISTRASI_KEYBOARD),
    "Hubungi Petugas":         ("*Hubungi Petugas Registrasi*" + NL + NL + "Untuk konsultasi registrasi produk:" + NL + NL + "Telp: (0733) 325678" + NL + "Email: bpom.lubuklinggau@pom.go.id" + NL + "Jam: Senin-Jumat 08.00-16.00 WIB" + NL + NL + "Datang langsung ke:" + NL + "Jl. Yos Sudarso No. 12, Lubuklinggau", REGISTRASI_KEYBOARD),
    "Daftar Online":           ("*Daftar Registrasi Online*" + NL + NL + "Langkah daftar online:" + NL + "1. Buka: *e-reg.pom.go.id*" + NL + "2. Klik Daftar Baru" + NL + "3. Isi data perusahaan" + NL + "4. Verifikasi email" + NL + "5. Login dan mulai proses registrasi" + NL + NL + "Atau scan QR di kantor BPOM setempat.", REGISTRASI_KEYBOARD),

    # ── Sub-menu Cek Produk ───────────────────────────────────────────────
    "Cara Cek via Aplikasi":   ("*Cara Cek Produk via Aplikasi*" + NL + NL + "Gunakan aplikasi *BPOM Mobile*:" + NL + "1. Download di Play Store/App Store" + NL + "2. Buka aplikasi" + NL + "3. Klik Cek Produk" + NL + "4. Scan barcode atau ketik nomor izin" + NL + "5. Lihat status keamanan produk" + NL + NL + "Website: *cekbpom.pom.go.id*", CEK_PRODUK_KEYBOARD),
    "Arti Kode Registrasi":    ("*Arti Kode Registrasi BPOM*" + NL + NL + "Kode pada kemasan produk:" + NL + "- *BPOM RI MD* = Produk dalam negeri" + NL + "- *BPOM RI ML* = Produk impor" + NL + "- *BPOM RI TR* = Obat tradisional" + NL + "- *BPOM RI NA* = Kosmetik dalam negeri" + NL + "- *BPOM RI NC* = Kosmetik impor" + NL + "- *BPOM RI SD* = Suplemen dalam negeri" + NL + NL + "Waspada jika tidak ada kode BPOM!", CEK_PRODUK_KEYBOARD),
    "Produk Berbahaya":        ("*Ciri Produk Berbahaya/Ilegal*" + NL + NL + "Waspadai produk dengan ciri:" + NL + "- Tidak ada nomor izin edar BPOM" + NL + "- Harga jauh di bawah pasaran" + NL + "- Klaim berlebihan (sembuh total, dll)" + NL + "- Label tidak berbahasa Indonesia" + NL + "- Kemasan mudah rusak/tidak rapi" + NL + "- Dijual tidak di tempat resmi" + NL + NL + "Laporkan ke hotline: *1500533*", CEK_PRODUK_KEYBOARD),
    "Cek Sekarang Online":     ("*Cek Produk Online*" + NL + NL + "Cara cek produk secara online:" + NL + NL + "1. Buka: *cekbpom.pom.go.id*" + NL + "2. Masukkan nama produk atau" + NL + "   nomor izin edar" + NL + "3. Klik Cari" + NL + "4. Lihat detail produk & status" + NL + NL + "Produk tidak ditemukan? Segera laporkan!", CEK_PRODUK_KEYBOARD),

    # ── Sub-menu Pengaduan ────────────────────────────────────────────────
    "Produk Ilegal/Palsu":     ("*Laporan Produk Ilegal/Palsu*" + NL + NL + "Cara melapor produk ilegal:" + NL + "1. Foto produk & kemasan" + NL + "2. Catat nama, merk, lokasi beli" + NL + "3. Hubungi: *1500533*" + NL + "4. Atau email: halobpom@pom.go.id" + NL + "5. Atau lapor via aplikasi BPOM Mobile" + NL + NL + "Laporan Anda sangat membantu!", PENGADUAN_KEYBOARD),
    "Produk Kedaluwarsa":      ("*Laporan Produk Kedaluwarsa*" + NL + NL + "Temukan produk kedaluwarsa di toko?" + NL + NL + "Langkah pelaporan:" + NL + "1. Foto produk & tanggal kedaluwarsa" + NL + "2. Catat nama toko & alamat" + NL + "3. Hubungi: *1500533*" + NL + "4. WhatsApp: 08121 9999 533" + NL + NL + "Jam layanan: 08.00-20.00 WIB", PENGADUAN_KEYBOARD),
    "Efek Samping":            ("*Laporan Efek Samping Produk*" + NL + NL + "Alami efek samping setelah" + NL + "menggunakan produk?" + NL + NL + "Segera:" + NL + "1. Hentikan penggunaan produk" + NL + "2. Periksakan ke dokter" + NL + "3. Catat nama & nomor batch produk" + NL + "4. Lapor ke: *1500533*" + NL + "5. Email: halobpom@pom.go.id", PENGADUAN_KEYBOARD),
    "Iklan Menyesatkan":       ("*Laporan Iklan Menyesatkan*" + NL + NL + "Temukan iklan produk yang menyesatkan?" + NL + NL + "Langkah pelaporan:" + NL + "1. Screenshot/foto iklan tersebut" + NL + "2. Catat media & tanggal tayang" + NL + "3. Hubungi: *1500533*" + NL + "4. Email: halobpom@pom.go.id" + NL + "5. Website: www.pom.go.id", PENGADUAN_KEYBOARD),
    "Pengaduan Lainnya":       ("*Pengaduan Lainnya*" + NL + NL + "Untuk pengaduan selain kategori di atas:" + NL + NL + "Hubungi kami melalui:" + NL + "- Hotline: *1500533*" + NL + "- WhatsApp: 08121 9999 533" + NL + "- Email: halobpom@pom.go.id" + NL + "- Datang langsung ke kantor" + NL + NL + "Jam layanan: 08.00-20.00 WIB", PENGADUAN_KEYBOARD),
    "Cara Melapor":            ("*Cara Melapor Pengaduan*" + NL + NL + "5 cara menyampaikan pengaduan:" + NL + NL + "1. Hotline: *1500533*" + NL + "2. WhatsApp: 08121 9999 533" + NL + "3. Email: halobpom@pom.go.id" + NL + "4. Aplikasi BPOM Mobile" + NL + "5. Datang ke kantor BPOM" + NL + NL + "Semua laporan ditindaklanjuti!", PENGADUAN_KEYBOARD),
    "Kontak Pengaduan":        ("*Kontak Layanan Pengaduan*" + NL + NL + "Hotline Nasional: *1500533*" + NL + "WhatsApp: 08121 9999 533" + NL + "Email: halobpom@pom.go.id" + NL + "Website: www.pom.go.id" + NL + NL + "BPOM Lubuklinggau:" + NL + "Telp: (0733) 325678" + NL + "Jam: Senin-Jumat 08.00-16.00 WIB", PENGADUAN_KEYBOARD),

    # ── Sub-menu Tips Keamanan ────────────────────────────────────────────
    "Cek Label Produk":        ("*Tips Cek Label Produk*" + NL + NL + "Label produk yang aman wajib ada:" + NL + "- Nama & merk produk" + NL + "- Komposisi/bahan" + NL + "- Nomor izin edar BPOM" + NL + "- Tanggal produksi & kedaluwarsa" + NL + "- Nama & alamat produsen" + NL + "- Cara penggunaan & penyimpanan" + NL + "- Netto/isi bersih" + NL + NL + "Jika tidak lengkap, jangan beli!", TIPS_KEYBOARD),
    "Cek Tanggal Kedaluwarsa": ("*Tips Cek Tanggal Kedaluwarsa*" + NL + NL + "Selalu periksa sebelum membeli:" + NL + NL + "- Cari tulisan EXP/Exp Date/Kedaluwarsa" + NL + "- Format: DD/MM/YYYY atau MM/YYYY" + NL + "- Jangan beli jika sudah lewat" + NL + "- Hindari produk tanpa tanggal" + NL + "- Perhatikan kondisi kemasan" + NL + NL + "Produk kedaluwarsa bisa berbahaya!", TIPS_KEYBOARD),
    "Kenali Produk Palsu":     ("*Cara Mengenali Produk Palsu*" + NL + NL + "Tanda-tanda produk palsu:" + NL + "- Harga jauh lebih murah" + NL + "- Kemasan mudah rusak/lecek" + NL + "- Tulisan/logo tidak rapi" + NL + "- Tidak ada nomor BPOM" + NL + "- Nomor BPOM tidak terdaftar" + NL + "- Dijual di tempat tidak resmi" + NL + NL + "Cek keaslian di cekbpom.pom.go.id", TIPS_KEYBOARD),
    "Tips Beli Online":        ("*Tips Aman Beli Produk Online*" + NL + NL + "Sebelum membeli online:" + NL + "1. Cek toko resmi/terverifikasi" + NL + "2. Baca ulasan pembeli lain" + NL + "3. Cek nomor izin edar BPOM" + NL + "4. Waspada harga tidak wajar" + NL + "5. Periksa kemasan saat terima" + NL + "6. Laporkan jika produk mencurigakan" + NL + NL + "Belanja aman di marketplace resmi!", TIPS_KEYBOARD),
    "Tips Obat Aman":          ("*Tips Penggunaan Obat Aman*" + NL + NL + "Gunakan obat dengan benar:" + NL + "- Beli obat di apotek resmi" + NL + "- Baca aturan pakai dengan teliti" + NL + "- Jangan konsumsi melebihi dosis" + NL + "- Simpan sesuai petunjuk" + NL + "- Jangan berikan obat dewasa ke anak" + NL + "- Konsultasi dokter untuk obat keras" + NL + NL + "Ingat: DAGUSIBU (Dapatkan, Gunakan," + NL + "Simpan, Buang)", TIPS_KEYBOARD),
    "Tips Kosmetik Aman":      ("*Tips Penggunaan Kosmetik Aman*" + NL + NL + "Pilih kosmetik yang tepat:" + NL + "- Cek nomor izin BPOM (NA/NC)" + NL + "- Baca komposisi bahan" + NL + "- Hindari merkuri, hidrokuinon" + NL + "- Lakukan uji patch sebelum pakai" + NL + "- Perhatikan tanggal kedaluwarsa" + NL + "- Hentikan jika iritasi" + NL + NL + "Cantik itu sehat, bukan berbahaya!", TIPS_KEYBOARD),

    # ── Sub-menu Regulasi ─────────────────────────────────────────────────
    "Regulasi Pangan":         ("*Regulasi Pangan BPOM*" + NL + NL + "Peraturan utama pangan:" + NL + "- UU No. 18/2012 tentang Pangan" + NL + "- PP No. 69/1999 tentang Label Pangan" + NL + "- Peraturan BPOM No. 27/2017" + NL + "  tentang Pendaftaran Pangan Olahan" + NL + "- Peraturan BPOM No. 22/2019" + NL + "  tentang Informasi Nilai Gizi" + NL + NL + "Lengkap: jdih.pom.go.id", REGULASI_KEYBOARD),
    "Regulasi Obat":           ("*Regulasi Obat BPOM*" + NL + NL + "Peraturan utama obat:" + NL + "- UU No. 36/2009 tentang Kesehatan" + NL + "- PP No. 51/2009 tentang Farmasi" + NL + "- Peraturan BPOM No. 4/2018" + NL + "  tentang Pengawasan Obat Tradisional" + NL + "- Peraturan BPOM No. 24/2021" + NL + "  tentang Registrasi Obat" + NL + NL + "Lengkap: jdih.pom.go.id", REGULASI_KEYBOARD),
    "Regulasi Kosmetik":       ("*Regulasi Kosmetik BPOM*" + NL + NL + "Peraturan utama kosmetik:" + NL + "- Peraturan BPOM No. 12/2020" + NL + "  tentang Tata Cara Pengajuan Notifikasi" + NL + "- Peraturan BPOM No. 23/2019" + NL + "  tentang Persyaratan Teknis Kosmetika" + NL + "- Peraturan BPOM No. 2/2020" + NL + "  tentang Pengawasan Kosmetika" + NL + NL + "Lengkap: jdih.pom.go.id", REGULASI_KEYBOARD),
    "Regulasi Alkes":          ("*Regulasi Alat Kesehatan BPOM*" + NL + NL + "Peraturan utama alkes:" + NL + "- PP No. 72/1998 tentang Pengamanan" + NL + "  Sediaan Farmasi & Alat Kesehatan" + NL + "- Peraturan Menkes No. 62/2017" + NL + "  tentang Izin Edar Alkes" + NL + "- Peraturan BPOM No. 9/2021" + NL + "  tentang Penandaan Alkes" + NL + NL + "Lengkap: jdih.pom.go.id", REGULASI_KEYBOARD),
    "Download Peraturan":      ("*Download Peraturan BPOM*" + NL + NL + "Akses peraturan lengkap di:" + NL + NL + "- Website JDIH BPOM:" + NL + "  jdih.pom.go.id" + NL + NL + "- Website BPOM RI:" + NL + "  www.pom.go.id" + NL + NL + "- BPOM Lubuklinggau:" + NL + "  lubuklinggau.pom.go.id" + NL + NL + "Semua peraturan tersedia gratis!", REGULASI_KEYBOARD),
}


# ── Form state per user (registrasi & pengaduan) ─────────────────────────────
user_form_state = {}  # { tg_chat_id: { "form": str, "step": int, "data": {} } }

# Keyboard pilihan jenis produk (registrasi)
JENIS_PRODUK_KEYBOARD = {
    "keyboard": [
        [{"text": "Pangan/Minuman"}, {"text": "Obat-obatan"}],
        [{"text": "Kosmetik"},       {"text": "Suplemen"}],
        [{"text": "Obat Tradisional"},{"text": "Alat Kesehatan"}],
        [{"text": "Batalkan"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}

# Keyboard pilihan jenis pengaduan
JENIS_PENGADUAN_KEYBOARD = {
    "keyboard": [
        [{"text": "Produk Ilegal/Palsu"}],
        [{"text": "Produk Kedaluwarsa"}],
        [{"text": "Efek Samping Berbahaya"}],
        [{"text": "Iklan Menyesatkan"}],
        [{"text": "Lainnya"}],
        [{"text": "Batalkan"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}

# Keyboard konfirmasi
KONFIRMASI_KEYBOARD = {
    "keyboard": [
        [{"text": "Ya, Kirim"}, {"text": "Tidak, Batalkan"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}

# Langkah-langkah form registrasi
REGISTRASI_STEPS = [
    {"key": "nama_produk",    "tanya": "Langkah 1/4 - Nama Produk" + chr(10) + chr(10) + "Ketik *nama produk* yang ingin didaftarkan:", "keyboard": None},
    {"key": "nama_perusahaan","tanya": "Langkah 2/4 - Nama Perusahaan" + chr(10) + chr(10) + "Ketik *nama perusahaan/produsen*:", "keyboard": None},
    {"key": "jenis_produk",   "tanya": "Langkah 3/4 - Jenis Produk" + chr(10) + chr(10) + "Pilih *jenis produk* Anda:", "keyboard": JENIS_PRODUK_KEYBOARD},
    {"key": "keterangan",     "tanya": "Langkah 4/4 - Keterangan Tambahan" + chr(10) + chr(10) + "Ketik *keterangan tambahan* (komposisi, ukuran, dll):" + chr(10) + "Atau ketik *Lewati* jika tidak ada:", "keyboard": None},
]

# Langkah-langkah form pengaduan
PENGADUAN_STEPS = [
    {"key": "jenis_laporan",  "tanya": "Langkah 1/4 - Jenis Pengaduan" + chr(10) + chr(10) + "Pilih *jenis pengaduan*:", "keyboard": JENIS_PENGADUAN_KEYBOARD},
    {"key": "nama_produk",    "tanya": "Langkah 2/4 - Nama Produk" + chr(10) + chr(10) + "Ketik *nama produk* yang diadukan:" + chr(10) + "(Tulis Tidak Tahu jika tidak mengetahui)", "keyboard": None},
    {"key": "lokasi",         "tanya": "Langkah 3/4 - Lokasi Pembelian" + chr(10) + chr(10) + "Ketik *lokasi/toko* tempat membeli produk:", "keyboard": None},
    {"key": "keterangan",     "tanya": "Langkah 4/4 - Kronologi" + chr(10) + chr(10) + "Ketik *kronologi/keterangan lengkap* pengaduan Anda:", "keyboard": None},
]


def get_form_summary(form_type: str, data: dict) -> str:
    """Buat ringkasan isian form untuk konfirmasi."""
    if form_type == "registrasi":
        return (
            "*Ringkasan Pendaftaran Produk*" + chr(10) + chr(10) +
            "Nama Produk   : " + data.get("nama_produk", "-") + chr(10) +
            "Perusahaan    : " + data.get("nama_perusahaan", "-") + chr(10) +
            "Jenis Produk  : " + data.get("jenis_produk", "-") + chr(10) +
            "Keterangan    : " + data.get("keterangan", "-") + chr(10) + chr(10) +
            "Apakah data sudah benar?"
        )
    else:
        return (
            "*Ringkasan Pengaduan*" + chr(10) + chr(10) +
            "Jenis Laporan : " + data.get("jenis_laporan", "-") + chr(10) +
            "Nama Produk   : " + data.get("nama_produk", "-") + chr(10) +
            "Lokasi        : " + data.get("lokasi", "-") + chr(10) +
            "Keterangan    : " + data.get("keterangan", "-") + chr(10) + chr(10) +
            "Apakah data sudah benar?"
        )


def process_form(tg_chat_id: int, tg_text: str) -> tuple:
    """
    Proses input form step by step.
    Return: (reply_text, keyboard, is_done, form_data)
    is_done=True jika form selesai diisi.
    """
    state = user_form_state.get(tg_chat_id)
    if not state:
        return None, None, False, None

    form_type = state["form"]
    step      = state["step"]
    data      = state["data"]
    steps     = REGISTRASI_STEPS if form_type == "registrasi" else PENGADUAN_STEPS

    # Batalkan form
    if tg_text in ["Batalkan", "Tidak, Batalkan"]:
        del user_form_state[tg_chat_id]
        return (
            "Form dibatalkan." + chr(10) + chr(10) + "Silakan pilih menu lain:",
            MAIN_REPLY_KEYBOARD,
            False,
            None
        )

    # Langkah konfirmasi
    if step == len(steps):
        if tg_text == "Ya, Kirim":
            del user_form_state[tg_chat_id]
            label = "Pendaftaran Produk" if form_type == "registrasi" else "Pengaduan"
            return (
                "*" + label + " berhasil dikirim!*" + chr(10) + chr(10) +
                "Terima kasih. Tim BPOM Lubuklinggau akan menindaklanjuti." + chr(10) +
                "Untuk informasi lebih lanjut hubungi: *1500533*",
                MAIN_REPLY_KEYBOARD,
                True,
                data
            )
        else:
            del user_form_state[tg_chat_id]
            return (
                "Form dibatalkan." + chr(10) + chr(10) + "Silakan pilih menu lain:",
                MAIN_REPLY_KEYBOARD,
                False,
                None
            )

    # Simpan jawaban langkah sebelumnya (kecuali langkah pertama)
    if step > 0 or (step == 0 and data):
        current_step = steps[step - 1] if step > 0 else steps[0]
        if step > 0:
            data[steps[step - 1]["key"]] = tg_text

    # Jika ini pertama kali (step=0, belum ada data)
    if step == 0 and not data:
        # Tampilkan pertanyaan pertama
        q = steps[0]
        user_form_state[tg_chat_id]["step"] = 1
        return q["tanya"], q["keyboard"], False, None

    # Simpan jawaban step saat ini dan lanjut
    if step > 0:
        data[steps[step - 1]["key"]] = tg_text

    # Apakah sudah semua langkah?
    if step >= len(steps):
        # Tampilkan konfirmasi
        user_form_state[tg_chat_id]["step"] = len(steps)
        summary = get_form_summary(form_type, data)
        return summary, KONFIRMASI_KEYBOARD, False, None

    # Tampilkan pertanyaan berikutnya
    q = steps[step]
    user_form_state[tg_chat_id]["step"] = step + 1
    return q["tanya"], q["keyboard"], False, None


def send_telegram_message(chat_id: "Union[str, int]", text: str, reply_markup=None):
    """Kirim pesan ke pengguna Telegram, opsional dengan inline keyboard."""
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram] BOT_TOKEN belum diset, pesan tidak terkirim.")
        return False
    import urllib.request
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{TELEGRAM_API_BASE}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        print(f"[Telegram] Gagal kirim pesan: {e}")
        return False


def send_telegram_menu(chat_id: "Union[str, int]", text: str, keyboard=None):
    """Kirim pesan dengan Reply Keyboard (tombol permanen di bawah)."""
    if keyboard is None:
        keyboard = MAIN_REPLY_KEYBOARD
    return send_telegram_message(chat_id, text, keyboard)


def answer_callback_query(callback_query_id: str, text: str = ""):
    """Konfirmasi callback query agar tombol tidak loading terus."""
    import urllib.request
    payload = json.dumps({
        "callback_query_id": callback_query_id,
        "text": text,
    }).encode()
    req = urllib.request.Request(
        f"{TELEGRAM_API_BASE}/answerCallbackQuery",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def verify_telegram_webhook(request_body: bytes, x_telegram_bot_api_secret_token: str, update: dict = None) -> bool:
    """Verifikasi header X-Telegram-Bot-Api-Secret-Token.
    Callback queries dari klik tombol tidak membawa secret token — izinkan."""
    if not TELEGRAM_WEBHOOK_SECRET:
        return True
    # Callback query tidak membawa secret token — tetap izinkan
    if update and "callback_query" in update:
        return True
    # Jika secret kosong (pesan biasa tanpa header) — tetap izinkan
    if not x_telegram_bot_api_secret_token:
        return True
    return hmac.compare_digest(x_telegram_bot_api_secret_token, TELEGRAM_WEBHOOK_SECRET)


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES DARI app.py ASLI (di-proxy agar tetap berfungsi)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
        session["menu"] = "main"
    get_or_create_session(session["session_id"], "web")
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Route chat HTTP biasa — TETAP berfungsi seperti app.py asli."""
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Pesan kosong"}), 400

    if "menu" not in session:
        session["menu"] = "main"
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    session_id = session["session_id"]
    session_data = {"menu": session.get("menu", "main")}

    # Simpan pesan user
    save_message(session_id, "user", user_message, "web")

    # Bot auto-reply — langsung jawab pengguna
    response = get_bot_response(user_message, session_data)
    if "update_menu" in response:
        session["menu"] = response["update_menu"]
        active_sessions.get(session_id, {})["menu"] = response["update_menu"]

    response["timestamp"] = datetime.now().strftime("%H:%M")
    save_message(session_id, "bot", response.get("message", ""), "web")

    # Broadcast ke dashboard admin (untuk pantau/balas manual)
    def _emit_web_msg():
        socketio.emit("new_web_message", {
            "session_id": session_id,
            "user_message": user_message,
            "bot_response": response.get("message", ""),
            "timestamp": response["timestamp"],
        }, namespace="/", room="dashboard")
    threading.Thread(target=_emit_web_msg, daemon=True).start()

    return jsonify(response)


@app.route("/api/reset", methods=["POST"])
def reset():
    session["menu"] = "main"
    session["chat_history"] = []
    if "session_id" in session:
        sid = session["session_id"]
        if sid in active_sessions:
            active_sessions[sid]["menu"] = "main"
            active_sessions[sid]["messages"] = []
    return jsonify({"status": "ok"})


@app.route("/api/chat_direct", methods=["POST"])
def chat_direct():
    """Route fallback — dipanggil oleh chat.js jika response type='waiting'."""
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Pesan kosong"}), 400

    if "menu" not in session:
        session["menu"] = "main"
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    session_data = {"menu": session.get("menu", "main")}
    response = get_bot_response(user_message, session_data)
    if "update_menu" in response:
        session["menu"] = response["update_menu"]

    response["timestamp"] = datetime.now().strftime("%H:%M")
    return jsonify(response)


@app.route("/api/welcome", methods=["GET"])
def welcome():
    return jsonify({
        "type": "text_with_menu",
        "message": (
            "👋 **Selamat datang di Chatbot BPOM Lubuklinggau!**\n\n"
            "Saya siap membantu Anda dengan informasi seputar:\n"
            "• 📝 Registrasi & sertifikasi produk\n"
            "• 🔍 Pengecekan keamanan produk\n"
            "• 📢 Pengaduan produk ilegal\n"
            "• 💡 Tips keamanan konsumen\n"
            "• 📋 Regulasi dan peraturan BPOM\n\n"
            "Silakan pilih menu di bawah atau ketik pertanyaan Anda! 😊"
        ),
        "quick_replies": QUICK_MENUS["main"],
        "timestamp": datetime.now().strftime("%H:%M"),
    })


# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM WEBHOOK ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/webhook/telegram", methods=["POST"])
def telegram_webhook():
    """\n    Endpoint yang didaftarkan ke Telegram sebagai webhook.\n    Telegram mengirim update ke sini setiap ada pesan masuk.\n    """
    update = request.json
    if not update:
        return jsonify({"ok": True})

    # Verifikasi secret token — callback_query dikecualikan
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not verify_telegram_webhook(request.data, secret, update):
        return jsonify({"error": "Unauthorized"}), 403

    # ── Handle callback_query (klik tombol inline keyboard) ──────────────────
    callback_query = update.get("callback_query")
    if callback_query:
        cb_id       = callback_query["id"]
        cb_data     = callback_query.get("data", "main")
        cb_chat_id  = callback_query["message"]["chat"]["id"]
        cb_username = callback_query["from"].get("username") or callback_query["from"].get("first_name", "User")

        answer_callback_query(cb_id)

        # Respon sesuai tombol yang diklik
        menu_responses = {
            "main":                ("*Menu Utama BPOM Lubuklinggau*" + chr(10) + chr(10) + "Silakan pilih layanan:", "main"),
            "registrasi":          ("*Registrasi Produk*" + chr(10) + chr(10) + "Pilih informasi yang dibutuhkan:", "registrasi"),
            "cek_produk":          ("*Cek Produk BPOM*" + chr(10) + chr(10) + "Pilih informasi yang dibutuhkan:", "cek_produk"),
            "pengaduan":           ("*Pengaduan*" + chr(10) + chr(10) + "Pilih informasi yang dibutuhkan:", "pengaduan"),
            "tips":                ("*Tips Keamanan Konsumen BPOM*" + chr(10) + chr(10) + "- Cek nomor registrasi BPOM" + chr(10) + "- Perhatikan tanggal kedaluwarsa" + chr(10) + "- Waspadai produk tanpa izin edar" + chr(10) + "- Beli di tempat resmi" + chr(10) + "- Laporkan ke: 1500533", "main"),
            "kontak":              ("*Kontak BPOM Lubuklinggau*" + chr(10) + chr(10) + "Alamat: Jl. Yos Sudarso No. 12" + chr(10) + "Telp: (0733) 325678" + chr(10) + "Email: bpom.lubuklinggau@pom.go.id" + chr(10) + "Jam: Sen-Jum 08.00-16.00 WIB" + chr(10) + "Hotline: *1500533*", "main"),
            "regulasi":            ("*Regulasi BPOM*" + chr(10) + chr(10) + "- Peraturan BPOM tentang pangan" + chr(10) + "- Regulasi obat dan suplemen" + chr(10) + "- Aturan kosmetik dan alkes" + chr(10) + chr(10) + "Kunjungi: jdih.pom.go.id", "main"),
            "prosedur_registrasi": ("*Prosedur Registrasi*" + chr(10) + chr(10) + "1. Daftar akun e-reg.pom.go.id" + chr(10) + "2. Lengkapi data perusahaan" + chr(10) + "3. Upload dokumen persyaratan" + chr(10) + "4. Bayar PNBP" + chr(10) + "5. Tunggu evaluasi 3-14 hari kerja", "registrasi"),
            "syarat_registrasi":   ("*Syarat Registrasi*" + chr(10) + chr(10) + "- NIB (Nomor Induk Berusaha)" + chr(10) + "- NPWP perusahaan" + chr(10) + "- Sertifikat GMP/CPOTB" + chr(10) + "- Hasil uji laboratorium" + chr(10) + "- Label produk", "registrasi"),
            "biaya_registrasi":    ("*Biaya Registrasi*" + chr(10) + chr(10) + "Biaya PNBP sesuai PP No. 32/2017:" + chr(10) + "- Pangan: Rp 100.000 - 500.000" + chr(10) + "- Kosmetik: Rp 500.000 - 1.500.000" + chr(10) + "- Obat tradisional: Rp 150.000 - 1.000.000", "registrasi"),
            "cara_cek":            ("*Cara Cek Produk BPOM*" + chr(10) + chr(10) + "1. Download aplikasi *BPOM Mobile*" + chr(10) + "2. Scan barcode produk" + chr(10) + "3. Kunjungi cekbpom.pom.go.id" + chr(10) + "4. Masukkan nomor registrasi" + chr(10) + "5. Cek keaslian produk", "cek_produk"),
            "kode_registrasi":     ("*Arti Kode Registrasi*" + chr(10) + chr(10) + "- *BPOM RI MD* = Produk dalam negeri" + chr(10) + "- *BPOM RI ML* = Produk impor" + chr(10) + "- *BPOM RI TR* = Obat tradisional" + chr(10) + "- *BPOM RI NA* = Kosmetik DN" + chr(10) + "- *BPOM RI NC* = Kosmetik impor", "cek_produk"),
            "produk_berbahaya":    ("*Produk Berbahaya*" + chr(10) + chr(10) + "Ciri produk berbahaya:" + chr(10) + "- Tanpa nomor registrasi BPOM" + chr(10) + "- Harga jauh di bawah pasaran" + chr(10) + "- Klaim berlebihan" + chr(10) + "- Label tidak lengkap" + chr(10) + chr(10) + "Laporkan ke: 1500533", "cek_produk"),
            "cara_melapor":        ("*Cara Melapor Pengaduan*" + chr(10) + chr(10) + "1. Hubungi hotline *1500533*" + chr(10) + "2. Email: halobpom@pom.go.id" + chr(10) + "3. Aplikasi BPOM Mobile" + chr(10) + "4. Datang langsung ke kantor" + chr(10) + "5. Website: www.pom.go.id", "pengaduan"),
            "kontak_pengaduan":    ("*Kontak Pengaduan*" + chr(10) + chr(10) + "- Hotline: *1500533*" + chr(10) + "- WhatsApp: 08121 9999 533" + chr(10) + "- Email: halobpom@pom.go.id" + chr(10) + "- Jam layanan: 08.00-20.00 WIB", "pengaduan"),
        }

        resp_text, next_menu = menu_responses.get(cb_data, ("*Menu Utama BPOM Lubuklinggau*" + chr(10) + chr(10) + "Silakan pilih layanan:", "main"))
        send_telegram_menu(cb_chat_id, resp_text, next_menu)

        # Simpan ke session & forward ke dashboard
        if cb_chat_id not in telegram_session_map:
            telegram_session_map[cb_chat_id] = f"tg_{cb_chat_id}_{uuid.uuid4().hex[:8]}"
        session_id = telegram_session_map[cb_chat_id]
        sess = get_or_create_session(session_id, "telegram")
        sess["username"] = cb_username
        save_message(session_id, "user", f"[Menu] {cb_data}", "telegram")

        def _emit_cb():
            socketio.emit("new_telegram_message", {
                "session_id": session_id,
                "tg_chat_id": cb_chat_id,
                "username": cb_username,
                "user_message": f"🔘 Pilih menu: {cb_data}",
                "bot_response": None,
                "timestamp": datetime.now().strftime("%H:%M"),
            }, namespace="/", room="dashboard")
        threading.Thread(target=_emit_cb, daemon=True).start()

        return jsonify({"ok": True})

    # ── Handle pesan teks biasa ───────────────────────────────────────────────
    message = update.get("message") or update.get("edited_message")
    if not message:
        return jsonify({"ok": True})

    tg_chat_id  = message["chat"]["id"]
    tg_username = message["chat"].get("username") or message["chat"].get("first_name", "User")
    tg_text     = message.get("text", "").strip()

    if not tg_text:
        return jsonify({"ok": True})

    # Dapatkan atau buat session untuk pengguna Telegram ini
    if tg_chat_id not in telegram_session_map:
        new_sid = f"tg_{tg_chat_id}_{uuid.uuid4().hex[:8]}"
        telegram_session_map[tg_chat_id] = new_sid

    session_id = telegram_session_map[tg_chat_id]
    sess = get_or_create_session(session_id, "telegram")
    sess["username"] = tg_username

    # Handle /start /menu /help
    if tg_text in ["/start", "/menu", "/help"]:
        sess["tg_chat_id"] = tg_chat_id
        welcome = (
            "*Selamat Datang di Layanan Bot BPOM Lubuklinggau!*" + chr(10) + chr(10) +
            "Halo! Saya asisten virtual resmi BPOM Lubuklinggau." + chr(10) +
            "Saya siap membantu Anda dengan informasi seputar:" + chr(10) + chr(10) +
            "- Registrasi & sertifikasi produk" + chr(10) +
            "- Pengecekan keamanan produk" + chr(10) +
            "- Layanan sertifikasi BPOM" + chr(10) +
            "- Pengaduan produk ilegal/berbahaya" + chr(10) +
            "- Kontak dan informasi BPOM" + chr(10) + chr(10) +
            "Silakan pilih menu di bawah atau ketik pertanyaan Anda:"
        )
        send_telegram_message(tg_chat_id, welcome, MAIN_REPLY_KEYBOARD)
        return jsonify({"ok": True})

    # Cek apakah teks cocok dengan tombol menu
    import re
    tg_clean = re.sub("[^a-zA-Z0-9 ]", "", tg_text).strip()
    menu_key = None
    if tg_text in MENU_RESPONSES:
        menu_key = tg_text
    else:
        for key in MENU_RESPONSES:
            if re.sub("[^a-zA-Z0-9 ]", "", key).strip().lower() == tg_clean.lower():
                menu_key = key
                break

    if menu_key:
        # Tombol menu diklik: langsung balas dengan informasi
        resp_text, next_keyboard = MENU_RESPONSES[menu_key]
        save_message(session_id, "user", tg_text, "telegram")
        send_telegram_message(tg_chat_id, resp_text, next_keyboard)
        def _emit_menu():
            socketio.emit("new_telegram_message", {
                "session_id": session_id,
                "tg_chat_id": tg_chat_id,
                "username": tg_username,
                "user_message": f"[Menu] {tg_text}",
                "bot_response": resp_text[:80] + "...",
                "timestamp": datetime.now().strftime("%H:%M"),
            }, namespace="/", room="dashboard")
        threading.Thread(target=_emit_menu, daemon=True).start()
        return jsonify({"ok": True})

    # ── Pesan bebas: AUTO-REPLY oleh bot (tidak perlu admin/dashboard online) ──
    save_message(session_id, "user", tg_text, "telegram")

    # Panggil get_bot_response() persis seperti chat web
    session_data = {"menu": sess.get("menu", "main")}
    bot_resp = get_bot_response(tg_text, session_data)

    if "update_menu" in bot_resp:
        sess["menu"] = bot_resp["update_menu"]

    bot_text = bot_resp.get("message", "")
    save_message(session_id, "bot", bot_text, "telegram")

    # Kirim jawaban bot langsung ke Telegram
    send_telegram_message(tg_chat_id, bot_text, MAIN_REPLY_KEYBOARD)

    # Broadcast ke dashboard (hanya untuk monitoring, BUKAN syarat balasan)
    ts = datetime.now().strftime("%H:%M")
    def _emit_to_dashboard():
        socketio.emit("new_telegram_message", {
            "session_id": session_id,
            "tg_chat_id": tg_chat_id,
            "username": tg_username,
            "user_message": tg_text,
            "bot_response": bot_text[:80] + ("..." if len(bot_text) > 80 else ""),
            "timestamp": ts,
            "auto_replied": True,
        }, namespace="/", room="dashboard")
    threading.Thread(target=_emit_to_dashboard, daemon=True).start()

    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/dashboard/sessions")
def api_dashboard_sessions():
    """Daftar semua sesi aktif (web + telegram)."""
    sessions_list = []
    for sid, data in active_sessions.items():
        last_msg = data["messages"][-1] if data["messages"] else None
        sessions_list.append({
            "id": sid,
            "source": data["source"],
            "username": data.get("username", ""),
            "message_count": len(data["messages"]),
            "last_message": last_msg["text"][:80] if last_msg else "",
            "last_active": data["last_active"],
        })
    # Urutkan berdasarkan waktu aktif terakhir
    sessions_list.sort(key=lambda x: x["last_active"], reverse=True)
    return jsonify(sessions_list)


@app.route("/api/dashboard/session/<session_id>")
def api_session_detail(session_id):
    """Detail pesan satu sesi."""
    sess = active_sessions.get(session_id)
    if not sess:
        return jsonify({"error": "Sesi tidak ditemukan"}), 404
    return jsonify(sess)


@app.route("/api/dashboard/reply", methods=["POST"])
def api_dashboard_reply():
    """\n    Admin membalas pesan secara manual dari dashboard.\n    Pesan ini akan dikirim ke user web (via WebSocket) ATAU\n    ke Telegram (via Bot API), tergantung source sesi.\n    """
    data = request.json
    session_id = data.get("session_id", "")
    reply_text = data.get("message", "").strip()

    if not session_id or not reply_text:
        return jsonify({"error": "session_id dan message wajib diisi"}), 400

    sess = active_sessions.get(session_id)
    if not sess:
        return jsonify({"error": "Sesi tidak ditemukan"}), 404

    # Simpan pesan admin
    msg = save_message(session_id, "admin", reply_text, "dashboard")

    if sess["source"] == "telegram":
        # Cari telegram chat_id dari peta
        tg_chat_id = next(
            (cid for cid, sid in telegram_session_map.items() if sid == session_id),
            None,
        )
        if tg_chat_id:
            send_telegram_message(tg_chat_id, f"👨‍💼 *Petugas BPOM:*\n{reply_text}")

    # Kirim ke browser pengguna web via WebSocket (room = session_id)
    socketio.emit("admin_reply", {
        "message": reply_text,
        "timestamp": msg["timestamp"],
        "role": "admin",
    }, room=session_id)

    # Update dashboard semua admin
    socketio.emit("session_updated", {
        "session_id": session_id,
        "last_message": reply_text[:80],
        "last_active": sess["last_active"],
    }, room="dashboard")

    return jsonify({"status": "ok", "message": msg})


@app.route("/api/dashboard/stats")
def api_dashboard_stats():
    """Statistik singkat untuk header dashboard."""
    total = len(active_sessions)
    web_count = sum(1 for s in active_sessions.values() if s["source"] == "web")
    tg_count  = sum(1 for s in active_sessions.values() if s["source"] == "telegram")
    total_msgs = sum(len(s["messages"]) for s in active_sessions.values())
    return jsonify({
        "total_sessions": total,
        "web_sessions": web_count,
        "telegram_sessions": tg_count,
        "total_messages": total_msgs,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  WEBSOCKET EVENTS
# ══════════════════════════════════════════════════════════════════════════════

@socketio.on("connect")
def on_connect():
    """Client terhubung — identifikasi apakah web user atau dashboard admin."""
    pass


@socketio.on("join_user")
def on_join_user(data):
    """\n    Web user bergabung ke room session mereka sendiri.\n    Frontend harus emit event ini setelah koneksi.\n    Payload: { session_id: "..." }\n    """
    sid = data.get("session_id")
    if sid:
        join_room(sid)
        emit("joined", {"room": sid, "status": "ok"})


@socketio.on("join_dashboard")
def on_join_dashboard(data=None):
    """Admin dashboard bergabung ke room 'dashboard' untuk menerima semua broadcast."""
    join_room("dashboard")
    emit("joined", {"room": "dashboard", "status": "ok"})


@socketio.on("chat_message_ws")
def on_chat_message_ws(data):
    """\n    Pesan chat dari web user dikirim via WebSocket (real-time).\n    Payload: { session_id: str, message: str }\n    """
    session_id  = data.get("session_id", "")
    user_message = data.get("message", "").strip()

    if not session_id or not user_message:
        emit("error", {"message": "Data tidak lengkap"})
        return

    sess = get_or_create_session(session_id, "web")
    save_message(session_id, "user", user_message, "web")

    # Kirim "typing" indicator
    emit("typing_start", {}, room=session_id)

    # Bot auto-reply via WebSocket
    def process_and_emit():
        import time
        time.sleep(0.6)  # delay natural

        session_data = {"menu": sess.get("menu", "main")}
        response = get_bot_response(user_message, session_data)

        if "update_menu" in response:
            sess["menu"] = response["update_menu"]

        response["timestamp"] = datetime.now().strftime("%H:%M")
        save_message(session_id, "bot", response.get("message", ""), "web")

        # Kirim balasan ke pengguna web
        socketio.emit("bot_reply", response, room=session_id)
        socketio.emit("typing_stop", {}, room=session_id)

        # Broadcast ke dashboard untuk dipantau/dibalas admin
        socketio.emit("new_web_message", {
            "session_id": session_id,
            "user_message": user_message,
            "bot_response": response.get("message", ""),
            "timestamp": response["timestamp"],
        }, namespace="/", room="dashboard")

    threading.Thread(target=process_and_emit, daemon=True).start()


@socketio.on("disconnect")
def on_disconnect():
    pass


# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM WEBHOOK SETUP HELPER
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/setup/telegram", methods=["GET"])
def setup_telegram_info():
    """\n    Endpoint helper: tampilkan instruksi pendaftaran webhook Telegram.\n    Akses: http://127.0.0.1:5000/setup/telegram\n    """
    host = request.host_url.rstrip("/")
    webhook_url = f"{host}/webhook/telegram"
    curl_cmd = (
        f'curl -X POST "https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN or "<TOKEN>"}/setWebhook" '
        f'-H "Content-Type: application/json" '
        f'-d \'{{"url": "{webhook_url}", '
        f'"secret_token": "{TELEGRAM_WEBHOOK_SECRET}"}}\''
    )
    return jsonify({
        "instruksi": "Daftarkan URL berikut sebagai webhook Telegram Bot Anda",
        "webhook_url": webhook_url,
        "token_set": bool(TELEGRAM_BOT_TOKEN),
        "curl_command": curl_cmd,
        "catatan": (
            "Untuk uji lokal, gunakan ngrok: "
            "ngrok http 5000  →  salin URL https → daftarkan ke Telegram"
        ),
    })


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    print("=" * 60)
    print("  BPOM Lubuklinggau — WebSocket + Telegram Edition")
    print(f"  Chatbot  : http://{host}:{port}")
    print(f"  Dashboard: http://{host}:{port}/dashboard")
    print(f"  Setup TG : http://{host}:{port}/setup/telegram")
    print("  Mode     : 24/7 Online (bot auto-reply aktif)")
    print("=" * 60)
    # allow_unsafe_werkzeug=True diperlukan di beberapa versi Flask-SocketIO
    # untuk mode threading tanpa eventlet/gevent
    socketio.run(
        app,
        debug=False,          # debug=False untuk produksi/24 jam
        port=port,
        host=host,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
