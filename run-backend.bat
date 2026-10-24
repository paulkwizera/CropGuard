@echo off
title CropGuard backend
cd /d "%~dp0backend"
echo.
echo  Starting the CropGuard backend at http://127.0.0.1:8000
echo  Needs MongoDB (docker compose up -d, or a MongoDB Atlas link in .env).
echo.
if not exist venv ( python -m venv venv || py -m venv venv )
call venv\Scripts\activate
pip install -q -r requirements.txt
python manage.py migrate
python manage.py runserver
pause
