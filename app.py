from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
import uuid
import re
import os
import requests

app = Flask(__name__)
app.secret_key = "bpom_lubuklinggau_secret_2024"
BOT_TOKEN = "8741328752:AAGrDb6hfydbvpHKozUSKl4CX7lkw26wts0"
os.environ.get("BOT_TOKEN")

# =============================================
# DATA PENGETAHUAN BPOM LUBUKLINGGAU
# =============================================

BPOM_DATA = {
    "profil": {
        "nama": "Balai Besar/Loka Pengawas Obat dan Makanan (BPOM) Lubuklinggau",
        "alamat": "Jl. Yos Sudarso No. 12, Lubuklinggau, Sumatera Selatan",
        "telepon": "(0733) 325678",
        "email": "bpom.lubuklinggau@pom.go.id",
        "jam_operasional": "Senin - Jumat: 08.00 - 16.00 WIB",
        "website": "www.pom.go.id",
    },
    "layanan": [
        {
            "id": "registrasi",
            "nama": "Registrasi Produk",
            "deskripsi": "Layanan pendaftaran produk obat, makanan, kosmetik, dan suplemen kesehatan",
            "prosedur": [
                "Siapkan dokumen persyaratan lengkap",
                "Akses portal e-reg di  https://e-reg.pom.go.id/",
                "Buat akun atau login jika sudah terdaftar",
                "Isi formulir pendaftaran produk secara online",
                "Upload dokumen pendukung (hasil uji lab, komposisi, dll)",
                "Bayar PNBP (Penerimaan Negara Bukan Pajak) sesuai kategori",
                "Tunggu proses evaluasi 10-30 hari kerja",
                "Terima nomor registrasi jika disetujui",
            ],
            "biaya": "Sesuai PP No. 32 Tahun 2017 tentang Tarif PNBP BPOM",
        },
        {
            "id": "sertifikasi",
            "nama": "Sertifikasi CPOB/CPOTB/CPPB",
            "deskripsi": "Sertifikasi Cara Produksi yang Baik untuk industri farmasi, obat tradisional, dan pangan",
            "prosedur": [
                "Ajukan permohonan sertifikasi ke kantor BPOM",
                "Tim BPOM akan melakukan audit/inspeksi ke fasilitas produksi",
                "Evaluasi dokumen sistem manajemen mutu",
                "Perbaikan temuan inspeksi (jika ada)",
                "Penerbitan sertifikat CPOB/CPOTB/CPPB",
            ],
            "biaya": "Rp 2.000.000 - Rp 10.000.000 (tergantung jenis sertifikasi)",
        },
        {
            "id": "pengaduan",
            "nama": "Pengaduan Produk Ilegal",
            "deskripsi": "Layanan pelaporan produk obat, makanan, dan kosmetik ilegal atau palsu",
            "cara_melapor": [
                "Datang langsung ke kantor BPOM Lubuklinggau",
                "Hubungi hotline BPOM: 1500533",
                "Email: halobpom@pom.go.id",
                "Aplikasi BPOM Mobile (cek izin edar)",
                "Website: www.pom.go.id/pengaduan",
            ],
        },
        {
            "id": "informasi",
            "nama": "Informasi & Konsultasi",
            "deskripsi": "Layanan informasi seputar regulasi, perizinan, dan pengawasan produk",
            "kontak": "Hubungi 1500533 atau datang langsung ke kantor",
        },
    ],
    "produk_terdaftar": {
        "cara_cek": [
            "Download aplikasi 'BPOM Mobile' di Play Store / App Store",
            "Buka website https://lubuklinggau.pom.go.id/",
            "Masukkan nomor registrasi produk (contoh: MD/ML/NA/TR/SI/POM)",
            "Atau scan barcode/QR code pada kemasan produk",
        ],
        "kode_registrasi": {
            "MD": "Makanan Dalam Negeri",
            "ML": "Makanan Luar Negeri (Impor)",
            "NA": "Nomor Atom (Obat bebas)",
            "TR": "Obat Tradisional",
            "SI": "Suplemen Impor",
            "SD": "Suplemen Dalam Negeri",
            "KA": "Kosmetik",
            "POM": "Produk yang telah mendapat izin edar BPOM",
        },
    },
    "regulasi": {
        "makanan": [
            "UU No. 18 Tahun 2012 tentang Pangan",
            "PP No. 86 Tahun 2019 tentang Keamanan Pangan",
            "Peraturan BPOM No. 34 Tahun 2019 tentang Label Pangan",
        ],
        "obat": [
            "UU No. 36 Tahun 2009 tentang Kesehatan",
            "PP No. 51 Tahun 2009 tentang Pekerjaan Kefarmasian",
            "Peraturan BPOM No. 4 Tahun 2018 tentang CPOB",
        ],
        "kosmetik": [
            "Peraturan BPOM No. 12 Tahun 2020 tentang Tata Cara Pengajuan Notifikasi Kosmetik",
            "Peraturan BPOM No. 23 Tahun 2019 tentang Persyaratan Teknis Bahan Kosmetik",
        ],
    },
    "tips_keamanan": [
        "Selalu cek nomor registrasi BPOM pada kemasan produk",
        "Hindari produk tanpa label yang jelas",
        "Waspadai produk dengan harga yang terlalu murah",
        "Cek tanggal kadaluarsa sebelum membeli",
        "Beli produk di tempat resmi dan terpercaya",
        "Laporkan produk mencurigakan ke BPOM",
        "Jangan konsumsi obat tanpa resep dokter",
        "Baca komposisi dan peringatan pada label produk",
    ],
    "obat_berbahaya": {
        "ciri_ciri": [
            "Tidak memiliki nomor registrasi BPOM",
            "Label tidak jelas atau tidak ada keterangan produsen",
            "Klaim berlebihan (menyembuhkan semua penyakit)",
            "Harga sangat murah tidak wajar",
            "Dijual tanpa kemasan atau eceran",
            "Produk impor tanpa terjemahan bahasa Indonesia",
        ],
        "cara_hindari": [
            "Beli hanya di apotek resmi atau toko obat berizin",
            "Selalu minta struk pembelian",
            "Cek nomor BPOM di aplikasi atau website resmi",
            "Konsultasikan dengan apoteker atau dokter",
        ],
    },
}

