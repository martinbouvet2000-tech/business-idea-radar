@echo off
title Idea Radar Dashboard
echo.
echo  ========================================
echo    IDEA RADAR — Starting dashboard...
echo  ========================================
echo.

:: Kill any existing instance on port 8421
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8421" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Start server in background
start /B python "%~dp0dashboard.py"

:: Wait for server to be ready
timeout /t 2 /nobreak >nul

:: Open browser
start http://localhost:8421/

echo  Dashboard running on http://localhost:8421/
echo  Press Ctrl+C or close this window to stop.
echo.

:: Keep window open (server runs in background)
pause >nul
