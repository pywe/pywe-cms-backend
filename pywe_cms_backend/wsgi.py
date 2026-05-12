"""WSGI config for pywe-cms-backend."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pywe_cms_backend.settings")

application = get_wsgi_application()
