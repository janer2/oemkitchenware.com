@echo off
chcp 65001 >nul
title XSmallAppliance Server
echo.
echo   XSmallAppliance - Catalog Viewer
echo   http://localhost:8080
echo   Press Ctrl+C to stop
echo.
start http://localhost:8080
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python -m http.server 8080
) else (
    "C:\Users\Administrator\AppData\Roaming\Accio\pre-install\ab1f8a6ee51b\python\python.exe" -m http.server 8080
)
pause
