"""
URL patterns for the directories app.

This module defines API endpoints for directory organization functionality.

Related Documentation:
- SRS.md: Section 6.1.3 Core Endpoints
- ARCHITECTURE.md: API Design
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'directories'

urlpatterns = [
    # Template Views
    path('list/', views.DirectoryListView.as_view(), name='list'),
]