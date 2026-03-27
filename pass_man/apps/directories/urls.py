"""
URL patterns for the directories app.

This module defines API and web endpoints for directory organization functionality.

Related Documentation:
- SRS.md: Section 6.1.3 Core Endpoints
- ARCHITECTURE.md: API Design
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'directories'

# API Router
router = DefaultRouter()
router.register(r'api', views.DirectoryViewSet, basename='directory-api')

urlpatterns = [
    # Template Views
    path('', views.DirectoryListView.as_view(), name='list'),
    path('create/', views.DirectoryCreateView.as_view(), name='create'),
    path('<uuid:directory_id>/edit/', views.DirectoryEditView.as_view(), name='edit'),
    path('<uuid:directory_id>/delete/', views.DirectoryDeleteView.as_view(), name='delete'),

    # AJAX Views
    path('ajax/create/', views.ajax_create_directory, name='ajax_create'),
    path('ajax/get/', views.ajax_get_directories, name='ajax_get'),

    # API Routes
    path('', include(router.urls)),
]