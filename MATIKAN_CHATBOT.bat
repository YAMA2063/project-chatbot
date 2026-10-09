@echo off
title Hentikan Server Chatbot Gunadarma
color 0C

echo =======================================================
echo    MEMATIKAN SERVER CHATBOT GUNADARMA
echo =======================================================
echo.

taskkill /F /IM cloudflared.exe >nul 2>&1
echo [OK] Cloudflare Tunnel dimatikan.

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo [OK] Backend Python port 8000 dimatikan.

echo.
echo =======================================================
echo    SEMUA SERVER CHATBOT TELAH DIMATIKAN DENGAN BERSIH
echo =======================================================
echo.
pause
