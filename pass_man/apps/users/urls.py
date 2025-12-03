"""
API URL patterns for the users app.

This module defines API endpoints for user management functionality.
These endpoints will be implemented progressively in Epic 2.

Related Documentation:
- SRS.md: Section 6.1.3 Core Endpoints
- ARCHITECTURE.md: API Design
"""

from django.urls import path
from . import views

app_name = 'users_api'

urlpatterns = [
    # Authentication API endpoints
    path('register/', views.api_register, name='api_register'),
    path('login/', views.api_login, name='api_login'),
    path('profile/', views.api_profile, name='api_profile'),
    
    # To be implemented in future tasks
    # path('logout/', views.api_logout, name='api_logout'),
    # path('password-reset/', views.api_password_reset, name='api_password_reset'),
    # path('change-password/', views.api_change_password, name='api_change_password'),
]