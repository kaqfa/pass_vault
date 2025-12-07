"""
API URL patterns for directory management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'directories_api'

# API router for viewsets
router = DefaultRouter()
router.register(r'', views.DirectoryViewSet, basename='directory')

urlpatterns = [
    path('', include(router.urls)),
]
