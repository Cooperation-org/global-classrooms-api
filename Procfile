web: gunicorn global_classrooms.wsgi --workers 2 --timeout 120 --max-requests 1000 --max-requests-jitter 50
release: python manage.py migrate