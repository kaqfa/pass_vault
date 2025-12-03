"""
User models for Pass-Man Enterprise Password Management System.

This module defines the custom User model with additional fields and methods
for authentication, profile management, and security features.

Related Documentation:
- SRS.md: Section 3.1 User Management
- ARCHITECTURE.md: Database Design - User Model
- CODING_STANDARDS.md: Model Design Best Practices
"""

import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.core.models import BaseModel
from apps.users.managers import UserManager, ActiveUserManager, AllUserManager


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    
    This model includes additional fields for Pass-Man specific functionality
    including email verification, profile information, and security settings.
    """
    
    # Override default fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # We use email as username
    email = models.EmailField(
        unique=True,
        help_text="User's email address (used for login)"
    )
    
    # Profile fields
    full_name = models.CharField(
        max_length=150,
        help_text="User's full name"
    )
    
    # Email verification
    email_verified = models.BooleanField(
        default=False,
        help_text="Whether user's email has been verified"
    )
    email_verification_token = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Token for email verification"
    )
    
    # Password reset
    password_reset_token = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Token for password reset"
    )
    password_reset_expires = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When password reset token expires"
    )
    
    # Security fields
    banned = models.BooleanField(
        default=False,
        help_text="Whether user is banned from the system"
    )
    banned_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When user was banned"
    )
    banned_reason = models.TextField(
        blank=True,
        help_text="Reason for banning user"
    )
    
    # Activity tracking
    last_password_change = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When user last changed their password"
    )
    
    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    # Custom managers
    objects = UserManager()  # Default manager
    active_objects = ActiveUserManager()  # Only active users
    all_objects = AllUserManager()  # All users including banned
    
    class Meta:
        ordering = ['full_name', 'email']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['email_verified']),
            models.Index(fields=['banned']),
            models.Index(fields=['-date_joined']),
        ]
        verbose_name = "User"
        verbose_name_plural = "Users"
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    def clean(self):
        """Custom validation for User model."""
        super().clean()
        
        if not self.full_name or not self.full_name.strip():
            raise ValidationError("Full name is required")
        
        if not self.email or not self.email.strip():
            raise ValidationError("Email is required")
        
        # Clean email
        self.email = self.email.lower().strip()
    
    def save(self, *args, **kwargs):
        """Override save to perform validation and cleanup."""
        self.full_clean()
        
        # Clean fields
        if self.full_name:
            self.full_name = self.full_name.strip()
        
        # Track password changes
        if self.pk and 'password' in kwargs.get('update_fields', []):
            self.last_password_change = timezone.now()
        
        super().save(*args, **kwargs)
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.full_name.split()[0] if self.full_name else self.email
    
    def get_full_name(self):
        """Return the full name for the user."""
        return self.full_name
    
    def is_email_verified(self):
        """Check if user's email is verified."""
        return self.email_verified
    
    def is_banned(self):
        """Check if user is banned."""
        return self.banned
    
    def ban_user(self, reason="", banned_by=None):
        """Ban the user."""
        self.banned = True
        self.banned_at = timezone.now()
        self.banned_reason = reason
        self.is_active = False
        self.save(update_fields=['banned', 'banned_at', 'banned_reason', 'is_active'])
    
    def unban_user(self):
        """Unban the user."""
        self.banned = False
        self.banned_at = None
        self.banned_reason = ""
        self.is_active = True
        self.save(update_fields=['banned', 'banned_at', 'banned_reason', 'is_active'])
    
    def get_user_groups(self):
        """Get all groups where user is a member."""
        from apps.groups.models import Group
        return Group.objects.filter(usergroup__user=self).distinct()
    
    def get_owned_groups(self):
        """Get all groups owned by this user."""
        return self.owned_groups.all()
    
    def get_personal_group(self):
        """Get user's personal group."""
        return self.owned_groups.filter(is_personal=True).first()
    
    def is_group_member(self, group):
        """Check if user is a member of the given group."""
        from apps.groups.models import UserGroup
        return UserGroup.objects.filter(user=self, group=group).exists()
    
    def get_role_in_group(self, group):
        """Get user's role in the given group."""
        from apps.groups.models import UserGroup
        membership = UserGroup.objects.filter(user=self, group=group).first()
        return membership.role if membership else None
    
    def can_manage_group(self, group):
        """Check if user can manage the given group."""
        if group.owner == self:
            return True
        
        from apps.groups.models import UserGroup
        membership = UserGroup.objects.filter(user=self, group=group).first()
        return membership and membership.role == UserGroup.Role.ADMIN
    
    def get_password_count(self):
        """Get total count of passwords created by this user."""
        # TODO: Implement when Password model is created in Epic 3
        # return self.created_passwords.count()
        return 0
    
    def get_group_count(self):
        """Get total count of groups user belongs to."""
        return self.get_user_groups().count()
    
    def get_owned_group_count(self):
        """Get count of groups owned by this user."""
        return self.owned_groups.count()
    
    def has_password_reset_token(self):
        """Check if user has a valid password reset token."""
        return (
            self.password_reset_token and
            self.password_reset_expires and
            self.password_reset_expires > timezone.now()
        )
    
    def clear_password_reset_token(self):
        """Clear password reset token."""
        self.password_reset_token = None
        self.password_reset_expires = None
        self.save(update_fields=['password_reset_token', 'password_reset_expires'])
    
    def set_password_reset_token(self, token, expires_in_hours=1):
        """Set password reset token with expiration."""
        self.password_reset_token = token
        self.password_reset_expires = timezone.now() + timezone.timedelta(hours=expires_in_hours)
        self.save(update_fields=['password_reset_token', 'password_reset_expires'])
    
    def verify_email(self):
        """Mark email as verified."""
        self.email_verified = True
        self.email_verification_token = None
        self.is_active = True
        self.save(update_fields=['email_verified', 'email_verification_token', 'is_active'])
    
    def needs_email_verification(self):
        """Check if user needs email verification."""
        return not self.email_verified and not self.is_active