# =============================================
# MENU CEPAT (QUICK REPLIES)
# =============================================

QUICK_MENUS = {
    "main": [
        {"id": "layanan", "text": "🏥 Layanan BPOM", "icon": "🏥"},
        {"id": "cek_produk", "text": "🔍 Cek Produk", "icon": "🔍"},
        {"id": "pengaduan", "text": "📢 Pengaduan", "icon": "📢"},
        {"id": "tips", "text": "💡 Tips Keamanan", "icon": "💡"},
        {"id": "kontak", "text": "📞 Kontak Kami", "icon": "📞"},
        {"id": "regulasi", "text": "📋 Regulasi", "icon": "📋"},
    ],
    "layanan": [
        {"id": "sertifikasi_cpkb", "text": "💄 Sertifikasi CPKB Kosmetik"},
        {"id": "sertifikasi_cpotb", "text": "🌿 Sertifikasi CPOTB Obat Tradisional"},
        {"id": "sertifikasi_cdob", "text": "🚚 Sertifikasi CDOB Distribusi Obat"},
        {"id": "rekomendasi_notifikasi", "text": "📋 Rekomendasi Notifikasi Kosmetik"},
        {"id": "izin_cppob", "text": "🍱 Izin CPPOB Pangan Olahan"},
        {"id": "back", "text": "⬅️ Kembali"},
    ],
    "cek_produk": [
        {"id": "cara_cek", "text": "📱 Cara Cek Produk"},
        {"id": "kode_registrasi", "text": "🔑 Arti Kode Registrasi"},
        {"id": "produk_berbahaya", "text": "⚠️ Ciri Produk Berbahaya"},
        {"id": "back", "text": "⬅️ Kembali"},
    ],
}


# =============================================
# CHATBOT ENGINE
# =============================================


