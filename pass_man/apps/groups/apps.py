"""
Django app configuration for groups app.
"""

from django.apps import AppConfig


class GroupsConfig(AppConfig):
    """Configuration for groups app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.groups'
    verbose_name = 'Group Management'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.groups.signals  # noqa
        except ImportError:
            pass