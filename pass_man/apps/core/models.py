"""
Core models for Pass-Man Enterprise Password Management System.

This module contains base models and shared functionality that other
applications can inherit from or use.

Related Documentation:
- SRS.md: Section 7 Database Schema
- ARCHITECTURE.md: Models Layer
- CODING_STANDARDS.md: Model Design
"""

import uuid
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    Abstract base model that provides common fields for all models.
    
    This model includes:
    - UUID primary key for security
    - Created and updated timestamps
    - Soft delete functionality
    
    All other models should inherit from this base model to ensure
    consistency across the application.
    
    Related Documentation:
    - CODING_STANDARDS.md: Model Design Best Practices
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this record"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this record was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this record was last updated"
    )
    
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag - if True, record is considered deleted"
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this record was soft deleted"
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def soft_delete(self):
        """
        Perform a soft delete on this record.
        
        Sets is_deleted to True and records the deletion timestamp.
        The record remains in the database but is excluded from
        normal queries.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
    
    def restore(self):
        """
        Restore a soft-deleted record.
        
        Sets is_deleted to False and clears the deletion timestamp.
        """
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class ActiveManager(models.Manager):
    """
    Manager that excludes soft-deleted records by default.
    
    This manager automatically filters out records where is_deleted=True,
    providing a clean interface for working with active records only.
    """
    
    def get_queryset(self):
        """Return queryset excluding soft-deleted records."""
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """
    Manager that includes all records, including soft-deleted ones.
    
    This manager provides access to all records in the database,
    including those that have been soft-deleted.
    """
    
    def get_queryset(self):
        """Return queryset including all records."""
        return super().get_queryset()


class TimestampedModel(BaseModel):
    """
    Abstract model that extends BaseModel with additional timestamp fields.
    
    This model is useful for entities that need to track more detailed
    timing information beyond just created/updated timestamps.
    """
    
    first_accessed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this record was first accessed"
    )
    
    last_accessed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this record was last accessed"
    )
    
    access_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this record has been accessed"
    )
    
    class Meta:
        abstract = True
    
    def record_access(self):
        """
        Record an access to this record.
        
        Updates the access timestamps and increments the access counter.
        """
        now = timezone.now()
        
        if not self.first_accessed:
            self.first_accessed = now
        
        self.last_accessed = now
        self.access_count += 1
        
        self.save(update_fields=['first_accessed', 'last_accessed', 'access_count'])