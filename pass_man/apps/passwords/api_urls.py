"""
API URL patterns for password management.

This module defines API endpoints for password CRUD operations.
"""

from django.urls import path
from . import views

app_name = 'passwords_api'

urlpatterns = [
    path('', views.api_password_list, name='list'),
    path('create/', views.api_password_create, name='create'),
    path('<uuid:password_id>/', views.api_password_detail, name='detail'),
    path('<uuid:password_id>/update/', views.api_password_update, name='update'),
    path('<uuid:password_id>/delete/', views.api_password_delete, name='delete'),
]
