"""
Password views for Pass-Man Enterprise Password Management System.

This module contains views for password management including creation, viewing,
editing, deletion, and search functionality.

Related Documentation:
- SRS.md: Section 4.1 Password Management
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
from django.db.models import Q

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.views import BaseView
from apps.core.exceptions import ServiceError, ValidationError as CustomValidationError
from apps.passwords.services import PasswordService, PasswordGeneratorService
from apps.passwords.models import Password, PasswordHistory
from apps.groups.models import Group

logger = logging.getLogger(__name__)


class PasswordListView(LoginRequiredMixin, BaseView):
    """
    Password list view with search and filtering.
    
    Displays user's accessible passwords with search and filter capabilities.
    """
    template_name = 'passwords/password_list.html'
    
    def get(self, request):
        """Display password list with search and filters."""
        try:
            # Get search parameters
            query = request.GET.get('q', '').strip()
            group_id = request.GET.get('group')
            priority = request.GET.get('priority')
            is_favorite = request.GET.get('favorite')
            
            # Build filters
            filters = {}
            if group_id:
                filters['group_id'] = group_id
            if priority:
                filters['priority'] = priority
            if is_favorite:
                filters['is_favorite'] = is_favorite == 'true'
            
            # Get passwords
            if query or filters:
                passwords = PasswordService.search_passwords(request.user, query, filters)
            else:
                passwords = PasswordService.get_user_passwords(request.user)
            
            # Pagination
            paginator = Paginator(passwords, 20)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            # Get user's groups for filter dropdown
            user_groups = Group.objects.filter(
                Q(owner=request.user) | Q(usergroup__user=request.user)
            ).distinct()
            
            context = {
                'page_title': 'My Passwords',
                'passwords': page_obj,
                'user_groups': user_groups,
                'search_query': query,
                'current_filters': {
                    'group': group_id,
                    'priority': priority,
                    'favorite': is_favorite
                },
                'priority_choices': Password.Priority.choices,
                'total_count': len(passwords)
            }
            
            return render(request, self.template_name, context)
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('core:dashboard')


class PasswordDetailView(LoginRequiredMixin, BaseView):
    """
    Password detail view with decryption.
    
    Shows password details and allows viewing decrypted password.
    """
    template_name = 'passwords/password_detail.html'
    
    def get(self, request, password_id):
        """Display password details."""
        try:
            password = PasswordService.get_password(
                request.user, 
                password_id, 
                record_access=True
            )
            
            # Get password history
            history = PasswordHistory.objects.filter(
                password=password
            ).select_related('changed_by').order_by('-created_at')[:10]
            
            context = {
                'page_title': f'Password: {password.title}',
                'password': password,
                'history': history,
                'can_edit': PasswordService._can_user_edit_password(request.user, password),
                'can_delete': PasswordService._can_user_delete_password(request.user, password)
            }
            
            return render(request, self.template_name, context)
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('passwords:list')


class PasswordCreateView(LoginRequiredMixin, BaseView):
    """
    Password creation view.
    
    Handles password creation with encryption and validation.
    """
    template_name = 'passwords/password_form.html'
    
    def get(self, request):
        """Display password creation form."""
        # Get user's groups
        user_groups = Group.objects.filter(
            Q(owner=request.user) | Q(usergroup__user=request.user)
        ).distinct()
        
        if not user_groups.exists():
            messages.error(request, 'You need to be a member of at least one group to create passwords.')
            return redirect('core:dashboard')
        
        context = {
            'page_title': 'Add New Password',
            'user_groups': user_groups,
            'priority_choices': Password.Priority.choices,
            'is_create': True
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle password creation."""
        try:
            # Get form data
            password_data = {
                'title': request.POST.get('title', '').strip(),
                'username': request.POST.get('username', '').strip(),
                'password': request.POST.get('password', ''),
                'url': request.POST.get('url', '').strip(),
                'notes': request.POST.get('notes', '').strip(),
                'group_id': request.POST.get('group_id'),
                'priority': request.POST.get('priority', Password.Priority.MEDIUM),
                'custom_fields': self._parse_custom_fields(request.POST.get('custom_fields', '{}')),
                'tags': self._parse_tags(request.POST.get('tags', ''))
            }
            
            # Create password
            password = PasswordService.create_password(request.user, password_data)
            
            messages.success(
                request,
                f'Password "{password.title}" created successfully!'
            )
            
            return redirect('passwords:detail', password_id=password.id)
            
        except CustomValidationError as e:
            # Get user's groups for form
            user_groups = Group.objects.filter(
                Q(owner=request.user) | Q(usergroup__user=request.user)
            ).distinct()
            
            context = {
                'page_title': 'Add New Password',
                'user_groups': user_groups,
                'priority_choices': Password.Priority.choices,
                'is_create': True,
                'errors': e.details,
                'form_data': password_data
            }
            
            return render(request, self.template_name, context)
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('passwords:create')
    
    def _parse_custom_fields(self, custom_fields_str):
        """Parse custom fields JSON string."""
        try:
            if custom_fields_str:
                return json.loads(custom_fields_str)
            return {}
        except json.JSONDecodeError:
            return {}
    
    def _parse_tags(self, tags_str):
        """Parse tags string into list."""
        if not tags_str:
            return []
        
        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        return tags


