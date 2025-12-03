"""
URL patterns for the core app.

This module defines URL routing for core functionality including
the dashboard, health checks, and common pages.

Related Documentation:
- ARCHITECTURE.md: URL Routing
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Home page
    path('', views.HomeView.as_view(), name='home'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Health check endpoint
    path('health/', views.health_check, name='health_check'),
]