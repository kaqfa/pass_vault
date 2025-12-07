"""
Directory models for Pass-Man Enterprise Password Management System.

This module defines the Directory model for organizing passwords in a hierarchical structure.

Related Documentation:
- SRS.md: Section 3.3 Directory Management
- ARCHITECTURE.md: Database Design - Directory Model
- CODING_STANDARDS.md: Model Design Best Practices
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.core.models import BaseModel
from apps.groups.models import Group

User = get_user_model()


class Directory(BaseModel):
    """
    Directory model for hierarchical organization of passwords.
    
    Directories allow users to organize passwords within a group into a folder structure.
    Directories can be nested (parent-child relationship).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        help_text="Directory name (max 100 characters)"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional directory description"
    )
    
    # Hierarchy
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subdirectories',
        help_text="Parent directory (null for root directories)"
    )
    
    # Ownership and Access
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='directories',
        help_text="Group that owns this directory"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_directories',
        help_text="User who created this directory"
    )
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['group', 'parent', 'name']),
            models.Index(fields=['group', '-created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'parent', 'name'],
                name='unique_directory_name_per_parent'
            )
        ]
        verbose_name = "Directory"
        verbose_name_plural = "Directories"
    
    def __str__(self):
        return f"{self.name} ({self.group.name})"
    
    def clean(self):
        """Custom validation for Directory model."""
        super().clean()
        
        if not self.name or not self.name.strip():
            raise ValidationError("Directory name cannot be empty")
        
        if len(self.name.strip()) > 100:
            raise ValidationError("Directory name too long (max 100 characters)")
            
        # Prevent circular references
        if self.parent and self.parent == self:
            raise ValidationError("Directory cannot be its own parent")
            
        if self.parent and self.parent.group != self.group:
            raise ValidationError("Parent directory must belong to the same group")
            
    def save(self, *args, **kwargs):
        """Override save to perform validation."""
        self.full_clean()
        
        # Clean name
        if self.name:
            self.name = self.name.strip()
            
        super().save(*args, **kwargs)
        
    def get_path(self):
        """Get the full path of the directory."""
        if self.parent:
            return f"{self.parent.get_path()}/{self.name}"
        return self.name
        
    def get_password_count(self):
        """Get count of passwords in this directory."""
        # This will be available once the Password model has the directory foreign key
        if hasattr(self, 'passwords'):
            return self.passwords.count()
        return 0
