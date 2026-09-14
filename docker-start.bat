@echo off
title Shorts Automation Studio - Docker Launcher
echo ========================================================
echo   Shorts Automation Studio - Starting Docker Containers
echo ========================================================
echo.
echo Pastikan aplikasi Docker Desktop sudah dalam keadaan RUNNING.
echo Memulai seluruh container (Postgres, Redis, Qdrant, API, Worker, Web)...
echo.
docker compose up -d
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Gagal menjalankan Docker Compose.
    echo Pastikan aplikasi Docker Desktop di Windows sudah dibuka dan siap.
    pause
    exit /b %errorlevel%
)

echo.
echo Status container:
docker compose ps
echo.
echo ========================================================
echo   Semua service telah aktif:
echo   - Web UI:    http://localhost:3000
echo   - API Docs:  http://localhost:8000/docs
echo   Untuk stop:  docker compose down
echo ========================================================
timeout /t 3 >nul
start http://localhost:3000
