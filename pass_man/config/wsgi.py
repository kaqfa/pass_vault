"""
WSGI config for Pass-Man Enterprise Password Management System.

This module contains the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/

Related Documentation:
- ARCHITECTURE.md: Deployment Architecture
- DEVELOPER_GUIDE.md: Deployment Guide
"""

import os
from django.core.wsgi import get_wsgi_application

# Set the default settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()