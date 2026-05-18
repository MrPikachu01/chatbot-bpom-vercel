"""
diagnosa.py — Cek semua koneksi Telegram + Dashboard
Jalankan: python diagnosa.py
"""
import urllib.request
import json
import sys
import os

TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "8741328752:AAGFYg8fJMwnXwF18B_papxkItL_eVSyYJI")
SECRET  = os.getenv("TELEGRAM_WEBHOOK_SECRET", "bpom_secret_2024")
API     = f"https://api.telegram.org/bot{TOKEN}"
LOCAL   = "http://127.0.0.1:5000"

OK  = "[OK]"
ERR = "[ERROR]"
WRN = "[WARN]"

def req(url, payload=None):
    try:
        data = json.dumps(payload).encode() if payload else None
        r = urllib.request.Request(url, data=data,
            headers={"Content-Type":"application/json"} if data else {})
        with urllib.request.urlopen(r, timeout=8) as resp:
            return json.loads(resp.read()), None
    except Exception as e:
        return None, str(e)

print("\n" + "="*55)
print("  DIAGNOSA SISTEM BPOM LUBUKLINGGAU")
print("="*55)

# 1. Cek token Telegram
print("\n[1] CEK TOKEN TELEGRAM")
data, err = req(f"{API}/getMe")
if err or not data or not data.get("ok"):
    print(f"  {ERR} Token tidak valid atau expired!")
    print(f"       Solusi: /revoke di BotFather untuk token baru")
    sys.exit(1)
print(f"  {OK}  Bot: {data['result']['first_name']} (@{data['result'].get('username','-')})")

# 2. Cek webhook terdaftar
print("\n[2] CEK STATUS WEBHOOK")
data, err = req(f"{API}/getWebhookInfo")
if err or not data or not data.get("ok"):
    print(f"  {ERR} Gagal ambil info webhook: {err}")
else:
    wh = data["result"]
    url = wh.get("url", "")
    pending = wh.get("pending_update_count", 0)
    last_err = wh.get("last_error_message", "")
    last_err_date = wh.get("last_error_date", 0)

    if not url:
        print(f"  {ERR} Webhook BELUM terdaftar!")
        print(f"       Solusi: Jalankan setWebhook dengan URL ngrok terbaru")
    else:
        print(f"  {OK}  URL: {url}")
        if "ngrok" in url:
            print(f"  {WRN} Menggunakan ngrok — pastikan ngrok masih berjalan!")

    if pending > 0:
        print(f"  {WRN} Ada {pending} pesan tertunda (belum diproses)")

    if last_err:
        print(f"  {ERR} Error terakhir: {last_err}")
        print(f"       Kemungkinan: Flask tidak berjalan saat pesan datang")
    else:
        print(f"  {OK}  Tidak ada error webhook")

# 3. Cek Flask berjalan
print("\n[3] CEK FLASK SERVER")
data, err = req(f"{LOCAL}/api/welcome")
if err:
    print(f"  {ERR} Flask TIDAK berjalan di port 5000!")
    print(f"       Solusi: python app_websocket.py")
else:
    print(f"  {OK}  Flask berjalan di {LOCAL}")

# 4. Cek dashboard bisa diakses
print("\n[4] CEK DASHBOARD")
try:
    r = urllib.request.urlopen(f"{LOCAL}/dashboard", timeout=5)
    if r.status == 200:
        print(f"  {OK}  Dashboard: {LOCAL}/dashboard")
    else:
        print(f"  {ERR} Dashboard error: HTTP {r.status}")
except Exception as e:
    print(f"  {ERR} Dashboard tidak bisa diakses: {e}")

# 5. Cek token di Flask
print("\n[5] CEK TOKEN DI FLASK")
data, err = req(f"{LOCAL}/setup/telegram")
if err:
    print(f"  {ERR} Flask tidak jalan, skip")
elif data:
    token_set = data.get("token_set", False)
    if token_set:
        print(f"  {OK}  TELEGRAM_BOT_TOKEN sudah diset di Flask")
        wh_url = data.get("webhook_url","")
        print(f"  {OK}  Webhook URL Flask: {wh_url}")
    else:
        print(f"  {ERR} TELEGRAM_BOT_TOKEN BELUM diset di Flask!")
        print(f"       Solusi: Jalankan Flask dengan:")
        print(f'         $env:TELEGRAM_BOT_TOKEN="{TOKEN}"')
        print(f'         $env:TELEGRAM_WEBHOOK_SECRET="{SECRET}"')
        print(f"         python app_websocket.py")

# 6. Cek ngrok masih aktif
print("\n[6] CEK NGROK")
try:
    r = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=3)
    tunnels = json.loads(r.read())
    for t in tunnels.get("tunnels", []):
        if "https" in t.get("public_url",""):
            print(f"  {OK}  ngrok aktif: {t['public_url']}")
            # Bandingkan dengan webhook
            if data and not err:
                wh_url = data.get("webhook_url","")
                ngrok_url = t['public_url']
                if ngrok_url in wh_url or wh_url.startswith(ngrok_url):
                    print(f"  {OK}  URL ngrok SESUAI dengan webhook")
                else:
                    print(f"  {ERR} URL ngrok BERBEDA dengan webhook!")
                    print(f"       ngrok  : {ngrok_url}")
                    print(f"       webhook: {wh_url}")
                    print(f"       Solusi : Daftarkan ulang webhook dengan URL ngrok baru")
                    print(f'       curl -X POST "{API}/setWebhook" -H "Content-Type: application/json"')
                    print(f'            -d "{{\"url\":\"{ngrok_url}/webhook/telegram\",\"secret_token\":\"{SECRET}\"}}"')
except Exception:
    print(f"  {WRN} ngrok web interface tidak ditemukan di port 4040")
    print(f"       Pastikan ngrok masih berjalan: ngrok.exe http 5000")

print("\n" + "="*55)
print("  DIAGNOSA SELESAI")
print("="*55 + "\n")
