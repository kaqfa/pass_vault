"""
URL patterns for password management.

This module defines URL routing for password CRUD operations,
search functionality, and API endpoints.

Related Documentation:
- SRS.md: Section 6.1.3 Core Endpoints
- ARCHITECTURE.md: URL Routing Design
"""

from django.urls import path
from . import views

app_name = 'passwords'

urlpatterns = [
    # Web Views
    path('', views.PasswordListView.as_view(), name='list'),
    path('create/', views.PasswordCreateView.as_view(), name='create'),
    path('<uuid:password_id>/', views.PasswordDetailView.as_view(), name='detail'),
    path('<uuid:password_id>/edit/', views.PasswordEditView.as_view(), name='edit'),
    path('<uuid:password_id>/delete/', views.PasswordDeleteView.as_view(), name='delete'),
    
    # AJAX Views
    path('ajax/<uuid:password_id>/reveal/', views.ajax_reveal_password, name='ajax_reveal'),
    path('ajax/<uuid:password_id>/favorite/', views.ajax_toggle_favorite, name='ajax_favorite'),
    path('ajax/generate/', views.ajax_generate_password, name='ajax_generate'),
    
    # API Views
    path('api/', views.api_password_list, name='api_list'),
    path('api/create/', views.api_password_create, name='api_create'),
    path('api/<uuid:password_id>/', views.api_password_detail, name='api_detail'),
    path('api/<uuid:password_id>/update/', views.api_password_update, name='api_update'),
    path('api/<uuid:password_id>/delete/', views.api_password_delete, name='api_delete'),
]