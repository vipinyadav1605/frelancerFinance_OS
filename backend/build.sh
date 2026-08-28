#!/usr/bin/env bash
# Render build command. Set the Build Command in the Render dashboard to:
#   bash build.sh
# (using "bash build.sh" instead of "./build.sh" avoids relying on this
# file's execute bit, which Windows git checkouts don't reliably preserve.)
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
