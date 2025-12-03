"""
User services for Pass-Man Enterprise Password Management System.

This module contains business logic for user management including registration,
authentication, profile management, and password reset functionality.

Related Documentation:
- SRS.md: Section 3.1 User Management
- ARCHITECTURE.md: Service Layer Pattern
- CODING_STANDARDS.md: Service Layer Best Practices
"""

import uuid
import secrets
import hashlib
from datetime import timedelta
from typing import Dict, Tuple, Optional
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.db import transaction

from apps.core.exceptions import ServiceError, ValidationError
from apps.users.models import User
from apps.users.validators import (
    UserRegistrationValidator,
    PasswordValidator,
    ProfileUpdateValidator
)
from apps.groups.services import GroupService

import logging

logger = logging.getLogger(__name__)


class UserRegistrationService:
    """Service for user registration and email verification."""
    
    @staticmethod
    @transaction.atomic
    def register_user(registration_data: Dict) -> Tuple[User, Optional[str]]:
        """
        Register a new user with email verification.
        
        Args:
            registration_data (Dict): User registration data
            
        Returns:
            Tuple[User, Optional[str]]: Created user and verification token
            
        Raises:
            ValidationError: If registration data is invalid
            ServiceError: If registration fails
        """
        try:
            # Validate registration data
            validator = UserRegistrationValidator(registration_data)
            if not validator.is_valid():
                raise ValidationError(validator.errors)
            
            # Check if user already exists
            email = registration_data['email'].lower().strip()
            if User.objects.filter(email=email).exists():
                raise ValidationError({'email': 'User with this email already exists'})
            
            # Create user (inactive by default until email verification)
            user = User.objects.create_user(
                email=email,
                full_name=registration_data['full_name'].strip(),
                password=registration_data['password'],
                is_active=True,  # Skip email verification for development
                email_verified=True  # Mark as verified for development
            )
            
            # Create personal group for the user
            try:
                GroupService.create_default_personal_group(user)
                logger.info(f"Personal group created for user: {user.email}")
            except Exception as e:
                logger.warning(f"Failed to create personal group for {user.email}: {e}")
                # Don't fail registration if group creation fails
            
            # Skip email verification for development
            verification_token = None
            logger.info(f"User registered successfully (development mode): {user.email}")
            
            return user, verification_token
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"User registration failed: {str(e)}")
            raise ServiceError(f"Registration failed: {str(e)}")
    
    @staticmethod
    def _generate_verification_token() -> str:
        """Generate a secure verification token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def _send_verification_email(user: User, token: str) -> bool:
        """
        Send email verification email to user.
        
        Args:
            user (User): User to send email to
            token (str): Verification token
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Generate verification URL
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            verification_url = f"{settings.FRONTEND_URL}/auth/verify-email/{uidb64}/{token}/"
            
            # Render email templates
            context = {
                'user': user,
                'verification_url': verification_url,
                'expires_hours': 24
            }
            
            html_message = render_to_string('emails/verify_email.html', context)
            text_message = render_to_string('emails/verify_email.txt', context)
            
            # Send email
            send_mail(
                subject='Verify Your Pass-Man Account',
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Verification email sent to: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def verify_email(user_id: str, token: str) -> bool:
        """
        Verify user's email with token.
        
        Args:
            user_id (str): User ID
            token (str): Verification token
            
        Returns:
            bool: True if verification successful
            
        Raises:
            ServiceError: If verification fails
        """
        try:
            user = User.objects.get(id=user_id)
            
            # Check if already verified
            if user.email_verified:
                return True
            
            # Verify token
            if user.email_verification_token != token:
                raise ServiceError("Invalid verification token")
            
            # Activate user
            user.verify_email()
            
            # Create personal group if not exists
            try:
                GroupService.create_default_personal_group(user)
            except Exception as e:
                logger.warning(f"Failed to create personal group during verification for {user.email}: {e}")
            
            logger.info(f"Email verified successfully for user: {user.email}")
            return True
            
        except User.DoesNotExist:
            raise ServiceError("User not found")
        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            raise ServiceError(f"Verification failed: {str(e)}")
    
    @staticmethod
    def resend_verification_email(email: str) -> bool:
        """
        Resend verification email to user.
        
        Args:
            email (str): User's email address
            
        Returns:
            bool: True if email sent (or user already verified)
            
        Raises:
            ServiceError: If operation fails
        """
        try:
            user = User.objects.get(email=email.lower().strip())
            
            # Check if already verified
            if user.email_verified:
                return True
            
            # Generate new token
            token = UserRegistrationService._generate_verification_token()
            user.email_verification_token = token
            user.save(update_fields=['email_verification_token'])
            
            # Send email
            return UserRegistrationService._send_verification_email(user, token)
            
        except User.DoesNotExist:
            # Don't reveal if user exists for security
            logger.info(f"Resend verification attempted for non-existent email: {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to resend verification email: {str(e)}")
            raise ServiceError(f"Failed to resend verification email: {str(e)}")


class UserAuthenticationService:
    """Service for user authentication and session management."""
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.
        
        Args:
            email (str): User's email
            password (str): User's password
            
        Returns:
            Optional[User]: Authenticated user or None
            
        Raises:
            ServiceError: If authentication fails
        """
        try:
            # Normalize email
            email = email.lower().strip()
            
            # Check if user exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise ServiceError("Invalid email or password")
            
            # Check if user is banned
            if user.is_banned():
                raise ServiceError("Your account has been suspended. Please contact support.")
            
            # Skip email verification check for development
            # if not user.email_verified:
            #     raise ServiceError("Please verify your email address before logging in")
            
            # Authenticate user
            authenticated_user = authenticate(email=email, password=password)
            if not authenticated_user:
                raise ServiceError("Invalid email or password")
            
            # Update last login
            authenticated_user.last_login = timezone.now()
            authenticated_user.save(update_fields=['last_login'])
            
            logger.info(f"User authenticated successfully: {email}")
            return authenticated_user
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"Authentication failed for {email}: {str(e)}")
            raise ServiceError("Authentication failed")


class UserProfileService:
    """Service for user profile management."""
    
    @staticmethod
    def update_profile(user: User, profile_data: Dict) -> User:
        """
        Update user profile information.
        
        Args:
            user (User): User to update
            profile_data (Dict): Profile data to update
            
        Returns:
            User: Updated user
            
        Raises:
            ValidationError: If profile data is invalid
            ServiceError: If update fails
        """
        try:
            # Validate profile data
            validator = ProfileUpdateValidator(profile_data, user)
            if not validator.is_valid():
                raise ValidationError(validator.errors)
            
            # Update user fields
            if 'full_name' in profile_data:
                user.full_name = profile_data['full_name'].strip()
            
            if 'email' in profile_data:
                new_email = profile_data['email'].lower().strip()
                if new_email != user.email:
                    # If email changed, require re-verification
                    user.email = new_email
                    user.email_verified = True  # Skip verification for development
                    user.email_verification_token = None
            
            user.save()
            
            logger.info(f"Profile updated for user: {user.email}")
            return user
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Profile update failed for {user.email}: {str(e)}")
            raise ServiceError(f"Profile update failed: {str(e)}")
    
    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> bool:
        """
        Change user's password.
        
        Args:
            user (User): User to change password for
            current_password (str): Current password
            new_password (str): New password
            
        Returns:
            bool: True if password changed successfully
            
        Raises:
            ValidationError: If password data is invalid
            ServiceError: If password change fails
        """
        try:
            # Verify current password
            if not user.check_password(current_password):
                raise ValidationError({'current_password': 'Current password is incorrect'})
            
            # Validate new password
            validator = PasswordValidator({'password': new_password})
            if not validator.is_valid():
                raise ValidationError(validator.errors)
            
            # Change password
            user.set_password(new_password)
            user.last_password_change = timezone.now()
            user.save(update_fields=['password', 'last_password_change'])
            
            logger.info(f"Password changed for user: {user.email}")
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Password change failed for {user.email}: {str(e)}")
            raise ServiceError(f"Password change failed: {str(e)}")


class UserPasswordResetService:
    """Service for password reset functionality."""
    
    @staticmethod
    def initiate_password_reset(email: str) -> bool:
        """
        Initiate password reset process.
        
        Args:
            email (str): User's email address
            
        Returns:
            bool: True if reset initiated (always returns True for security)
        """
        try:
            user = User.objects.get(email=email.lower().strip())
            
            # Generate reset token
            token = secrets.token_urlsafe(32)
            user.set_password_reset_token(token, expires_in_hours=1)
            
            # Send reset email
            UserPasswordResetService._send_password_reset_email(user, token)
            
            logger.info(f"Password reset initiated for: {email}")
            
        except User.DoesNotExist:
            # Don't reveal if user exists for security
            logger.info(f"Password reset attempted for non-existent email: {email}")
        except Exception as e:
            logger.error(f"Password reset initiation failed: {str(e)}")
        
        # Always return True for security (don't reveal if user exists)
        return True
    
    @staticmethod
    def _send_password_reset_email(user: User, token: str) -> bool:
        """
        Send password reset email to user.
        
        Args:
            user (User): User to send email to
            token (str): Reset token
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Generate reset URL
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = f"{settings.FRONTEND_URL}/auth/password-reset-confirm/{uidb64}/{token}/"
            
            # Render email templates
            context = {
                'user': user,
                'reset_url': reset_url,
                'expires_hours': 1
            }
            
            html_message = render_to_string('emails/password_reset.html', context)
            text_message = render_to_string('emails/password_reset.txt', context)
            
            # Send email
            send_mail(
                subject='Reset Your Pass-Man Password',
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Password reset email sent to: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def reset_password(user_id: str, token: str, new_password: str) -> bool:
        """
        Reset user's password with token.
        
        Args:
            user_id (str): User ID
            token (str): Reset token
            new_password (str): New password
            
        Returns:
            bool: True if password reset successfully
            
        Raises:
            ValidationError: If password is invalid
            ServiceError: If reset fails
        """
        try:
            user = User.objects.get(id=user_id)
            
            # Verify token
            if not user.has_password_reset_token() or user.password_reset_token != token:
                raise ServiceError("Invalid or expired reset token")
            
            # Validate new password
            validator = PasswordValidator({'password': new_password})
            if not validator.is_valid():
                raise ValidationError(validator.errors)
            
            # Reset password
            user.set_password(new_password)
            user.last_password_change = timezone.now()
            user.clear_password_reset_token()
            user.save(update_fields=['password', 'last_password_change'])
            
            logger.info(f"Password reset successfully for user: {user.email}")
            return True
            
        except User.DoesNotExist:
            raise ServiceError("User not found")
        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Password reset failed: {str(e)}")
            raise ServiceError(f"Password reset failed: {str(e)}")