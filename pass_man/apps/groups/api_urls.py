"""
API URL patterns for group management.

This module defines API endpoints for group CRUD operations.
"""

from django.urls import path
from . import views

app_name = 'groups_api'

urlpatterns = [
    path('', views.api_group_list, name='list'),
    path('create/', views.api_group_create, name='create'),
    path('<uuid:group_id>/', views.api_group_detail, name='detail'),
    path('<uuid:group_id>/update/', views.api_group_update, name='update'),
    path('<uuid:group_id>/delete/', views.api_group_delete, name='delete'),
]
