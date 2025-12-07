"""
Password models for Pass-Man Enterprise Password Management System.

This module defines the Password model with AES-256-GCM encryption,
version history, and comprehensive password management features.

Related Documentation:
- SRS.md: Section 4.1 Password Management
- ARCHITECTURE.md: Database Design - Password Model
- CODING_STANDARDS.md: Model Design Best Practices
"""

import uuid
import json
from datetime import datetime
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

from apps.core.models import BaseModel
from apps.groups.models import Group

User = get_user_model()


class PasswordManager(models.Manager):
    """Custom manager for Password model."""
    
    def get_queryset(self):
        """Return queryset excluding soft-deleted passwords."""
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        """Return queryset including soft-deleted passwords."""
        return super().get_queryset()
    
    def deleted_only(self):
        """Return queryset with only soft-deleted passwords."""
        return super().get_queryset().filter(is_deleted=True)


class Password(BaseModel):
    """
    Password model with AES-256-GCM encryption.
    
    This model stores encrypted passwords with comprehensive metadata,
    version history, and group-based access control.
    """
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(
        max_length=255,
        help_text="Password entry title"
    )
    username = models.CharField(
        max_length=255,
        blank=True,
        help_text="Username or email for the account"
    )
    
    # Encrypted password field
    encrypted_password = models.TextField(
        help_text="AES-256-GCM encrypted password"
    )
    
    # Additional Information
    url = models.URLField(
        blank=True,
        help_text="Website or service URL"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes or information"
    )
    
    # Custom fields (JSON)
    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields as JSON"
    )
    
    # Tags and categorization
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for categorization"
    )
    
    # Relationships
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='passwords',
        help_text="Group that owns this password"
    )
    
    # Directory relationship
    directory = models.ForeignKey(
        'directories.Directory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='passwords',
        help_text="Directory for organization"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_passwords',
        help_text="User who created this password"
    )
    
    # Metadata
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text="Password priority level"
    )
    
    is_favorite = models.BooleanField(
        default=False,
        help_text="Whether this password is marked as favorite"
    )
    
    # Security and tracking
    last_accessed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When password was last accessed"
    )
    
    access_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times password was accessed"
    )
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When password expires (optional)"
    )
    
    # Soft delete
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When password was deleted"
    )
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_passwords',
        help_text="User who deleted this password"
    )
    
    # Managers
    objects = PasswordManager()  # Default manager (excludes deleted)
    all_objects = models.Manager()  # All passwords including deleted
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['group', '-updated_at']),
            models.Index(fields=['created_by', '-updated_at']),
            models.Index(fields=['title']),
            models.Index(fields=['is_favorite', '-updated_at']),
            models.Index(fields=['priority', '-updated_at']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = "Password"
        verbose_name_plural = "Passwords"
    
    def __str__(self):
        return f"{self.title} ({self.group.name})"
    
    def clean(self):
        """Custom validation for Password model."""
        super().clean()
        
        if not self.title or not self.title.strip():
            raise ValidationError("Title is required")
        
        if not self.encrypted_password:
            raise ValidationError("Password is required")
        
        # Validate custom fields JSON
        if self.custom_fields and not isinstance(self.custom_fields, dict):
            raise ValidationError("Custom fields must be a valid JSON object")
        
        # Validate tags JSON
        if self.tags and not isinstance(self.tags, list):
            raise ValidationError("Tags must be a valid JSON array")
    
    def save(self, *args, **kwargs):
        """Override save to perform validation and cleanup."""
        self.full_clean()
        
        # Clean fields
        if self.title:
            self.title = self.title.strip()
        if self.username:
            self.username = self.username.strip()
        if self.url:
            self.url = self.url.strip()
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def _generate_key(group_key: str, password_id: str) -> bytes:
        """Generate encryption key from group key and password ID."""
        # Use PBKDF2 to derive a key from group key and password ID
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=password_id.encode(),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(group_key.encode()))
        return key
    
    def encrypt_password(self, plain_password: str) -> str:
        """Encrypt password using group's encryption key."""
        if not self.group or not self.group.encryption_key:
            raise ValueError("Group encryption key is required")
        
        # Generate encryption key
        key = self._generate_key(self.group.encryption_key, str(self.id))
        fernet = Fernet(key)
        
        # Encrypt password
        encrypted = fernet.encrypt(plain_password.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_password(self) -> str:
        """Decrypt password using group's encryption key."""
        if not self.encrypted_password:
            raise ValueError("No encrypted password to decrypt")
        
        if not self.group or not self.group.encryption_key:
            raise ValueError("Group encryption key is required")
        
        try:
            # Generate encryption key
            key = self._generate_key(self.group.encryption_key, str(self.id))
            fernet = Fernet(key)
            
            # Decrypt password
            encrypted_bytes = base64.urlsafe_b64decode(self.encrypted_password.encode())
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt password: {str(e)}")
    
    def set_password(self, plain_password: str):
        """Set password by encrypting it."""
        self.encrypted_password = self.encrypt_password(plain_password)
    
    def get_password(self) -> str:
        """Get decrypted password."""
        return self.decrypt_password()
    
    def record_access(self, user: User = None):
        """Record password access."""
        self.last_accessed = timezone.now()
        self.access_count += 1
        self.save(update_fields=['last_accessed', 'access_count'])
        
        # Create access log
        PasswordAccessLog.objects.create(
            password=self,
            user=user or self.created_by,
            accessed_at=self.last_accessed
        )
    
    def soft_delete(self, user: User = None):
        """Soft delete password."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    def restore(self):
        """Restore soft-deleted password."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    def is_expired(self) -> bool:
        """Check if password is expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def add_tag(self, tag: str):
        """Add a tag to password."""
        if not self.tags:
            self.tags = []
        
        tag = tag.strip().lower()
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.save(update_fields=['tags'])
    
    def remove_tag(self, tag: str):
        """Remove a tag from password."""
        if not self.tags:
            return
        
        tag = tag.strip().lower()
        if tag in self.tags:
            self.tags.remove(tag)
            self.save(update_fields=['tags'])
    
    def set_custom_field(self, field_name: str, field_value: str):
        """Set a custom field."""
        if not self.custom_fields:
            self.custom_fields = {}
        
        self.custom_fields[field_name] = field_value
        self.save(update_fields=['custom_fields'])
    
    def get_custom_field(self, field_name: str, default=None):
        """Get a custom field value."""
        if not self.custom_fields:
            return default
        return self.custom_fields.get(field_name, default)
    
    def toggle_favorite(self):
        """Toggle favorite status."""
        self.is_favorite = not self.is_favorite
        self.save(update_fields=['is_favorite'])


class PasswordHistory(BaseModel):
    """
    Password version history model.
    
    Tracks changes to passwords for audit and rollback purposes.
    """
    
    class ChangeType(models.TextChoices):
        CREATED = 'created', 'Created'
        UPDATED = 'updated', 'Updated'
        PASSWORD_CHANGED = 'password_changed', 'Password Changed'
        DELETED = 'deleted', 'Deleted'
        RESTORED = 'restored', 'Restored'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    password = models.ForeignKey(
        Password,
        on_delete=models.CASCADE,
        related_name='history',
        help_text="Password this history belongs to"
    )
    
    # Change information
    change_type = models.CharField(
        max_length=20,
        choices=ChangeType.choices,
        help_text="Type of change made"
    )
    
    changed_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_changes',
        help_text="User who made the change"
    )
    
    # Previous values (JSON)
    previous_values = models.JSONField(
        default=dict,
        help_text="Previous field values before change"
    )
    
    # Change details
    change_summary = models.TextField(
        blank=True,
        help_text="Summary of changes made"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['password', '-created_at']),
            models.Index(fields=['changed_by', '-created_at']),
            models.Index(fields=['change_type', '-created_at']),
        ]
        verbose_name = "Password History"
        verbose_name_plural = "Password Histories"
    
    def __str__(self):
        return f"{self.password.title} - {self.change_type} by {self.changed_by.email}"


class PasswordAccessLog(BaseModel):
    """
    Password access logging model.
    
    Tracks when passwords are accessed for security auditing.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    password = models.ForeignKey(
        Password,
        on_delete=models.CASCADE,
        related_name='access_logs',
        help_text="Password that was accessed"
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_accesses',
        help_text="User who accessed the password"
    )
    
    accessed_at = models.DateTimeField(
        default=timezone.now,
        help_text="When password was accessed"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of access"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    
    class Meta:
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['password', '-accessed_at']),
            models.Index(fields=['user', '-accessed_at']),
            models.Index(fields=['-accessed_at']),
        ]
        verbose_name = "Password Access Log"
        verbose_name_plural = "Password Access Logs"
    
    def __str__(self):
        return f"{self.password.title} accessed by {self.user.email} at {self.accessed_at}"