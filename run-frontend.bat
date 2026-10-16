@echo off
title CropGuard frontend
cd /d "%~dp0frontend"
echo.
echo  CropGuard is starting at http://127.0.0.1:5500
echo  Keep this window open while you work. Close it to stop.
echo.
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5500/index.html"
where python >nul 2>nul && (python -m http.server 5500) || (py -m http.server 5500)
pause
