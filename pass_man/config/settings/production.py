"""
Production settings for Pass-Man Enterprise Password Management System.

This module contains production-specific configuration that extends the base settings.
These settings are optimized for security, performance, and reliability in production.

Related Documentation:
- SRS.md: Section 4.2 Security Requirements
- ARCHITECTURE.md: Deployment Architecture
- CODING_STANDARDS.md: Deployment Standards
"""

from .base import *

# Security settings for production
DEBUG = False

# Security headers
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)

# Static files configuration for production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Database configuration for production
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['OPTIONS'].update({
    'sslmode': 'require',
    'connect_timeout': 10,
    'options': '-c default_transaction_isolation=serializable'
})

# Cache configuration for production
CACHES['default']['TIMEOUT'] = 3600  # 1 hour
CACHES['default']['OPTIONS'].update({
    'CONNECTION_POOL_KWARGS': {
        'max_connections': 50,
        'retry_on_timeout': True,
    },
    'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
    'IGNORE_EXCEPTIONS': True,
})

# Session configuration for production
SESSION_COOKIE_AGE = 28800  # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_TIMEOUT = 30

# Logging configuration for production
LOGGING['handlers']['file']['filename'] = '/var/log/passmanager/django.log'
LOGGING['handlers']['error_file'] = {
    'level': 'ERROR',
    'class': 'logging.FileHandler',
    'filename': '/var/log/passmanager/django_errors.log',
    'formatter': 'verbose',
}
LOGGING['handlers']['security_file'] = {
    'level': 'WARNING',
    'class': 'logging.FileHandler',
    'filename': '/var/log/passmanager/security.log',
    'formatter': 'verbose',
}

LOGGING['loggers'].update({
    'django.security': {
        'handlers': ['security_file', 'console'],
        'level': 'WARNING',
        'propagate': False,
    },
    'django.request': {
        'handlers': ['error_file', 'console'],
        'level': 'ERROR',
        'propagate': False,
    },
})

# Performance optimizations
USE_TZ = True
USE_L10N = True

# File upload settings for production
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755
FILE_UPLOAD_TEMP_DIR = '/tmp/passmanager_uploads'

# CORS settings for production (restrictive)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]
)

# JWT settings for production
SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=24),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
})

# Admin settings
ADMIN_URL = config('ADMIN_URL', default='admin/')

# Monitoring and health checks
HEALTH_CHECK_ENABLED = True

# Rate limiting (if implemented)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Backup settings
BACKUP_ENABLED = config('BACKUP_ENABLED', default=True, cast=bool)
BACKUP_STORAGE = config('BACKUP_STORAGE', default='local')

# Error reporting
ADMINS = [
    ('Admin', config('ADMIN_EMAIL', default='admin@passmanager.com')),
]
MANAGERS = ADMINS

# Server email
SERVER_EMAIL = config('SERVER_EMAIL', default='server@passmanager.com')

# Security middleware order (important for production)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]