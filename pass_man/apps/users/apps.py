"""
Users app configuration for Pass-Man Enterprise Password Management System.

This app handles user authentication, registration, and user management
functionality as specified in the SRS.

Related Documentation:
- SRS.md: Section 3.1 Authentication & Authorization
- ARCHITECTURE.md: User Model section
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configuration for the users application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'Users'
    
    def ready(self):
        """
        Initialize the app when Django starts.
        
        Import signal handlers for user-related events.
        """
        try:
            import apps.users.signals  # noqa
        except ImportError:
            pass