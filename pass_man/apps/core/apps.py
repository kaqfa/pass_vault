"""
Core app configuration for Pass-Man Enterprise Password Management System.

This app contains shared utilities, base models, and common functionality
used across all other applications in the project.

Related Documentation:
- ARCHITECTURE.md: Core App section
- CODING_STANDARDS.md: Django Best Practices
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the core application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'
    
    def ready(self):
        """
        Initialize the app when Django starts.
        
        This method is called when the app is ready and can be used
        to register signals, perform startup tasks, etc.
        """
        # Import signal handlers
        try:
            import apps.core.signals  # noqa
        except ImportError:
            pass