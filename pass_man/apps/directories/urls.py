"""
URL patterns for the directories app.

This module defines API endpoints for directory organization functionality.

Related Documentation:
- SRS.md: Section 6.1.3 Core Endpoints
- ARCHITECTURE.md: API Design
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# API router for viewsets
router = DefaultRouter()
# router.register(r'', views.DirectoryViewSet, basename='directory')

app_name = 'directories'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Placeholder endpoints - to be implemented in Epic 5
    # path('create/', views.DirectoryCreateView.as_view(), name='create'),
    # path('<uuid:directory_id>/', views.DirectoryDetailView.as_view(), name='detail'),
]