class PasswordEditView(LoginRequiredMixin, BaseView):
    """
    Password edit view.
    
    Handles password updates with version history.
    """
    template_name = 'passwords/password_form.html'
    
    def get(self, request, password_id):
        """Display password edit form."""
        try:
            password = PasswordService.get_password(
                request.user, 
                password_id, 
                record_access=False
            )
            
            # Check edit permission
            if not PasswordService._can_user_edit_password(request.user, password):
                messages.error(request, "You don't have permission to edit this password.")
                return redirect('passwords:detail', password_id=password_id)
            
            # Get user's groups
            user_groups = Group.objects.filter(
                Q(owner=request.user) | Q(usergroup__user=request.user)
            ).distinct()
            
            context = {
                'page_title': f'Edit Password: {password.title}',
                'password': password,
                'user_groups': user_groups,
                'priority_choices': Password.Priority.choices,
                'is_create': False,
                'tags_str': ', '.join(password.tags) if password.tags else '',
                'custom_fields_str': json.dumps(password.custom_fields) if password.custom_fields else '{}'
            }
            
            return render(request, self.template_name, context)
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('passwords:list')
    
    def post(self, request, password_id):
        """Handle password update."""
        try:
            # Get form data
            password_data = {
                'title': request.POST.get('title', '').strip(),
                'username': request.POST.get('username', '').strip(),
                'url': request.POST.get('url', '').strip(),
                'notes': request.POST.get('notes', '').strip(),
                'priority': request.POST.get('priority', Password.Priority.MEDIUM),
                'custom_fields': self._parse_custom_fields(request.POST.get('custom_fields', '{}')),
                'tags': self._parse_tags(request.POST.get('tags', ''))
            }
            
            # Include password if provided
            new_password = request.POST.get('password', '').strip()
            if new_password:
                password_data['password'] = new_password
            
            # Update password
            password = PasswordService.update_password(request.user, password_id, password_data)
            
            messages.success(
                request,
                f'Password "{password.title}" updated successfully!'
            )
            
            return redirect('passwords:detail', password_id=password.id)
            
        except CustomValidationError as e:
            try:
                password = PasswordService.get_password(
                    request.user, 
                    password_id, 
                    record_access=False
                )
                
                user_groups = Group.objects.filter(
                    Q(owner=request.user) | Q(usergroup__user=request.user)
                ).distinct()
                
                context = {
                    'page_title': f'Edit Password: {password.title}',
                    'password': password,
                    'user_groups': user_groups,
                    'priority_choices': Password.Priority.choices,
                    'is_create': False,
                    'errors': e.details,
                    'form_data': password_data
                }
                
                return render(request, self.template_name, context)
                
            except ServiceError:
                messages.error(request, "Password not found.")
                return redirect('passwords:list')
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('passwords:detail', password_id=password_id)
    
    def _parse_custom_fields(self, custom_fields_str):
        """Parse custom fields JSON string."""
        try:
            if custom_fields_str:
                return json.loads(custom_fields_str)
            return {}
        except json.JSONDecodeError:
            return {}
    
    def _parse_tags(self, tags_str):
        """Parse tags string into list."""
        if not tags_str:
            return []
        
        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        return tags


class PasswordDeleteView(LoginRequiredMixin, View):
    """
    Password deletion view.
    
    Handles soft deletion of passwords.
    """
    
    def post(self, request, password_id):
        """Handle password deletion."""
        try:
            password = PasswordService.get_password(
                request.user, 
                password_id, 
                record_access=False
            )
            
            title = password.title
            
            # Delete password
            PasswordService.delete_password(request.user, password_id)
            
            messages.success(
                request,
                f'Password "{title}" deleted successfully!'
            )
            
            return redirect('passwords:list')
            
        except ServiceError as e:
            messages.error(request, str(e))
            return redirect('passwords:list')


# AJAX Views for dynamic functionality

