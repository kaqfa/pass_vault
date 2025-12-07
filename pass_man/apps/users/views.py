"""
User views for Pass-Man Enterprise Password Management System.

This module contains views for user authentication, registration, and profile management
using both web interface and API endpoints.

Related Documentation:
- SRS.md: Section 3.1 User Management
- ARCHITECTURE.md: View Layer Design
- CODING_STANDARDS.md: View Best Practices
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView, FormView, View
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.views import BaseView, APIResponseMixin
from apps.core.exceptions import ServiceError, ValidationError as CustomValidationError
from apps.users.services import (
    UserRegistrationService, 
    UserAuthenticationService,
    UserProfileService,
    UserPasswordResetService
)
from apps.users.models import User

logger = logging.getLogger(__name__)


class UserRegistrationView(BaseView):
    """
    User registration view with email verification.
    
    Handles user registration process including form validation,
    account creation, and email verification sending.
    """
    template_name = 'auth/register.html'
    
    def get(self, request):
        """Display registration form."""
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        
        context = {
            'page_title': 'Create Account',
            'show_login_link': True
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle registration form submission."""
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        
        # Get form data
        registration_data = {
            'email': request.POST.get('email', '').strip().lower(),
            'full_name': request.POST.get('full_name', '').strip(),
            'password': request.POST.get('password', ''),
            'confirm_password': request.POST.get('confirm_password', '')
        }
        
        try:
            # Register user using service
            user, verification_token = UserRegistrationService.register_user(registration_data)
            
            messages.success(
                request,
                f'Account created successfully! You can now sign in with your credentials.'
            )
            
            # Redirect to login page with success message
            return redirect('users:login')
            
        except CustomValidationError as e:
            # Add service validation errors to context
            context = {
                'page_title': 'Create Account',
                'show_login_link': True,
                'errors': e.details,
                'form_data': registration_data
            }
            return render(request, self.template_name, context)
                    
        except ServiceError as e:
            messages.error(request, str(e))
            logger.error(f"Registration service error: {e}")
            
            context = {
                'page_title': 'Create Account',
                'show_login_link': True,
                'form_data': registration_data
            }
            return render(request, self.template_name, context)


