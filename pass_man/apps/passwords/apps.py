"""
Django app configuration for passwords app.
"""

from django.apps import AppConfig


class PasswordsConfig(AppConfig):
    """Configuration for passwords app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.passwords'
    verbose_name = 'Password Management'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.passwords.signals  # noqa
        except ImportError:
            pass