"""
Notification models for Pass-Man.

This module defines the Notification model for user notifications.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import BaseModel

User = get_user_model()


class Notification(BaseModel):
    """
    User notification model.

    Tracks notifications for users such as password shares, access alerts, etc.
    """

    class Type(models.TextChoices):
        PASSWORD_SHARED = 'password_shared', 'Password Shared'
        SHARE_REVOKED = 'share_revoked', 'Share Revoked'
        PASSWORD_ACCESS = 'password_access', 'Password Accessed'
        SYSTEM = 'system', 'System'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="User who will receive this notification"
    )

    type = models.CharField(
        max_length=50,
        choices=Type.choices,
        help_text="Type of notification"
    )

    title = models.CharField(
        max_length=200,
        help_text="Notification title"
    )

    message = models.TextField(
        help_text="Notification message"
    )

    is_read = models.BooleanField(
        default=False,
        help_text="Whether notification has been read"
    )

    # Optional links
    link_url = models.URLField(
        blank=True,
        help_text="Optional URL to navigate to when clicked"
    )

    # Related object IDs (for password shares, etc.)
    password_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Related password ID if applicable"
    )

    share_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Related share ID if applicable"
    )

    # Metadata
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional data for the notification"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['type']),
        ]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.title} - {self.user.email}"

    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
