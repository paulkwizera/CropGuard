#!/usr/bin/env sh
# Starts the CropGuard backend at http://127.0.0.1:8000 (needs MongoDB: docker compose up -d)
cd "$(dirname "$0")/backend" || exit 1
[ -d venv ] || python3 -m venv venv
. venv/bin/activate
pip install -q -r requirements.txt
python manage.py migrate
python manage.py runserver