@login_required
def ajax_reveal_password(request, password_id):
    """AJAX endpoint to reveal decrypted password."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        password = PasswordService.get_password(
            request.user, 
            password_id, 
            record_access=True
        )
        
        # Decrypt password
        decrypted_password = password.get_password()
        
        return JsonResponse({
            'success': True,
            'password': decrypted_password
        })
        
    except ServiceError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def ajax_toggle_favorite(request, password_id):
    """AJAX endpoint to toggle password favorite status."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        password = PasswordService.get_password(
            request.user, 
            password_id, 
            record_access=False
        )
        
        # Toggle favorite
        password.toggle_favorite()
        
        return JsonResponse({
            'success': True,
            'is_favorite': password.is_favorite
        })
        
    except ServiceError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def ajax_generate_password(request):
    """AJAX endpoint to generate secure password."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get generation parameters
        length = int(request.POST.get('length', 16))
        include_uppercase = request.POST.get('include_uppercase') == 'true'
        include_lowercase = request.POST.get('include_lowercase') == 'true'
        include_numbers = request.POST.get('include_numbers') == 'true'
        include_symbols = request.POST.get('include_symbols') == 'true'
        exclude_ambiguous = request.POST.get('exclude_ambiguous') == 'true'
        
        # Generate password
        generated_password = PasswordGeneratorService.generate_password(
            length=length,
            include_uppercase=include_uppercase,
            include_lowercase=include_lowercase,
            include_numbers=include_numbers,
            include_symbols=include_symbols,
            exclude_ambiguous=exclude_ambiguous
        )
        
        # Check strength
        strength_analysis = PasswordGeneratorService.check_password_strength(generated_password)
        
        return JsonResponse({
            'success': True,
            'password': generated_password,
            'strength': strength_analysis
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# API Views for mobile/SPA applications

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_password_list(request):
    """API endpoint to get user's passwords."""
    try:
        # Get query parameters
        group_id = request.GET.get('group_id')
        query = request.GET.get('q', '').strip()
        
        # Get passwords
        if query:
            passwords = PasswordService.search_passwords(request.user, query)
        else:
            passwords = PasswordService.get_user_passwords(request.user, group_id)
        
        # Serialize passwords (without decrypted password)
        password_data = []
        for password in passwords:
            password_data.append({
                'id': str(password.id),
                'title': password.title,
                'username': password.username,
                'url': password.url,
                'notes': password.notes,
                'priority': password.priority,
                'is_favorite': password.is_favorite,
                'tags': password.tags,
                'custom_fields': password.custom_fields,
                'group': {
                    'id': str(password.group.id),
                    'name': password.group.name
                },
                'created_at': password.created_at.isoformat(),
                'updated_at': password.updated_at.isoformat(),
                'last_accessed': password.last_accessed.isoformat() if password.last_accessed else None,
                'access_count': password.access_count
            })
        
        return Response({
            'success': True,
            'data': password_data,
            'count': len(password_data)
        })
        
    except ServiceError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_password_detail(request, password_id):
    """API endpoint to get password details with decryption."""
    try:
        password = PasswordService.get_password(
            request.user, 
            password_id, 
            record_access=True
        )
        
        # Decrypt password
        decrypted_password = password.get_password()
        
        return Response({
            'success': True,
            'data': {
                'id': str(password.id),
                'title': password.title,
                'username': password.username,
                'password': decrypted_password,
                'url': password.url,
                'notes': password.notes,
                'priority': password.priority,
                'is_favorite': password.is_favorite,
                'tags': password.tags,
                'custom_fields': password.custom_fields,
                'group': {
                    'id': str(password.group.id),
                    'name': password.group.name
                },
                'created_at': password.created_at.isoformat(),
                'updated_at': password.updated_at.isoformat(),
                'last_accessed': password.last_accessed.isoformat() if password.last_accessed else None,
                'access_count': password.access_count,
                'expires_at': password.expires_at.isoformat() if password.expires_at else None
            }
        })
        
    except ServiceError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_password_create(request):
    """API endpoint to create new password."""
    try:
        password = PasswordService.create_password(request.user, request.data)
        
        return Response({
            'success': True,
            'message': 'Password created successfully',
            'data': {
                'id': str(password.id),
                'title': password.title,
                'group': password.group.name
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
def api_password_update(request, password_id):
    """API endpoint to update password."""
    try:
        password = PasswordService.update_password(request.user, password_id, request.data)
        
        return Response({
            'success': True,
            'message': 'Password updated successfully',
            'data': {
                'id': str(password.id),
                'title': password.title,
                'updated_at': password.updated_at.isoformat()
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
def api_password_delete(request, password_id):
    """API endpoint to delete password."""
    try:
        PasswordService.delete_password(request.user, password_id)
        
        return Response({
            'success': True,
            'message': 'Password deleted successfully'
        })
        
    except ServiceError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)