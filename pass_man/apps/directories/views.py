"""
Directory views for Pass-Man Enterprise Password Management System.

This module contains views for directory management including
CRUD operations and hierarchical organization.

Related Documentation:
- SRS.md: Section 4.2 Directory Management
- ARCHITECTURE.md: View Layer Design
"""

import logging
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q

from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.directories.models import Directory
from apps.directories.serializers import DirectorySerializer, DirectoryTreeSerializer
from apps.core.views import BaseView

logger = logging.getLogger(__name__)


class DirectoryViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for Directory management.
    
    Provides CRUD operations for directories with permission checking.
    """
    serializer_class = DirectorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """
        Return directories accessible to the user.
        
        Users can see directories if:
        1. They created the directory
        2. They belong to the group that owns the directory
        """
        user = self.request.user
        if user.is_anonymous:
            return Directory.objects.none()
            
        return Directory.objects.filter(
            Q(created_by=user) |
            Q(group__usergroup__user=user)
        ).distinct()

    def perform_create(self, serializer):
        """Set the creator when saving a new directory."""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """
        Return a hierarchical tree of directories.
        """
        # Get root directories (no parent) accessible to user
        queryset = self.get_queryset().filter(parent__isnull=True)
        serializer = DirectoryTreeSerializer(queryset, many=True)
        return Response(serializer.data)


# Template Views
class DirectoryListView(LoginRequiredMixin, BaseView):
    """View for listing directories."""
    template_name = 'directories/list.html'
    
    def get(self, request):
        context = {
            'page_title': 'Directories',
        }
        return render(request, self.template_name, context)
