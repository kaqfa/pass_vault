"""
Web views for the users app.

This module contains HTMX-based web views for authentication
and user management. These views will be implemented in future sprints.

Related Documentation:
- ARCHITECTURE.md: Frontend Architecture
- DEVELOPER_GUIDE.md: HTMX Development
- BACKLOG.md: AUTH-001 to AUTH-007 tasks
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, FormView
from django.contrib import messages
from apps.core.views import BaseView


class LoginView(TemplateView):
    """
    Login view with HTMX support.
    
    Implementation: AUTH-002 task
    """
    template_name = 'auth/login.html'
    
    def get(self, request):
        """Display login form."""
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        
        # TODO: Implement in AUTH-002
        context = {
            'message': 'Login view - to be implemented in AUTH-002'
        }
        return render(request, self.template_name, context)


class LogoutView(LoginRequiredMixin, TemplateView):
    """
    Logout view.
    
    Implementation: AUTH-002 task
    """
    
    def post(self, request):
        """Handle logout."""
        # TODO: Implement in AUTH-002
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('users_web:login')


class RegisterView(TemplateView):
    """
    User registration view with email verification.
    
    Implementation: AUTH-001 task
    """
    template_name = 'auth/register.html'
    
    def get(self, request):
        """Display registration form."""
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        
        # TODO: Implement in AUTH-001
        context = {
            'message': 'Registration view - to be implemented in AUTH-001'
        }
        return render(request, self.template_name, context)


class EmailVerificationView(TemplateView):
    """
    Email verification view.
    
    Implementation: AUTH-001 task
    """
    template_name = 'auth/email_verification.html'
    
    def get(self, request, token):
        """Handle email verification."""
        # TODO: Implement in AUTH-001
        context = {
            'message': f'Email verification view - to be implemented in AUTH-001 (token: {token})'
        }
        return render(request, self.template_name, context)


class PasswordResetView(TemplateView):
    """
    Password reset request view.
    
    Implementation: AUTH-004 task
    """
    template_name = 'auth/password_reset.html'
    
    def get(self, request):
        """Display password reset form."""
        # TODO: Implement in AUTH-004
        context = {
            'message': 'Password reset view - to be implemented in AUTH-004'
        }
        return render(request, self.template_name, context)


class PasswordResetConfirmView(TemplateView):
    """
    Password reset confirmation view.
    
    Implementation: AUTH-004 task
    """
    template_name = 'auth/password_reset_confirm.html'
    
    def get(self, request, token):
        """Display password reset confirmation form."""
        # TODO: Implement in AUTH-004
        context = {
            'message': f'Password reset confirm view - to be implemented in AUTH-004 (token: {token})'
        }
        return render(request, self.template_name, context)


class ProfileView(BaseView):
    """
    User profile view.
    
    Implementation: AUTH-006 task
    """
    template_name = 'users/profile.html'
    htmx_template_name = 'users/partials/profile_content.html'
    
    def get_context_data(self, **kwargs):
        """Add profile context data."""
        context = super().get_context_data(**kwargs)
        
        # TODO: Implement in AUTH-006
        context.update({
            'message': 'Profile view - to be implemented in AUTH-006'
        })
        
        return context


class ProfileEditView(BaseView):
    """
    User profile edit view.
    
    Implementation: AUTH-006 task
    """
    template_name = 'users/profile_edit.html'
    htmx_template_name = 'users/partials/profile_edit_form.html'
    
    def get_context_data(self, **kwargs):
        """Add profile edit context data."""
        context = super().get_context_data(**kwargs)
        
        # TODO: Implement in AUTH-006
        context.update({
            'message': 'Profile edit view - to be implemented in AUTH-006'
        })
        
        return context


class ChangePasswordView(BaseView):
    """
    Change password view.
    
    Implementation: AUTH-006 task
    """
    template_name = 'users/change_password.html'
    htmx_template_name = 'users/partials/change_password_form.html'
    
    def get_context_data(self, **kwargs):
        """Add change password context data."""
        context = super().get_context_data(**kwargs)
        
        # TODO: Implement in AUTH-006
        context.update({
            'message': 'Change password view - to be implemented in AUTH-006'
        })
        
        return context