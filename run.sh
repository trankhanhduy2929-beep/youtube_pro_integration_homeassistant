#!/usr/bin/with-contenv bashio
exec gunicorn --bind 0.0.0.0:2032 --worker-class gthread --workers 1 --threads 8 --timeout 0 --keep-alive 10 --access-logfile - --error-logfile - app:app
