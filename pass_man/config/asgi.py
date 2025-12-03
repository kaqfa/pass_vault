"""
ASGI config for Pass-Man Enterprise Password Management System.

This module contains the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/

Related Documentation:
- ARCHITECTURE.md: Deployment Architecture
- DEVELOPER_GUIDE.md: Deployment Guide
"""

import os
from django.core.asgi import get_asgi_application

# Set the default settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_asgi_application()