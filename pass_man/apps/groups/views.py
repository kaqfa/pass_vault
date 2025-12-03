"""
Group views for Pass-Man Enterprise Password Management System.

This module contains views for group management including creation, member management,
role assignment, and group administration.

Related Documentation:
- SRS.md: Section 3.2 Group Management
- ARCHITECTURE.md: View Layer Design
- CODING_STANDARDS.md: View Best Practices
"""

import logging
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView, View
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.views import BaseView
from apps.core.exceptions import ServiceError, ValidationError as CustomValidationError
from apps.groups.services import GroupService
from apps.groups.models import Group, UserGroup

User = get_user_model()
logger = logging.getLogger(__name__)


class GroupListView(LoginRequiredMixin, BaseView):
    """
    Group list view with search and filtering.
    
    Displays user's accessible groups with search and filter capabilities.
    """
    template_name = 'groups/group_list.html'
    
    def get(self, request):
        """Display group list with search and filters."""
        try:
            # Get search parameters
            query = request.GET.get('q', '').strip()
            role_filter = request.GET.get('role')
            
            # Get user's groups
            groups = GroupService.get_user_groups(request.user, query, role_filter)
            
            # Pagination
            paginator = Paginator(groups, 20)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            context = {
                'page_title': 'My Groups',
                'groups': page_obj,
                'search_query': query,
                'current_filters': {
                    'role': role_filter
                },
                'role_choices': UserGroup.Role.choices,
                'total_count': len(groups)
            }
            
            return render(request, self.template_name, context)
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('core:dashboard')


class GroupDetailView(LoginRequiredMixin, BaseView):
    """
    Group detail view with member management.
    
    Shows group details, members, and management options.
    """
    template_name = 'groups/group_detail.html'
    
    def get(self, request, group_id):
        """Display group details."""
        try:
            group = GroupService.get_group(request.user, group_id)
            
            # Get group members
            members = GroupService.get_group_members(request.user, group_id)
            
            # Get user's role in group
            user_role = group.get_user_role(request.user)
            
            # Check permissions
            can_manage_members = group.can_user_manage_members(request.user)
            can_delete_group = (group.owner == request.user)
            
            context = {
                'page_title': f'Group: {group.name}',
                'group': group,
                'members': members,
                'user_role': user_role,
                'can_manage_members': can_manage_members,
                'can_delete_group': can_delete_group,
                'role_choices': UserGroup.Role.choices
            }
            
            return render(request, self.template_name, context)
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('groups:list')


