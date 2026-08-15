import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flyrain_kb.settings.prod')

application = get_asgi_application()
