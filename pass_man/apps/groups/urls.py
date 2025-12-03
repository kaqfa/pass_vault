"""
URL patterns for group management.

This module defines URL routing for group CRUD operations,
member management, and API endpoints.

Related Documentation:
- SRS.md: Section 6.1.3 Core Endpoints
- ARCHITECTURE.md: URL Routing Design
"""

from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    # Web Views
    path('', views.GroupListView.as_view(), name='list'),
    path('create/', views.GroupCreateView.as_view(), name='create'),
    path('<uuid:group_id>/', views.GroupDetailView.as_view(), name='detail'),
    path('<uuid:group_id>/edit/', views.GroupEditView.as_view(), name='edit'),
    path('<uuid:group_id>/delete/', views.GroupDeleteView.as_view(), name='delete'),
    path('<uuid:group_id>/members/', views.GroupMemberManageView.as_view(), name='members'),
    
    # AJAX Views
    path('ajax/<uuid:group_id>/add-member/', views.ajax_add_member, name='ajax_add_member'),
    path('ajax/<uuid:group_id>/remove-member/<uuid:member_id>/', views.ajax_remove_member, name='ajax_remove_member'),
    path('ajax/<uuid:group_id>/change-role/<uuid:member_id>/', views.ajax_change_role, name='ajax_change_role'),
    
    # API Views
    path('api/', views.api_group_list, name='api_list'),
    path('api/create/', views.api_group_create, name='api_create'),
    path('api/<uuid:group_id>/', views.api_group_detail, name='api_detail'),
    path('api/<uuid:group_id>/update/', views.api_group_update, name='api_update'),
    path('api/<uuid:group_id>/delete/', views.api_group_delete, name='api_delete'),
]