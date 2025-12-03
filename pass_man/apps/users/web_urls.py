"""
Web URL patterns for user authentication views.

This module defines URL routing for web-based user authentication,
registration, and profile management.

Related Documentation:
- SRS.md: Section 6.1.3 Core Endpoints
- ARCHITECTURE.md: URL Routing Design
"""

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication URLs
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    
    # Email verification
    path('verify-email/<str:uidb64>/<str:token>/', views.EmailVerificationView.as_view(), name='verify_email'),
    
    # Password reset
    path('password-reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset-confirm/<str:uidb64>/<str:token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Profile management (to be implemented in AUTH-006)
    # path('profile/', views.ProfileView.as_view(), name='profile'),
    # path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
]