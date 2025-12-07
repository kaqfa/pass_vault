"""
Core views for Pass-Man Enterprise Password Management System.

This module contains shared views and base classes used across the application.
Includes common functionality like authentication checks, HTMX handling, and error pages.

Related Documentation:
- ARCHITECTURE.md: View Layer Design
- CODING_STANDARDS.md: View Best Practices
"""

import logging
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


class BaseView(TemplateView):
    """
    Base view class with common functionality.
    
    Provides shared functionality for all views including:
    - Authentication context
    - HTMX detection
    - Common template context
    """
    
    def get_context_data(self, **kwargs):
        """Add common context data to all views."""
        context = super().get_context_data(**kwargs)
        
        # Add user context
        if self.request.user.is_authenticated:
            context['user_groups'] = self.request.user.get_user_groups()
        
        # Add HTMX context
        context['is_htmx'] = self.request.headers.get('HX-Request', False)
        
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to add logging."""
        logger.info(f"View accessed: {self.__class__.__name__} by {request.user}")
        return super().dispatch(request, *args, **kwargs)


class HomeView(BaseView):
    """
    Home page view.
    
    Displays the main landing page with features and call-to-action.
    """
    template_name = 'index.html'
    
    def get_context_data(self, **kwargs):
        """Add home page specific context."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Home'
        return context


class DashboardView(LoginRequiredMixin, BaseView):
    """
    Main dashboard view for authenticated users.
    
    Displays user's password vault, recent activity, and quick actions.
    Requires authentication to access.
    """
    template_name = 'dashboard.html'
    login_url = '/auth/login/'
    
    def get_context_data(self, **kwargs):
        """Add dashboard specific context data."""
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        # 1. Fetch User Stats
        total_passwords = user.created_passwords.filter(is_deleted=False).count()
        # TODO: Implement shared passwords count when sharing feature is ready
        shared_passwords = 0 
        groups_count = user.get_user_groups().count()
        
        # 2. Fetch Recent Passwords (last 5 accessed or updated)
        # using created_passwords as the source for now
        recent_passwords = (
            user.created_passwords
            .filter(is_deleted=False)
            .select_related('group')
            .order_by('-updated_at')[:5]
        )
        
        # 3. Fetch Recent Activity (PasswordAccessLog)
        # Ensure we import the model inside the method or at top level if possible
        # To avoid circular imports, doing lazy import if needed, but here it should be fine if imported at top
        from apps.passwords.models import PasswordAccessLog
        
        # Get logs where the user accessed a password
        recent_activity = (
            PasswordAccessLog.objects
            .filter(user=user)
            .select_related('password', 'password__group')
            .order_by('-accessed_at')[:10]
        )

        # 4. Password Health (Simple stub for now, or real calculation)
        # Real calculation:
        weak_passwords = 0
        medium_passwords = 0
        strong_passwords = 0
        # Since we can't easily decrypt all passwords to check strength efficiently in SQL,
        # we might rely on a 'strength' field if we had one, or just show total for now.
        # The Password model has 'priority', but not strength.
        # We'll just define generic stats for the UI to render if needed, or omit.
        
        context.update({
            'page_title': 'Dashboard',
            'user_stats': {
                'total_passwords': total_passwords,
                'shared_passwords': shared_passwords,
                'groups_count': groups_count,
            },
            'recent_passwords': recent_passwords,
            'recent_activity': recent_activity,
        })
        
        return context


# Health Check Endpoint
def health_check(request):
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns JSON response with system status.
    Used by Docker health checks and monitoring systems.
    """
    try:
        # Basic health checks
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': '2025-09-26T16:35:00Z'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)


# Error Handlers
def handler400(request, exception):
    """Handle 400 Bad Request errors."""
    logger.warning(f"400 error for {request.user}: {exception}")
    
    if request.headers.get('HX-Request'):
        return render(request, 'errors/400_htmx.html', status=400)
    return render(request, 'errors/400.html', status=400)


def handler403(request, exception):
    """Handle 403 Forbidden errors."""
    logger.warning(f"403 error for {request.user}: {exception}")
    
    if request.headers.get('HX-Request'):
        return render(request, 'errors/403_htmx.html', status=403)
    return render(request, 'errors/403.html', status=403)


def handler404(request, exception):
    """Handle 404 Not Found errors."""
    logger.info(f"404 error for {request.user}: {request.path}")
    
    if request.headers.get('HX-Request'):
        return render(request, 'errors/404_htmx.html', status=404)
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Handle 500 Internal Server errors."""
    logger.error(f"500 error for {request.user}: {request.path}")
    
    if request.headers.get('HX-Request'):
        return render(request, 'errors/500_htmx.html', status=500)
    return render(request, 'errors/500.html', status=500)


class APIResponseMixin:
    """
    Mixin for standardized API responses.
    
    Provides consistent JSON response formatting for API views.
    """
    
    def success_response(self, data=None, message="Success"):
        """Return standardized success response."""
        return JsonResponse({
            'success': True,
            'message': message,
            'data': data or {}
        })
    
    def error_response(self, message="Error", errors=None, status=400):
        """Return standardized error response."""
        return JsonResponse({
            'success': False,
            'message': message,
            'errors': errors or {}
        }, status=status)
    
    def validation_error_response(self, form):
        """Return validation error response from form."""
        return self.error_response(
            message="Validation failed",
            errors=form.errors,
            status=400
        )