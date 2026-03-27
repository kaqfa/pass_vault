"""
URL patterns for the notifications app.
"""

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Views
    path('', views.NotificationListView.as_view(), name='list'),

    # AJAX endpoints
    path('ajax/unread-count/', views.get_unread_count, name='unread_count'),
    path('ajax/mark-read/<uuid:notification_id>/', views.mark_as_read, name='mark_read'),
    path('ajax/mark-all-read/', views.mark_all_as_read, name='mark_all_read'),
    path('ajax/dropdown/', views.get_notification_dropdown, name='dropdown'),
]
