#!/usr/bin/env bash
# Render START command for the backend:   bash backend/start.sh
set -o errexit
cd "$(dirname "$0")"

# Ultralytics wants a writable settings folder; the project folder on Render is read-only at run time.
export YOLO_CONFIG_DIR="${YOLO_CONFIG_DIR:-/tmp/Ultralytics}"

python manage.py migrate --noinput      # creates/updates the MongoDB collections; safe to repeat
# Linux's allocator keeps a separate memory pool per thread, which wastes a lot of RAM with PyTorch. Two pools is enough.
export MALLOC_ARENA_MAX="${MALLOC_ARENA_MAX:-2}"
export MALLOC_TRIM_THRESHOLD_="${MALLOC_TRIM_THRESHOLD_:-65536}"

exec gunicorn config.wsgi:application   # port, workers and timeouts come from gunicorn.conf.py