class UserLoginView(BaseView):
    """
    User login view with authentication.
    
    Handles user login process including form validation,
    authentication, and session management.
    """
    template_name = 'auth/login.html'
    
    def get(self, request):
        """Display login form."""
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        
        context = {
            'page_title': 'Sign In',
            'show_register_link': True
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle login form submission."""
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        try:
            # Authenticate user using service
            user = UserAuthenticationService.authenticate_user(email, password)
            
            if user:
                # Log user in
                login(request, user)
                
                messages.success(
                    request,
                    f'Welcome back, {user.get_short_name()}!'
                )
                
                # Redirect to next URL or dashboard
                next_url = request.GET.get('next', reverse('core:dashboard'))
                return redirect(next_url)
            
        except ServiceError as e:
            messages.error(request, str(e))
            logger.warning(f"Login attempt failed: {e}")
        
        context = {
            'page_title': 'Sign In',
            'show_register_link': True,
            'form_data': {'email': email}
        }
        return render(request, self.template_name, context)


class UserLogoutView(LoginRequiredMixin, View):
    """User logout view."""
    
    def post(self, request):
        """Handle logout."""
        user_name = request.user.get_short_name()
        logout(request)
        
        messages.success(request, f'You have been logged out successfully. Goodbye, {user_name}!')
        return redirect('core:home')
    
    def get(self, request):
        """Handle logout via GET request."""
        return self.post(request)


class EmailVerificationView(BaseView):
    """
    Email verification view.
    
    Handles email verification process using tokens sent via email.
    """
    template_name = 'auth/email_verification.html'
    
    def get(self, request, uidb64, token):
        """Handle email verification."""
        try:
            # Decode user ID
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            
            # Verify token and activate user
            if UserRegistrationService.verify_email(str(user.id), token):
                messages.success(
                    request,
                    'Your email has been verified successfully! You can now log in to your account.'
                )
                
                context = {
                    'success': True,
                    'user': user,
                    'page_title': 'Email Verified'
                }
            else:
                messages.error(
                    request,
                    'The verification link is invalid or has expired. Please request a new verification email.'
                )
                
                context = {
                    'success': False,
                    'page_title': 'Verification Failed'
                }
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, ServiceError) as e:
            logger.warning(f"Email verification failed: {e}")
            messages.error(
                request,
                'The verification link is invalid. Please check your email or request a new verification link.'
            )
            
            context = {
                'success': False,
                'page_title': 'Verification Failed'
            }
        
        return render(request, self.template_name, context)


class PasswordResetView(BaseView):
    """
    Password reset request view.
    
    Handles password reset requests and sends reset emails.
    """
    template_name = 'auth/password_reset.html'
    
    def get(self, request):
        """Display password reset form."""
        context = {
            'page_title': 'Reset Password'
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle password reset request."""
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            context = {
                'page_title': 'Reset Password',
                'errors': {'email': 'Email address is required'},
                'form_data': {'email': email}
            }
            return render(request, self.template_name, context)
        
        # Always show success message for security
        UserPasswordResetService.initiate_password_reset(email)
        
        messages.success(
            request,
            f'If an account exists for {email}, '
            f'password reset instructions have been sent to your email.'
        )
        
        return redirect('users:login')


class PasswordResetConfirmView(BaseView):
    """
    Password reset confirmation view.
    
    Handles password reset confirmation using tokens sent via email.
    """
    template_name = 'auth/password_reset_confirm.html'
    
    def get(self, request, uidb64, token):
        """Display password reset confirmation form."""
        try:
            # Decode user ID
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            
            # Check if token is valid
            if user.has_password_reset_token() and user.password_reset_token == token:
                # Store user ID and token in session for POST request
                request.session['reset_user_id'] = str(user.id)
                request.session['reset_token'] = token
                
                context = {
                    'valid_link': True,
                    'page_title': 'Set New Password'
                }
            else:
                context = {
                    'valid_link': False,
                    'page_title': 'Invalid Reset Link'
                }
            
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            context = {
                'valid_link': False,
                'page_title': 'Invalid Reset Link'
            }
        
        return render(request, self.template_name, context)
    
    def post(self, request, uidb64, token):
        """Handle password reset confirmation."""
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Basic validation
        if not new_password or not confirm_password:
            context = {
                'valid_link': True,
                'page_title': 'Set New Password',
                'errors': {'new_password': 'Password is required'}
            }
            return render(request, self.template_name, context)
        
        if new_password != confirm_password:
            context = {
                'valid_link': True,
                'page_title': 'Set New Password',
                'errors': {'confirm_password': 'Passwords do not match'}
            }
            return render(request, self.template_name, context)
        
        try:
            user_id = request.session.get('reset_user_id')
            session_token = request.session.get('reset_token')
            
            if not user_id or not session_token or session_token != token:
                raise ServiceError("Invalid reset session")
            
            # Reset password using service
            if UserPasswordResetService.reset_password(user_id, session_token, new_password):
                # Clear session data
                request.session.pop('reset_user_id', None)
                request.session.pop('reset_token', None)
                
                messages.success(
                    request,
                    'Your password has been reset successfully! You can now log in with your new password.'
                )
                
                return redirect('users:login')
            
        except (ServiceError, CustomValidationError) as e:
            if isinstance(e, CustomValidationError):
                context = {
                    'valid_link': True,
                    'page_title': 'Set New Password',
                    'errors': e.details
                }
            else:
                context = {
                    'valid_link': False,
                    'page_title': 'Invalid Reset Link'
                }
            return render(request, self.template_name, context)
        
        context = {
            'valid_link': True,
            'page_title': 'Set New Password'
        }
        return render(request, self.template_name, context)


# API Views for JWT Authentication
@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    """API endpoint for user registration."""
    try:
        # Register user using service
        user, verification_token = UserRegistrationService.register_user(request.data)
        
        return Response({
            'success': True,
            'message': 'Account created successfully! You can now log in with your credentials.',
            'data': {
                'user_id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
                'email_verified': user.email_verified
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


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """API endpoint for user login with JWT tokens."""
    try:
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'success': False,
                'message': 'Email and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Authenticate user using service
        user = UserAuthenticationService.authenticate_user(email, password)
        
        if user:
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'data': {
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'full_name': user.full_name,
                        'email_verified': user.email_verified
                    },
                    'tokens': {
                        'access': str(access_token),
                        'refresh': str(refresh)
                    }
                }
            })
        
    except ServiceError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_profile(request):
    """API endpoint to get user profile."""
    user = request.user
    
    return Response({
        'success': True,
        'data': {
            'id': str(user.id),
            'email': user.email,
            'full_name': user.full_name,
            'email_verified': user.email_verified,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'group_count': user.get_group_count(),
            'password_count': user.get_password_count()
        }
    })