#!/usr/bin/env bash
# Redeploy script for the server (/var/www/hamdaancollege). Pulls the
# latest main, installs any new dependencies, applies migrations, collects
# static files, and restarts gunicorn. Run as root on the server:
#   cd /var/www/hamdaancollege && ./deploy.sh
set -euo pipefail

cd "$(dirname "$0")"

git pull origin main
./venv/bin/pip install --quiet -r requirements.txt
./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py collectstatic --noinput
chown -R www-data:www-data .
systemctl restart hamdaancollege.service

echo "Deployed $(git rev-parse --short HEAD)."
