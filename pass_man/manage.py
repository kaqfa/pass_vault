#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.

This script is the entry point for all Django management commands.
It automatically detects the environment and uses appropriate settings.

Related Documentation:
- DEVELOPER_GUIDE.md: Development Workflow
- CODING_STANDARDS.md: Development Best Practices
"""

import os
import sys

if __name__ == '__main__':
    # Determine which settings to use based on environment
    environment = os.environ.get('DJANGO_ENV', 'development')
    
    if environment == 'production':
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
    elif environment == 'testing':
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.testing')
    else:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    execute_from_command_line(sys.argv)