def get_bot_response(user_message, session_data):
    """Main chatbot logic - returns response dict"""
    msg = user_message.lower().strip()
    current_menu = session_data.get("menu", "main")

    # ---- GREETINGS ----
    greetings = ["halo", "hi", "hello", "hai", "selamat", "pagi", "siang", "sore", "malam", "apa kabar", "assalamualaikum"]
    if any(g in msg for g in greetings):
        return {
            "type": "text_with_menu",
            "message": (
                "👋 **Halo! Selamat datang di Chatbot BPOM Lubuklinggau!**\n\n"
                "Saya adalah asisten virtual BPOM yang siap membantu Anda dengan informasi seputar:\n"
                "• Registrasi & sertifikasi produk\n"
                "• Pengecekan keamanan produk\n"
                "• Pengaduan produk ilegal\n"
                "• Regulasi dan peraturan\n\n"
                "Silakan pilih menu di bawah atau ketik pertanyaan Anda! 😊"
            ),
            "quick_replies": QUICK_MENUS["main"],
            "update_menu": "main",
        }

    # ---- HANDLE QUICK REPLY BUTTONS ----
    if msg in ["layanan", "🏥 layanan bpom"]:
        return {
            "type": "text_with_menu",
            "message": "🏥 **Layanan Sertifikasi BPOM Lubuklinggau**\n\nPilih layanan sertifikasi yang Anda butuhkan:",
            "quick_replies": QUICK_MENUS["layanan"],
            "update_menu": "layanan",
        }

    if msg in ["cek_produk", "🔍 cek produk"]:
        return {
            "type": "text_with_menu",
            "message": "🔍 **Pengecekan Produk BPOM**\n\nKami memiliki berbagai cara untuk membantu Anda mengecek keamanan produk. Pilih informasi yang Anda butuhkan:",
            "quick_replies": QUICK_MENUS["cek_produk"],
            "update_menu": "cek_produk",
        }

    if msg in ["tips", "💡 tips keamanan"]:
        tips_list = "\n".join([f"✅ {tip}" for tip in BPOM_DATA["tips_keamanan"]])
        return {
            "type": "text_with_menu",
            "message": f"💡 **Tips Keamanan Produk**\n\n{tips_list}\n\n🔔 *Ingat: Selalu lindungi diri dan keluarga dengan memilih produk yang telah terdaftar BPOM!*",
            "quick_replies": QUICK_MENUS["main"],
            "update_menu": "main",
        }

    if msg in ["kontak", "📞 kontak kami"]:
        profil = BPOM_DATA["profil"]
        return {
            "type": "card",
            "message": "📞 **Kontak BPOM Lubuklinggau**",
            "card": {
                "title": profil["nama"],
                "items": [
                    {"icon": "📍", "label": "Alamat", "value": profil["alamat"]},
                    {"icon": "📞", "label": "Telepon", "value": profil["telepon"]},
                    {"icon": "📧", "label": "Email", "value": profil["email"]},
                    {"icon": "⏰", "label": "Jam Operasional", "value": profil["jam_operasional"]},
                    {"icon": "🌐", "label": "Website", "value": profil["website"]},
                    {"icon": "☎️", "label": "Hotline Nasional", "value": "1500533"},
                ],
            },
            "quick_replies": QUICK_MENUS["main"],
            "update_menu": "main",
        }

    if msg in ["regulasi", "📋 regulasi"]:
        reg = BPOM_DATA["regulasi"]
        makanan = "\n".join([f"  • {r}" for r in reg["makanan"]])
        obat = "\n".join([f"  • {r}" for r in reg["obat"]])
        kosmetik = "\n".join([f"  • {r}" for r in reg["kosmetik"]])
        return {
            "type": "text_with_menu",
            "message": (
                f"📋 **Regulasi & Peraturan BPOM**\n\n"
                f"**🍎 Pangan:**\n{makanan}\n\n"
                f"**💊 Obat:**\n{obat}\n\n"
                f"**💄 Kosmetik:**\n{kosmetik}\n\n"
                f"📌 *Untuk informasi regulasi lebih lengkap, kunjungi www.pom.go.id*"
            ),
            "quick_replies": QUICK_MENUS["main"],
            "update_menu": "main",
        }

    # ---- LAYANAN DETAIL ----
    if msg in ["registrasi", "📝 registrasi produk", "registrasi produk",
               "jenis layanan", "layanan registrasi"]:
        layanan = next(l for l in BPOM_DATA["layanan"] if l["id"] == "registrasi")
        prosedur = "\n".join([f"  {i+1}. {p}" for i, p in enumerate(layanan["prosedur"])])
        return {
            "type": "text_with_menu",
            "message": (
                f"📝 **{layanan['nama']}**\n\n"
                f"📌 *{layanan['deskripsi']}*\n\n"
                f"**Prosedur Pendaftaran:**\n{prosedur}\n\n"
                f"💰 **Biaya:** {layanan['biaya']}\n\n"
                f"🌐 Portal: https://e-reg.pom.go.id"
            ),
            "quick_replies": QUICK_MENUS["layanan"],
            "update_menu": "layanan",
        }

    if msg in ["sertifikasi_cpkb", "💄 sertifikasi cpkb kosmetik"]:
        return {
            "type": "text_with_menu",
            "message": (
                "💄 **Sertifikasi Cara Pembuatan Kosmetik yang Baik (CPKB)**\n\n"
                "📌 *Sertifikasi bagi industri kosmetik untuk memenuhi persyaratan CPKB.*\n\n"
                "**Prosedur:**\n"
                "  1. Ajukan permohonan ke kantor BPOM Lubuklinggau\n"
                "  2. Lengkapi dokumen persyaratan administrasi\n"
                "  3. Tim BPOM melakukan inspeksi fasilitas produksi\n"
                "  4. Evaluasi dan tindak lanjut temuan inspeksi\n"
                "  5. Penerbitan Sertifikat CPKB\n\n"
                "**Persyaratan:**\n"
                "  • Izin usaha industri kosmetik\n"
                "  • Fasilitas produksi sesuai standar CPKB\n"
                "  • Sistem manajemen mutu terdokumentasi\n"
                "  • Tenaga ahli kosmetologi/farmasi\n\n"
                "📞 Info: (0733) 325678 | bpom.lubuklinggau@pom.go.id"
            ),
            "quick_replies": QUICK_MENUS["layanan"],
            "update_menu": "layanan",
        }

    if msg in ["sertifikasi_cpotb", "🌿 sertifikasi cpotb obat tradisional"]:
        return {
            "type": "text_with_menu",
            "message": (
                "🌿 **Sertifikasi Cara Pembuatan Obat Tradisional yang Baik (CPOTB)**\n\n"
                "📌 *Sertifikasi CPOTB bagi industri obat tradisional.*\n\n"
                "**Prosedur:**\n"
                "  1. Ajukan permohonan ke kantor BPOM Lubuklinggau\n"
                "  2. Siapkan dokumen izin usaha & sistem manajemen mutu\n"
                "  3. Tim BPOM melakukan audit fasilitas produksi\n"
                "  4. Evaluasi sistem pengawasan mutu\n"
                "  5. Penerbitan Sertifikat CPOTB\n\n"
                "**Persyaratan:**\n"
                "  • Izin usaha industri obat tradisional/jamu\n"
                "  • Fasilitas produksi sesuai standar CPOTB\n"
                "  • Apoteker sebagai penanggung jawab\n\n"
                "📞 Hotline: **1500533** | halobpom@pom.go.id"
            ),
            "quick_replies": QUICK_MENUS["layanan"],
            "update_menu": "layanan",
        }

    if msg in ["sertifikasi_cdob", "🚚 sertifikasi cdob distribusi obat"]:
        return {
            "type": "text_with_menu",
            "message": (
                "🚚 **Sertifikasi Cara Distribusi Obat yang Baik (CDOB)**\n\n"
                "📌 *Sertifikasi bagi distributor/pedagang besar farmasi.*\n\n"
                "**Prosedur:**\n"
                "  1. Permohonan sertifikasi CDOB ke BPOM\n"
                "  2. Verifikasi dokumen administrasi\n"
                "  3. Inspeksi fasilitas distribusi\n"
                "  4. Evaluasi CAPA (Corrective Action)\n"
                "  5. Penerbitan Sertifikat CDOB (berlaku 5 tahun)\n\n"
                "**Persyaratan:**\n"
                "  • Izin Pedagang Besar Farmasi (PBF)\n"
                "  • Fasilitas penyimpanan sesuai standar\n"
                "  • Apoteker sebagai penanggung jawab\n\n"
                "📞 Info: (0733) 325678 | bpom.lubuklinggau@pom.go.id"
            ),
            "quick_replies": QUICK_MENUS["layanan"],
            "update_menu": "layanan",
        }

    if msg in ["rekomendasi_notifikasi", "📋 rekomendasi notifikasi kosmetik"]:
        return {
            "type": "text_with_menu",
            "message": (
                "📋 **Penerbitan Rekomendasi Notifikasi Kosmetik**\n\n"
                "📌 *Rekomendasi bagi pemohon notifikasi kosmetik ke BPOM Pusat.*\n\n"
                "**Prosedur:**\n"
                "  1. Daftar di notifikasikosmetik.pom.go.id\n"
                "  2. Lengkapi data perusahaan dan produk\n"
                "  3. Ajukan permohonan ke BPOM Lubuklinggau\n"
                "  4. Verifikasi dokumen oleh petugas\n"
                "  5. Rekomendasi diterbitkan 3-5 hari kerja\n\n"
                "**Persyaratan:**\n"
                "  • Badan usaha berbadan hukum\n"
                "  • Penanggung jawab teknis (Apoteker)\n"
                "  • Formula/komposisi produk lengkap\n\n"
                "🌐 Web: notifikasikosmetik.pom.go.id"
            ),
            "quick_replies": QUICK_MENUS["layanan"],
            "update_menu": "layanan",
        }

    if msg in ["izin_cppob", "🍱 izin cppob pangan olahan"]:
        return {
            "type": "text_with_menu",
            "message": (
                "🍱 **Penerbitan Izin Penerapan CPPOB**\n\n"
                "📌 *Izin Cara Produksi Pangan Olahan yang Baik bagi industri pangan.*\n\n"
                "**Prosedur:**\n"
                "  1. Permohonan izin CPPOB ke BPOM Lubuklinggau\n"
                "  2. Penilaian dokumen sistem manajemen pangan\n"
                "  3. Inspeksi sarana produksi pangan\n"
                "  4. Evaluasi GMP (Good Manufacturing Practice)\n"
                "  5. Penerbitan izin CPPOB (berlaku 5 tahun)\n\n"
                "**Persyaratan:**\n"
                "  • Izin usaha industri pangan (SIUP/NIB)\n"
                "  • Sistem HACCP terdokumentasi\n"
                "  • Tenaga ahli teknologi pangan\n\n"
                "🌐 Info: ereg.pom.go.id | 📞 (0733) 325678"
            ),
            "quick_replies": QUICK_MENUS["layanan"],
            "update_menu": "layanan",
        }

    if msg in ["pengaduan", "📢 pengaduan"]:
        return {
            "type": "text_with_menu",
            "message": (
                "📢 **Layanan Pengaduan Masyarakat BPOM**\n\n"
                "📌 *Sampaikan pengaduan Anda terkait produk obat, makanan, "
                "kosmetik, atau suplemen yang mencurigakan.*\n\n"
                "**Jenis Pengaduan yang Dilayani:**\n"
                "  1. Produk tanpa nomor izin edar BPOM\n"
                "  2. Produk kedaluwarsa yang masih beredar\n"
                "  3. Produk dengan klaim menyesatkan\n"
                "  4. Produk palsu atau dipalsukan\n"
                "  5. Iklan produk yang menyesatkan masyarakat\n"
                "  6. Efek samping/reaksi berbahaya setelah pemakaian produk\n\n"
                "**Cara Mengajukan Pengaduan:**\n"
                "  📞 Hotline BPOM: **1500533** (bebas pulsa)\n"
                "  📱 WhatsApp: 082160776367\n"
                "  📧 Email: halobpom@pom.go.id\n"
                "  🌐 Website: www.pom.go.id/pengaduan\n"
                "  📱 Aplikasi: BPOM Mobile (Play Store / App Store)\n"
                "  🏢 Datang langsung ke:\n"
                "     Jl. Yos Sudarso No. 12, Lubuklinggau\n"
                "     Senin–Kamis: 08.00–16.00 WIB\n"
                "     Jumat: 08.00–16.30 WIB\n\n"
                "⚠️ *Identitas pelapor dijaga kerahasiaannya. "
                "Setiap laporan akan ditindaklanjuti dalam 1x24 jam kerja.*"
            ),
            "quick_replies": QUICK_MENUS["main"],
            "update_menu": "main",
        }

    if msg in ["pengaduan_layanan", "📢 lapor produk ilegal"]:
        return {
            "type": "text_with_menu",
            "message": (
                "📢 **Lapor Produk Ilegal/Palsu**\n\n"
                "📌 *Laporkan temuan produk ilegal atau palsu kepada BPOM.*\n\n"
                "**Langkah Pelaporan:**\n"
                "  1. Dokumentasikan produk (foto kemasan, label, barcode)\n"
                "  2. Catat lokasi/toko tempat ditemukan produk\n"
                "  3. Catat tanggal penemuan dan keterangan lainnya\n"
                "  4. Hubungi BPOM melalui salah satu saluran berikut:\n\n"
                "📞 **Hotline:** 1500533 (bebas pulsa, 24 jam)\n"
                "📧 **Email:** halobpom@pom.go.id\n"
                "📱 **Aplikasi:** BPOM Mobile\n"
                "🌐 **Website:** www.pom.go.id/pengaduan\n\n"
                "✅ *Pelapor akan mendapat nomor tiket pengaduan untuk pemantauan tindak lanjut.*\n"
                "🔒 *Identitas pelapor dijaga kerahasiaannya.*"
            ),
            "quick_replies": QUICK_MENUS["main"],
            "update_menu": "main",
        }

    if msg in ["konsultasi", "💬 konsultasi"]:
        return {
            "type": "text_with_menu",
            "message": (
                "💬 **Layanan Informasi & Konsultasi BPOM**\n\n"
                "Anda dapat berkonsultasi melalui:\n\n"
                "☎️ **Hotline BPOM:** 1500533\n"
                "📧 **Email:** halobpom@pom.go.id\n"
                "🏢 **Datang langsung ke kantor:**\n"
                "    Jl.Yos Sudarso No.9c RT 03 Kelurahan Watervang, Kec.Lubuklinggau Timur I, Lubuklinggau 31625\n"
                "    Senin-Kamis: 08.00-16.00 WIB\n\n"
                "    Jumat: 08.00-16.30 WIB\n\n"
                "💬 **Live chat:** www.pom.go.id\n\n"
                "📱 **Sosial Media BPOM Lubuklinggau:**\n"
                "    Instagram: @bpom.lubuklinggau\n"
                "    Twitter: @bpomlbklinggau\n"
                "    Facebook: bpom.lubuklinggau\n"
                "    WhatsApp: 082160776367\n"
            ),
            "quick_replies": QUICK_MENUS["main"],
            "update_menu": "main",
        }

    # ---- CEK PRODUK ----
    if msg in ["cara_cek", "📱 cara cek produk"]:
        cara = "\n".join([f"  {i+1}. {c}" for i, c in enumerate(BPOM_DATA["produk_terdaftar"]["cara_cek"])])
        return {
            "type": "text_with_menu",
            "message": (
                f"📱 **Cara Mengecek Produk BPOM**\n\n{cara}\n\n"
                f"🌐 **Link langsung:** https://cekbpom.pom.go.id\n\n"
                f"💡 *Tips: Produk yang aman pasti memiliki nomor registrasi BPOM yang valid!*"
            ),
            "quick_replies": QUICK_MENUS["cek_produk"],
            "update_menu": "cek_produk",
        }

    if msg in ["kode_registrasi", "🔑 arti kode registrasi"]:
        kode = BPOM_DATA["produk_terdaftar"]["kode_registrasi"]
        kode_list = "\n".join([f"  **{k}** → {v}" for k, v in kode.items()])
        return {
            "type": "text_with_menu",
            "message": f"🔑 **Arti Kode Registrasi Produk BPOM**\n\n{kode_list}\n\n📌 *Contoh: MD 123456789012 berarti produk makanan produksi dalam negeri yang telah terdaftar BPOM*",
            "quick_replies": QUICK_MENUS["cek_produk"],
            "update_menu": "cek_produk",
        }

    if msg in ["produk_berbahaya", "⚠️ ciri produk berbahaya"]:
        ciri = "\n".join([f"  ⚠️ {c}" for c in BPOM_DATA["obat_berbahaya"]["ciri_ciri"]])
        cara = "\n".join([f"  ✅ {c}" for c in BPOM_DATA["obat_berbahaya"]["cara_hindari"]])
        return {
            "type": "text_with_menu",
            "message": (
                f"⚠️ **Ciri-ciri Produk Berbahaya/Ilegal**\n\n{ciri}\n\n"
                f"🛡️ **Cara Menghindarinya:**\n{cara}\n\n"
                f"📢 *Jika menemukan produk mencurigakan, segera laporkan ke BPOM di 1500533*"
            ),
            "quick_replies": QUICK_MENUS["cek_produk"],
            "update_menu": "cek_produk",
        }

    # ---- BACK ----
    if msg in ["back", "⬅️ kembali", "kembali", "menu utama"]:
        return {
            "type": "text_with_menu",
            "message": "🏠 Kembali ke Menu Utama. Ada yang bisa saya bantu? 😊",
            "quick_replies": QUICK_MENUS["main"],
            "update_menu": "main",
        }

    # ---- KEYWORD DETECTION ----
    keywords_map = {
        ("daftar", "registrasi", "pendaftaran", "izin edar"): "registrasi",
        ("sertifikasi", "cpob", "cpotb", "cppb", "cpkb", "cdob", "audit"): "layanan",
        ("laporkan", "lapor", "ilegal", "palsu", "tiruan"): "pengaduan",
        ("cek", "check", "periksa", "verifikasi"): "cara_cek",
        ("hotline", "telepon", "hubungi", "kontak", "alamat"): "kontak",
        ("tips", "saran", "cara aman", "keamanan"): "tips",
        ("biaya", "tarif", "harga", "bayar", "pnbp"): "registrasi",
        ("kosmetik", "skincare", "makeup"): "kode_registrasi",
        ("obat", "farmasi", "apotek", "dokter"): "kode_registrasi",
        ("makanan", "minuman", "pangan", "snack"): "kode_registrasi",
        ("suplemen", "vitamin", "herbal"): "kode_registrasi",
    }

    for keywords, action in keywords_map.items():
        if any(kw in msg for kw in keywords):
            # Redirect to appropriate handler
            return get_bot_response(action, session_data)

    # ---- DEFAULT ----
    return {
        "type": "text_with_menu",
        "message": (
            "🤔 Maaf, saya belum memahami pertanyaan Anda.\n\n"
            "Coba ketik salah satu topik berikut:\n"
            "• **registrasi** - Info pendaftaran produk\n"
            "• **cek produk** - Cara cek produk BPOM\n"
            "• **pengaduan** - Lapor produk ilegal\n"
            "• **kontak** - Hubungi BPOM\n"
            "• **tips** - Tips keamanan produk\n\n"
            "Atau pilih menu di bawah ini:"
        ),
        "quick_replies": QUICK_MENUS["main"],
        "update_menu": "main",
    }


