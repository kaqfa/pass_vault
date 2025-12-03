"""
Group models for Pass-Man Enterprise Password Management System.

This module defines the Group and UserGroup models for organizing users
and managing collaborative password sharing.

Related Documentation:
- SRS.md: Section 3.2 Group Management
- ARCHITECTURE.md: Database Design - Group Models
- CODING_STANDARDS.md: Model Design Best Practices
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.models import BaseModel

User = get_user_model()


class Group(BaseModel):
    """
    Group model for organizing users and passwords.
    
    Groups allow users to collaborate and share passwords securely.
    Each group has an owner and can have multiple members with different roles.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        help_text="Group name (max 100 characters)"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional group description"
    )
    
    # Group ownership
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_groups',
        help_text="User who owns this group"
    )
    
    # Group settings
    is_personal = models.BooleanField(
        default=False,
        help_text="True if this is a personal vault group"
    )
    
    # Group encryption key (stored encrypted)
    encryption_key = models.TextField(
        blank=True,
        help_text="Encrypted group encryption key for password encryption"
    )
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['owner', 'name']),
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['is_personal']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'name'],
                name='unique_group_name_per_owner'
            )
        ]
        verbose_name = "Group"
        verbose_name_plural = "Groups"
    
    def __str__(self):
        return f"{self.name} (Owner: {self.owner.full_name})"
    
    def clean(self):
        """Custom validation for Group model."""
        super().clean()
        
        if not self.name or not self.name.strip():
            raise ValidationError("Group name cannot be empty")
        
        if len(self.name.strip()) > 100:
            raise ValidationError("Group name too long (max 100 characters)")
        
        # Validate unique name per owner
        if self.pk:
            existing = Group.objects.filter(
                owner=self.owner,
                name=self.name
            ).exclude(pk=self.pk)
        else:
            existing = Group.objects.filter(
                owner=self.owner,
                name=self.name
            )
        
        if existing.exists():
            raise ValidationError("You already have a group with this name")
    
    def save(self, *args, **kwargs):
        """Override save to perform validation and setup."""
        self.full_clean()
        
        # Clean name
        if self.name:
            self.name = self.name.strip()
        
        # Generate encryption key if not exists
        if not self.encryption_key:
            self._generate_encryption_key()
        
        super().save(*args, **kwargs)
    
    def _generate_encryption_key(self):
        """Generate and store encrypted group encryption key."""
        from cryptography.fernet import Fernet
        import base64
        
        # Generate new key
        key = Fernet.generate_key()
        
        # For now, store the key directly (in production, this should be encrypted)
        # TODO: Implement proper key encryption with user's master key
        self.encryption_key = base64.urlsafe_b64encode(key).decode()
    
    def get_members(self):
        """Get all members of this group."""
        return User.objects.filter(usergroup__group=self).distinct()
    
    def get_member_count(self):
        """Get count of group members."""
        return self.usergroup_set.count()
    
    def has_member(self, user):
        """Check if user is a member of this group."""
        return self.usergroup_set.filter(user=user).exists()
    
    def get_user_role(self, user):
        """Get user's role in this group."""
        membership = self.usergroup_set.filter(user=user).first()
        return membership.role if membership else None
    
    def can_user_manage_members(self, user):
        """Check if user can manage group members."""
        if self.owner == user:
            return True
        
        membership = self.usergroup_set.filter(user=user).first()
        return membership and membership.role == UserGroup.Role.ADMIN
    
    def get_password_count(self):
        """Get count of passwords in this group."""
        return self.passwords.count()


class UserGroup(BaseModel):
    """
    Membership model linking users to groups with roles.
    
    This model represents the many-to-many relationship between users and groups,
    with additional fields for role management and membership tracking.
    """
    
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationship fields
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="User who is a member of the group"
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        help_text="Group the user belongs to"
    )
    
    # Role and permissions
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
        help_text="User's role in the group"
    )
    
    # Membership tracking
    joined_at = models.DateTimeField(
        default=timezone.now,
        help_text="When user joined the group"
    )
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_memberships',
        help_text="User who added this member to the group"
    )
    
    class Meta:
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['user', 'group']),
            models.Index(fields=['group', 'role']),
            models.Index(fields=['group', '-joined_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'group'],
                name='unique_user_group_membership'
            )
        ]
        verbose_name = "Group Membership"
        verbose_name_plural = "Group Memberships"
    
    def __str__(self):
        return f"{self.user.full_name} - {self.group.name} ({self.role})"
    
    def clean(self):
        """Custom validation for UserGroup model."""
        super().clean()
        
        # Validate that group owner has owner role
        if self.group and self.group.owner == self.user and self.role != self.Role.OWNER:
            raise ValidationError("Group owner must have owner role")
        
        # Validate that only group owner can have owner role
        if self.role == self.Role.OWNER and self.group and self.group.owner != self.user:
            raise ValidationError("Only group owner can have owner role")
    
    def save(self, *args, **kwargs):
        """Override save to perform validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def can_manage_members(self):
        """Check if this membership allows managing other members."""
        return self.role in [self.Role.OWNER, self.Role.ADMIN]
    
    def can_manage_passwords(self):
        """Check if this membership allows managing passwords."""
        return self.role in [self.Role.OWNER, self.Role.ADMIN, self.Role.MEMBER]
    
    def can_view_passwords(self):
        """Check if this membership allows viewing passwords."""
        return True  # All members can view passwords
    
    def is_owner(self):
        """Check if this is an owner membership."""
        return self.role == self.Role.OWNER
    
    def is_admin(self):
        """Check if this is an admin membership."""
        return self.role == self.Role.ADMIN
    
    def is_member(self):
        """Check if this is a regular member membership."""
        return self.role == self.Role.MEMBER