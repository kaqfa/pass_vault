"""
Development settings for Pass-Man Enterprise Password Management System.

This module contains development-specific configuration that extends the base settings.
These settings are optimized for local development and debugging.

Related Documentation:
- DEVELOPER_GUIDE.md: Development Environment Setup
- CODING_STANDARDS.md: Environment Configuration
"""

from .base import *

# Debug settings
DEBUG = True







# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Security settings for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# Static files serving
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Database configuration for development (PostgreSQL specific)
# Removed MySQL-specific options that are invalid for PostgreSQL

# Logging configuration for development
LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'
LOGGING['loggers']['apps']['level'] = 'DEBUG'

# Development-specific settings
ALLOWED_HOSTS = ['*']  # Allow all hosts in development

# Cache timeout for development (shorter for testing)
CACHES['default']['TIMEOUT'] = 300  # 5 minutes

# JWT settings for development (shorter tokens for testing)
SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
})

# File upload settings for development
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755