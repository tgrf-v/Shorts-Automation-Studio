@echo off
title Shorts Automation Studio - Dev Launcher
echo ========================================================
echo   Shorts Automation Studio - Starting Local Dev
echo ========================================================
echo.
echo Starting FastAPI Backend on http://localhost:8000 ...
start "Shorts API" cmd /k "cd /d %~dp0apps\api && python -m uvicorn app.main:app --reload --port 8000"

echo Starting Next.js Frontend on http://localhost:3000 ...
start "Shorts Web" cmd /k "cd /d %~dp0apps\web && npm run dev"

echo.
echo ========================================================
echo   Both services started in background windows!
echo   - Web UI:    http://localhost:3000
echo   - API Docs:  http://localhost:8000/docs
echo ========================================================
timeout /t 3 >nul
start http://localhost:3000
