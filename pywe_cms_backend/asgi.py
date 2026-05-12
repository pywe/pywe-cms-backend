"""ASGI config for pywe-cms-backend."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pywe_cms_backend.settings")

application = get_asgi_application()
