"""
Directory views for Pass-Man Enterprise Password Management System.

This module contains views for directory management including
CRUD operations and hierarchical organization.

Related Documentation:
- SRS.md: Section 4.2 Directory Management
- ARCHITECTURE.md: View Layer Design
"""

import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages

from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.directories.models import Directory
from apps.directories.services import DirectoryService
from apps.directories.serializers import DirectorySerializer, DirectoryTreeSerializer
from apps.core.views import BaseView
from apps.core.exceptions import ServiceError, ValidationError
from apps.groups.models import Group

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
        # Get user's groups
        user_groups = Group.objects.filter(
            Q(owner=request.user) | Q(usergroup__user=request.user)
        ).distinct()

        # Get directory trees for each group
        group_directories = []
        for group in user_groups:
            try:
                tree = DirectoryService.get_directory_tree(request.user, str(group.id))
                group_directories.append({
                    'group': group,
                    'directories': tree
                })
            except ServiceError:
                pass

        context = {
            'page_title': 'Directories',
            'user_groups': user_groups,
            'group_directories': group_directories
        }
        return render(request, self.template_name, context)


class DirectoryCreateView(LoginRequiredMixin, BaseView):
    """View for creating a new directory."""
    template_name = 'directories/form.html'

    def get(self, request):
        # Get user's groups
        user_groups = Group.objects.filter(
            Q(owner=request.user) | Q(usergroup__user=request.user)
        ).distinct()

        context = {
            'page_title': 'Create Directory',
            'user_groups': user_groups
        }
        return render(request, self.template_name, context)

    def post(self, request):
        try:
            directory = DirectoryService.create_directory(
                user=request.user,
                group_id=request.POST.get('group_id'),
                name=request.POST.get('name'),
                parent_id=request.POST.get('parent_id') or None,
                description=request.POST.get('description', '')
            )

            messages.success(
                request,
                f'Directory "{directory.name}" created successfully!'
            )

            # Check if HTMX request
            if request.headers.get('HX-Request'):
                return render(request, 'directories/partials/directory_row.html', {
                    'directory': directory
                })

            return redirect('directories:list')

        except ValidationError as e:
            user_groups = Group.objects.filter(
                Q(owner=request.user) | Q(usergroup__user=request.user)
            ).distinct()

            context = {
                'page_title': 'Create Directory',
                'user_groups': user_groups,
                'errors': e.details if hasattr(e, 'details') else {'__all__': [str(e)]},
                'form_data': request.POST
            }
            return render(request, self.template_name, context)

        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('directories:list')


class DirectoryEditView(LoginRequiredMixin, BaseView):
    """View for editing a directory."""
    template_name = 'directories/form.html'

    def get(self, request, directory_id):
        try:
            directory = DirectoryService.get_directory(request.user, directory_id)

            context = {
                'page_title': f'Edit Directory: {directory.name}',
                'directory': directory,
                'user_groups': [directory.group]
            }
            return render(request, self.template_name, context)

        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('directories:list')

    def post(self, request, directory_id):
        try:
            directory = DirectoryService.update_directory(
                user=request.user,
                directory_id=directory_id,
                name=request.POST.get('name'),
                description=request.POST.get('description', '')
            )

            messages.success(
                request,
                f'Directory "{directory.name}" updated successfully!'
            )

            return redirect('directories:list')

        except ValidationError as e:
            directory = DirectoryService.get_directory(request.user, directory_id)

            context = {
                'page_title': f'Edit Directory: {directory.name}',
                'directory': directory,
                'user_groups': [directory.group],
                'errors': e.details if hasattr(e, 'details') else {'__all__': [str(e)]},
                'form_data': request.POST
            }
            return render(request, self.template_name, context)

        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('directories:list')


class DirectoryDeleteView(LoginRequiredMixin, View):
    """View for deleting a directory."""

    def post(self, request, directory_id):
        try:
            move_passwords_to = request.POST.get('move_passwords_to')

            DirectoryService.delete_directory(
                user=request.user,
                directory_id=directory_id,
                move_passwords_to=move_passwords_to
            )

            messages.success(
                request,
                'Directory deleted successfully!'
            )

            return redirect('directories:list')

        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('directories:list')


# AJAX Views for HTMX
def ajax_create_directory(request):
    """AJAX endpoint to create a directory."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        directory = DirectoryService.create_directory(
            user=request.user,
            group_id=request.POST.get('group_id'),
            name=request.POST.get('name'),
            parent_id=request.POST.get('parent_id') or None,
            description=request.POST.get('description', '')
        )

        return JsonResponse({
            'success': True,
            'directory': {
                'id': str(directory.id),
                'name': directory.name,
                'description': directory.description,
                'level': directory.get_level()
            }
        })

    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'errors': e.details if hasattr(e, 'details') else {'__all__': [str(e)]}
        }, status=400)

    except ServiceError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def ajax_get_directories(request):
    """AJAX endpoint to get directories for a group."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    group_id = request.GET.get('group_id')

    if not group_id:
        return JsonResponse({'error': 'Group ID required'}, status=400)

    try:
        tree = DirectoryService.get_directory_tree(request.user, group_id)

        return JsonResponse({
            'success': True,
            'directories': tree
        })

    except ServiceError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
