@echo off
title BPOM Chatbot Launcher

echo =====================================
echo Menjalankan Flask (port 5000)...
echo =====================================

start "BPOM Flask Server" cmd /k "python app_websocket.py"

timeout /t 5 /nobreak >nul

echo.
echo =====================================
echo Memulai Cloudflare Tunnel...
echo =====================================

start "Cloudflare Tunnel" cmd /k "cloudflared.exe tunnel --url http://localhost:5000"

echo.
echo =====================================
echo Bot BPOM sedang berjalan!
echo =====================================

echo.
echo Chatbot : http://localhost:5000
echo Dashboard: http://localhost:5000/dashboard

echo.
echo PERHATIAN:
echo Salin URL Cloudflare Tunnel dari jendela
echo "Cloudflare Tunnel", lalu daftarkan
echo webhook Telegram.

pause