"""
Notification services for Pass-Man.

This module contains business logic for user notifications.
"""

import logging
from typing import Optional
from django.db.models import Q
from django.db.models.query import QuerySet

from apps.notifications.models import Notification
from apps.passwords.models import PasswordShare
from apps.users.models import User

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for notification management."""

    @staticmethod
    def create_notification(
        user: User,
        type: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
        password_id: Optional[str] = None,
        share_id: Optional[str] = None,
        data: dict = None
    ) -> Notification:
        """
        Create a notification for a user.

        Args:
            user (User): User to notify
            type (str): Notification type
            title (str): Notification title
            message (str): Notification message
            link_url (str): Optional link URL
            password_id (str): Optional related password ID
            share_id (str): Optional related share ID
            data (dict): Additional metadata

        Returns:
            Notification: Created notification
        """
        notification = Notification.objects.create(
            user=user,
            type=type,
            title=title,
            message=message,
            link_url=link_url,
            password_id=password_id,
            share_id=share_id,
            data=data or {}
        )

        logger.info(f"Notification created: {title} for {user.email}")
        return notification

    @staticmethod
    def get_user_notifications(user: User, unread_only: bool = False) -> QuerySet:
        """
        Get notifications for a user.

        Args:
            user (User): User to get notifications for
            unread_only (bool): Whether to only get unread notifications

        Returns:
            QuerySet: Notifications query
        """
        queryset = Notification.objects.filter(user=user)

        if unread_only:
            queryset = queryset.filter(is_read=False)

        return queryset.order_by('-created_at')

    @staticmethod
    def get_unread_count(user: User) -> int:
        """Get count of unread notifications for a user."""
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def mark_as_read(user: User, notification_id: str) -> bool:
        """Mark a notification as read."""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False

    @staticmethod
    def mark_all_as_read(user: User) -> int:
        """Mark all notifications as read for a user."""
        count = Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        if count > 0:
            logger.info(f"Marked {count} notifications as read for {user.email}")
        return count

    @staticmethod
    def delete_notification(user: User, notification_id: str) -> bool:
        """Delete a notification."""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.delete()
            return True
        except Notification.DoesNotExist:
            return False

    @staticmethod
    def notify_password_shared(share: PasswordShare, message: Optional[str] = None):
        """Notify user that a password has been shared with them."""
        NotificationService.create_notification(
            user=share.shared_with,
            type=Notification.Type.PASSWORD_SHARED,
            title=f"Password Shared: {share.password.title}",
            message=message or f"{share.shared_by.email} has shared '{share.password.title}' with you.",
            link_url=f"/passwords/{share.password.id}/",
            password_id=str(share.password.id),
            share_id=str(share.id),
            data={
                'shared_by': share.shared_by.email,
                'permission': share.permission,
                'expires_at': share.expires_at.isoformat() if share.expires_at else None
            }
        )

    @staticmethod
    def notify_share_revoked(shared_with: User, password_title: str, revoked_by: User):
        """Notify user that a share has been revoked."""
        NotificationService.create_notification(
            user=shared_with,
            type=Notification.Type.SHARE_REVOKED,
            title=f"Share Revoked: {password_title}",
            message=f"{revoked_by.email} has revoked your access to '{password_title}'.",
            data={
                'revoked_by': revoked_by.email,
                'password_title': password_title
            }
        )

    @staticmethod
    def notify_password_access(user: User, password_title: str, accessed_by: User):
        """Notify user that someone accessed their password."""
        NotificationService.create_notification(
            user=user,
            type=Notification.Type.PASSWORD_ACCESS,
            title=f"Password Accessed: {password_title}",
            message=f"{accessed_by.email} has accessed your password '{password_title}'.",
            link_url=f"/passwords/{user.id}/",
            data={
                'accessed_by': accessed_by.email,
                'password_title': password_title
            }
        )
