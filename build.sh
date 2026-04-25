#!/usr/bin/env bash
# Render build script — รันก่อน start server
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
