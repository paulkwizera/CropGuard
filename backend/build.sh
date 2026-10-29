#!/usr/bin/env bash
# Render BUILD command for the backend:   bash backend/build.sh
set -o errexit
cd "$(dirname "$0")"

python -m pip install --upgrade pip
pip install -r requirements.txt

# ultralytics installs the normal OpenCV, which needs a graphics library (libGL) that Render's servers do not have
# ("ImportError: libGL.so.1"). Swap it for the identical "headless" build.
CV_VERSION="$(pip show opencv-python 2>/dev/null | sed -n 's/^Version: //p')"
if [ -n "$CV_VERSION" ]; then
  pip uninstall -y opencv-python
  pip install --no-deps "opencv-python-headless==${CV_VERSION}"
fi

python manage.py collectstatic --noinput
