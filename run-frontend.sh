#!/usr/bin/env sh
# Starts the CropGuard frontend at http://127.0.0.1:5500  (Ctrl+C to stop)
cd "$(dirname "$0")/frontend" || exit 1
echo "CropGuard is starting at http://127.0.0.1:5500"
python3 -m http.server 5500 || python -m http.server 5500
