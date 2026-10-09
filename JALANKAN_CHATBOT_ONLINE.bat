@echo off
title Chatbot Gunadarma RAG v2.0 - Server Launcher
color 0A

echo =======================================================
echo    MENYALAKAN SERVER CHATBOT ASISTEN AI GUNADARMA
echo =======================================================
echo.

cd /d "C:\Users\MyBook Hype AMD\Documents\project-chatbot"

echo [1/3] Menyiapkan server FastAPI (Python)...
taskkill /F /IM cloudflared.exe >nul 2>&1

:: Cek apakah port 8000 sudah jalan
netstat -ano | findstr :8000 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    echo [2/3] Memulai backend Python di background...
    start "" /B py -3 -m uvicorn app:app --host 127.0.0.1 --port 8000
    timeout /t 5 /nobreak >nul
) else (
    echo [2/3] Backend Python sudah aktif di port 8000.
)

echo [3/3] Membuka terowongan Cloudflare publik...
del /f /q tunnel.log >nul 2>&1
start "" /B cloudflared.exe tunnel --url http://127.0.0.1:8000 > tunnel.log 2>&1

echo Menghubungkan ke jaringan publik Cloudflare (tunggu 5 detik)...
timeout /t 6 /nobreak >nul

echo.
echo =======================================================
echo    CHATBOT ONLINE DAN BERHASIL DIAKTIFKAN!
echo =======================================================
echo.
echo Mencari URL publik Anda...
powershell -Command "if (Test-Path 'tunnel.log') { $m = Select-String -Path 'tunnel.log' -Pattern 'https://[a-zA-Z0-9-]+\.trycloudflare\.com'; if ($m) { Write-Host 'Link Publik Anda: ' -ForegroundColor Cyan; Write-Host $m.Matches[0].Value -ForegroundColor Yellow; Start-Process $m.Matches[0].Value } else { Write-Host 'Buka link tunnel di file tunnel.log' } }"
echo.
echo =======================================================
echo Jendela ini boleh diminimize. Server akan tetap jalan!
echo Untuk mematikan server, jalankan file MATIKAN_CHATBOT.bat.
echo =======================================================
pause