# =============================================
# FLASK ROUTES
# =============================================


@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
        session["menu"] = "main"
        session["chat_history"] = []
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Pesan kosong"}), 400

    # Initialize session data
    if "menu" not in session:
        session["menu"] = "main"

    session_data = {"menu": session.get("menu", "main")}

    # Get bot response
    response = get_bot_response(user_message, session_data)

    # Update session menu
    if "update_menu" in response:
        session["menu"] = response["update_menu"]

    # Add timestamp
    response["timestamp"] = datetime.now().strftime("%H:%M")

    return jsonify(response)


@app.route("/api/reset", methods=["POST"])
def reset():
    session["menu"] = "main"
    session["chat_history"] = []
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

    session_data = {"menu": session.get("menu", "main")}
    response = get_bot_response(user_message, session_data)
    if "update_menu" in response:
        session["menu"] = response["update_menu"]

    response["timestamp"] = datetime.now().strftime("%H:%M")
    return jsonify(response)


@app.route("/api/welcome", methods=["GET"])
def welcome():
    """Return welcome message"""
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

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()

    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        response = get_bot_response(text)

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": response
            }
        )

    return "OK", 200

if __name__ == "__main__":
    print("=" * 50)
    print("  BPOM Lubuklinggau Chatbot")
    print("  Akses di: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