class GroupCreateView(LoginRequiredMixin, BaseView):
    """
    Group creation view.
    
    Handles group creation with validation.
    """
    template_name = 'groups/group_form.html'
    
    def get(self, request):
        """Display group creation form."""
        context = {
            'page_title': 'Create New Group',
            'is_create': True
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle group creation."""
        try:
            # Get form data
            group_data = {
                'name': request.POST.get('name', '').strip(),
                'description': request.POST.get('description', '').strip(),
            }
            
            # Create group
            group = GroupService.create_group(request.user, group_data)
            
            messages.success(
                request,
                f'Group "{group.name}" created successfully!'
            )
            
            return redirect('groups:detail', group_id=group.id)
            
        except CustomValidationError as e:
            context = {
                'page_title': 'Create New Group',
                'is_create': True,
                'errors': e.details,
                'form_data': group_data
            }
            
            return render(request, self.template_name, context)
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('groups:create')


class GroupEditView(LoginRequiredMixin, BaseView):
    """
    Group edit view.
    
    Handles group updates.
    """
    template_name = 'groups/group_form.html'
    
    def get(self, request, group_id):
        """Display group edit form."""
        try:
            group = GroupService.get_group(request.user, group_id)
            
            # Check edit permission
            if not GroupService._can_user_edit_group(request.user, group):
                messages.error(request, "You don't have permission to edit this group.")
                return redirect('groups:detail', group_id=group_id)
            
            context = {
                'page_title': f'Edit Group: {group.name}',
                'group': group,
                'is_create': False
            }
            
            return render(request, self.template_name, context)
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('groups:list')
    
    def post(self, request, group_id):
        """Handle group update."""
        try:
            # Get form data
            group_data = {
                'name': request.POST.get('name', '').strip(),
                'description': request.POST.get('description', '').strip(),
            }
            
            # Update group
            group = GroupService.update_group(request.user, group_id, group_data)
            
            messages.success(
                request,
                f'Group "{group.name}" updated successfully!'
            )
            
            return redirect('groups:detail', group_id=group.id)
            
        except CustomValidationError as e:
            try:
                group = GroupService.get_group(request.user, group_id)
                
                context = {
                    'page_title': f'Edit Group: {group.name}',
                    'group': group,
                    'is_create': False,
                    'errors': e.details,
                    'form_data': group_data
                }
                
                return render(request, self.template_name, context)
                
            except ServiceError:
                messages.error(request, "Group not found.")
                return redirect('groups:list')
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('groups:detail', group_id=group_id)


class GroupDeleteView(LoginRequiredMixin, View):
    """
    Group deletion view.
    
    Handles group deletion with confirmation.
    """
    
    def post(self, request, group_id):
        """Handle group deletion."""
        try:
            group = GroupService.get_group(request.user, group_id)
            
            # Check if it's a personal group
            if group.is_personal:
                messages.error(request, "Personal groups cannot be deleted.")
                return redirect('groups:detail', group_id=group_id)
            
            group_name = group.name
            
            # Delete group
            GroupService.delete_group(request.user, group_id)
            
            messages.success(
                request,
                f'Group "{group_name}" deleted successfully!'
            )
            
            return redirect('groups:list')
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('groups:list')


class GroupMemberManageView(LoginRequiredMixin, BaseView):
    """
    Group member management view.
    
    Handles adding/removing members and role changes.
    """
    template_name = 'groups/group_members.html'
    
    def get(self, request, group_id):
        """Display member management page."""
        try:
            group = GroupService.get_group(request.user, group_id)
            
            # Check permission
            if not group.can_user_manage_members(request.user):
                messages.error(request, "You don't have permission to manage members.")
                return redirect('groups:detail', group_id=group_id)
            
            # Get group members
            members = GroupService.get_group_members(request.user, group_id)
            
            context = {
                'page_title': f'Manage Members: {group.name}',
                'group': group,
                'members': members,
                'role_choices': UserGroup.Role.choices
            }
            
            return render(request, self.template_name, context)
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('groups:list')


# AJAX Views for dynamic functionality

@login_required
def ajax_add_member(request, group_id):
    """AJAX endpoint to add member to group."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', UserGroup.Role.MEMBER)
        
        if not email:
            return JsonResponse({
                'success': False,
                'error': 'Email is required'
            }, status=400)
        
        # Add member
        member = GroupService.add_member(request.user, group_id, email, role)
        
        return JsonResponse({
            'success': True,
            'member': {
                'id': str(member.id),
                'user_name': member.user.full_name,
                'user_email': member.user.email,
                'role': member.role,
                'role_display': member.get_role_display(),
                'joined_at': member.joined_at.strftime('%Y-%m-%d %H:%M')
            }
        })
        
    except ServiceError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def ajax_remove_member(request, group_id, member_id):
    """AJAX endpoint to remove member from group."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        GroupService.remove_member(request.user, group_id, member_id)
        
        return JsonResponse({
            'success': True,
            'message': 'Member removed successfully'
        })
        
    except ServiceError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def ajax_change_role(request, group_id, member_id):
    """AJAX endpoint to change member role."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        new_role = request.POST.get('role')
        
        if not new_role or new_role not in [choice[0] for choice in UserGroup.Role.choices]:
            return JsonResponse({
                'success': False,
                'error': 'Invalid role'
            }, status=400)
        
        member = GroupService.change_member_role(request.user, group_id, member_id, new_role)
        
        return JsonResponse({
            'success': True,
            'member': {
                'id': str(member.id),
                'role': member.role,
                'role_display': member.get_role_display()
            }
        })
        
    except ServiceError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# API Views for mobile/SPA applications

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_group_list(request):
    """API endpoint to get user's groups."""
    try:
        query = request.GET.get('q', '').strip()
        role_filter = request.GET.get('role')
        
        groups = GroupService.get_user_groups(request.user, query, role_filter)
        
        # Serialize groups
        group_data = []
        for group in groups:
            user_role = group.get_user_role(request.user)
            
            group_data.append({
                'id': str(group.id),
                'name': group.name,
                'description': group.description,
                'is_personal': group.is_personal,
                'member_count': group.get_member_count(),
                'password_count': group.get_password_count(),
                'user_role': user_role,
                'is_owner': group.owner == request.user,
                'created_at': group.created_at.isoformat(),
                'updated_at': group.updated_at.isoformat()
            })
        
        return Response({
            'success': True,
            'data': group_data,
            'count': len(group_data)
        })
        
    except ServiceError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_group_detail(request, group_id):
    """API endpoint to get group details."""
    try:
        group = GroupService.get_group(request.user, group_id)
        members = GroupService.get_group_members(request.user, group_id)
        
        # Serialize members
        member_data = []
        for member in members:
            member_data.append({
                'id': str(member.id),
                'user': {
                    'id': str(member.user.id),
                    'full_name': member.user.full_name,
                    'email': member.user.email
                },
                'role': member.role,
                'role_display': member.get_role_display(),
                'joined_at': member.joined_at.isoformat(),
                'added_by': {
                    'id': str(member.added_by.id),
                    'full_name': member.added_by.full_name,
                    'email': member.added_by.email
                } if member.added_by else None
            })
        
        return Response({
            'success': True,
            'data': {
                'id': str(group.id),
                'name': group.name,
                'description': group.description,
                'is_personal': group.is_personal,
                'owner': {
                    'id': str(group.owner.id),
                    'full_name': group.owner.full_name,
                    'email': group.owner.email
                },
                'member_count': group.get_member_count(),
                'password_count': group.get_password_count(),
                'user_role': group.get_user_role(request.user),
                'can_manage_members': group.can_user_manage_members(request.user),
                'members': member_data,
                'created_at': group.created_at.isoformat(),
                'updated_at': group.updated_at.isoformat()
            }
        })
        
    except ServiceError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_group_create(request):
    """API endpoint to create new group."""
    try:
        group = GroupService.create_group(request.user, request.data)
        
        return Response({
            'success': True,
            'message': 'Group created successfully',
            'data': {
                'id': str(group.id),
                'name': group.name,
                'description': group.description
            }
        }, status=status.HTTP_201_CREATED)
        
    except CustomValidationError as e:
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': e.details
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except ServiceError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def api_group_update(request, group_id):
    """API endpoint to update group."""
    try:
        group = GroupService.update_group(request.user, group_id, request.data)
        
        return Response({
            'success': True,
            'message': 'Group updated successfully',
            'data': {
                'id': str(group.id),
                'name': group.name,
                'description': group.description,
                'updated_at': group.updated_at.isoformat()
            }
        })
        
    except CustomValidationError as e:
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': e.details
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except ServiceError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def api_group_delete(request, group_id):
    """API endpoint to delete group."""
    try:
        GroupService.delete_group(request.user, group_id)
        
        return Response({
            'success': True,
            'message': 'Group deleted successfully'
        })
        
    except ServiceError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)