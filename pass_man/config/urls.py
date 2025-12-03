"""
Main URL configuration for Pass-Man Enterprise Password Management System.

This module defines the root URL routing for the entire application,
including web views, API endpoints, and admin interface.

Related Documentation:
- ARCHITECTURE.md: URL Routing Design
- SRS.md: Section 6.1.3 Core Endpoints
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # Core application (home page, dashboard, health check)
    path('', include('apps.core.urls')),
    
    # User authentication and management
    path('auth/', include('apps.users.web_urls')),
    
    # Password management
    path('passwords/', include('apps.passwords.urls')),
    
    # Groups management
    path('groups/', include('apps.groups.urls')),
    
    # API endpoints
    path('api/auth/', include('apps.users.urls')),
    path('api/passwords/', include('apps.passwords.urls')),
    path('api/groups/', include('apps.groups.urls')),
    
    # Directories management (to be implemented in Epic 5)
    # path('directories/', include('apps.directories.urls')),
    # path('api/directories/', include('apps.directories.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug Toolbar
    try:
        import debug_toolbar
        urlpatterns += [
            path('__debug__/', include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass

# Custom error handlers
handler400 = 'apps.core.views.handler400'
handler403 = 'apps.core.views.handler403'
handler404 = 'apps.core.views.handler404'
handler500 = 'apps.core.views.handler500'

# Admin site customization
admin.site.site_header = 'Pass-Man Administration'
admin.site.site_title = 'Pass-Man Admin'
admin.site.index_title = 'Welcome to Pass-Man Administration'