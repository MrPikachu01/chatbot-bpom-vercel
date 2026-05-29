"""
test_telegram_menu.py
Jalankan: python test_telegram_menu.py
Script ini mengirim pesan dengan tombol menu ke bot Telegram Anda.
Gunakan untuk memastikan inline keyboard bekerja sebelum integrasi ke app utama.
"""

import urllib.request
import json
import sys

# ── Ganti dengan token bot Anda ──────────────────────────────────────────────
TOKEN   = "8741328752:AAGrDb6hfydbvpHKozUSKl4CX7lkw26wts0"
API_URL = f"https://api.telegram.org/bot{TOKEN}"
# ─────────────────────────────────────────────────────────────────────────────


def api_call(method: str, payload: dict):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{API_URL}/{method}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_me():
    return api_call("getMe", {})


def get_updates():
    return api_call("getUpdates", {"limit": 5, "offset": -5})


def send_menu(chat_id: int):
    payload = {
        "chat_id": chat_id,
        "text": "*Menu Layanan BPOM Lubuklinggau*\n\nSilakan pilih menu:",
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "Registrasi Produk",  "callback_data": "registrasi"}],
                [{"text": "Cek Produk BPOM",    "callback_data": "cek_produk"}],
                [{"text": "Pengaduan",           "callback_data": "pengaduan"}],
                [{"text": "Tips Keamanan",       "callback_data": "tips"}],
                [{"text": "Kontak BPOM",         "callback_data": "kontak"}],
                [{"text": "Regulasi",            "callback_data": "regulasi"}],
            ]
        }
    }
    return api_call("sendMessage", payload)


if __name__ == "__main__":
    print("=" * 50)
    print("  Test Telegram Inline Keyboard Menu")
    print("=" * 50)

    # Cek token valid
    print("\n1. Cek token bot...")
    me = get_me()
    if not me.get("ok"):
        print(f"   ERROR: Token tidak valid! {me}")
        sys.exit(1)
    bot_name = me["result"]["first_name"]
    print(f"   OK - Bot: {bot_name}")

    # Ambil chat_id terbaru
    print("\n2. Ambil chat_id dari pesan terakhir...")
    updates = get_updates()
    if not updates.get("ok") or not updates.get("result"):
        print("   ERROR: Tidak ada pesan masuk.")
        print("   Kirim pesan /start ke bot Anda dulu, lalu jalankan script ini lagi.")
        sys.exit(1)

    # Ambil chat_id dari update terakhir
    last = updates["result"][-1]
    if "message" in last:
        chat_id  = last["message"]["chat"]["id"]
        username = last["message"]["chat"].get("username") or last["message"]["chat"].get("first_name")
    elif "callback_query" in last:
        chat_id  = last["callback_query"]["message"]["chat"]["id"]
        username = last["callback_query"]["from"].get("username", "User")
    else:
        print("   ERROR: Format update tidak dikenal.")
        sys.exit(1)

    print(f"   OK - Chat ID: {chat_id} (@{username})")

    # Kirim menu
    print(f"\n3. Kirim inline keyboard menu ke @{username}...")
    result = send_menu(chat_id)
    if result.get("ok"):
        print("   OK - Menu berhasil dikirim! Cek Telegram Anda.")
    else:
        print(f"   ERROR: {result}")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("  SUKSES! Inline keyboard berfungsi.")
    print("  Sekarang update app_websocket.py dan restart Flask.")
    print("=" * 50)
