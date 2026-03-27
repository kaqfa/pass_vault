"""
Password sharing service for Pass-Man Enterprise Password Management System.

This module contains business logic for password sharing including user-to-user
sharing, permission management, expiration handling, and share revocation.

Related Documentation:
- SRS.md: Section 4.2 Password Sharing
- ARCHITECTURE.md: Service Layer Pattern
- CODING_STANDARDS.md: Service Layer Best Practices
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.contrib.auth import get_user_model

from apps.core.exceptions import ServiceError, ValidationError as CustomValidationError
from apps.passwords.models import Password, PasswordShare
from apps.groups.models import Group, UserGroup

User = get_user_model()
logger = logging.getLogger(__name__)


class PasswordShareService:
    """Service for password sharing operations."""

    @staticmethod
    @transaction.atomic
    def share_password(
        user: User,
        password_id: str,
        email: str,
        permission: str = PasswordShare.Permission.VIEW,
        expires_at: Optional[datetime] = None,
        message: Optional[str] = None
    ) -> PasswordShare:
        """
        Share a password with another user.

        Args:
            user (User): User sharing the password
            password_id (str): Password ID to share
            email (str): Email of user to share with
            permission (str): Permission level (view, copy, edit)
            expires_at (datetime): Optional expiration date
            message (str): Optional message to recipient

        Returns:
            PasswordShare: Created share instance

        Raises:
            ValidationError: If share data is invalid
            PermissionDenied: If user doesn't have permission
            ServiceError: If sharing fails
        """
        try:
            # Get password
            try:
                password = Password.objects.get(id=password_id)
            except Password.DoesNotExist:
                raise ServiceError("Password not found")

            # Check if user can share this password
            if not PasswordShareService._can_user_share_password(user, password):
                raise PermissionDenied("You don't have permission to share this password")

            # Validate permission
            valid_permissions = [p[0] for p in PasswordShare.Permission.choices]
            if permission not in valid_permissions:
                raise CustomValidationError({
                    'permission': f'Invalid permission. Must be one of: {", ".join(valid_permissions)}'
                })

            # Find recipient user
            email = email.strip().lower()
            try:
                shared_with = User.objects.get(email=email)
            except User.DoesNotExist:
                raise CustomValidationError({'email': f'User with email "{email}" not found'})

            # Prevent self-sharing
            if shared_with == user:
                raise CustomValidationError({'email': 'Cannot share password with yourself'})

            # Check if already shared
            if PasswordShare.objects.filter(password=password, shared_with=shared_with).exists():
                raise CustomValidationError({'email': 'Password is already shared with this user'})

            # Validate expiration date
            if expires_at:
                if expires_at <= timezone.now():
                    raise CustomValidationError({'expires_at': 'Expiration date must be in the future'})

                # Optional: limit maximum share duration
                max_expiration = timezone.now() + timedelta(days=365)
                if expires_at > max_expiration:
                    raise CustomValidationError({'expires_at': 'Share cannot expire more than 1 year from now'})

            # Create the share
            share = PasswordShare.objects.create(
                password=password,
                shared_by=user,
                shared_with=shared_with,
                permission=permission,
                expires_at=expires_at
            )

            logger.info(
                f"Password '{password.title}' shared by {user.email} "
                f"with {shared_with.email} ({permission})"
            )

            # Create notification if notification app exists
            try:
                from apps.notifications.services import NotificationService
                NotificationService.notify_password_shared(share, message)
            except ImportError:
                # Notification app not created yet, skip
                pass

            return share

        except CustomValidationError:
            raise
        except PermissionDenied:
            raise
        except Exception as e:
            logger.error(f"Password share failed: {str(e)}")
            raise ServiceError(f"Failed to share password: {str(e)}")

    @staticmethod
    def get_shared_with_user(user: User, include_expired: bool = False) -> List[PasswordShare]:
        """
        Get passwords shared with the user.

        Args:
            user (User): User to get shares for
            include_expired (bool): Whether to include expired shares

        Returns:
            List[PasswordShare]: List of shares
        """
        try:
            queryset = PasswordShare.objects.filter(
                shared_with=user
            ).select_related(
                'password',
                'password__group',
                'shared_by'
            ).order_by('-created_at')

            if not include_expired:
                # Filter out expired shares
                queryset = queryset.filter(
                    Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
                )

            return list(queryset)

        except Exception as e:
            logger.error(f"Get shared with user failed: {str(e)}")
            raise ServiceError(f"Failed to get shared passwords: {str(e)}")

    @staticmethod
    def get_shared_by_user(user: User, include_expired: bool = False) -> List[PasswordShare]:
        """
        Get passwords shared by the user.

        Args:
            user (User): User who shared the passwords
            include_expired (bool): Whether to include expired shares

        Returns:
            List[PasswordShare]: List of shares
        """
        try:
            queryset = PasswordShare.objects.filter(
                shared_by=user
            ).select_related(
                'password',
                'password__group',
                'shared_with'
            ).order_by('-created_at')

            if not include_expired:
                # Filter out expired shares
                queryset = queryset.filter(
                    Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
                )

            return list(queryset)

        except Exception as e:
            logger.error(f"Get shared by user failed: {str(e)}")
            raise ServiceError(f"Failed to get shared passwords: {str(e)}")

    @staticmethod
    @transaction.atomic
    def revoke_share(user: User, share_id: str) -> bool:
        """
        Revoke a password share.

        Args:
            user (User): User revoking the share
            share_id (str): Share ID to revoke

        Returns:
            bool: True if revocation successful

        Raises:
            PermissionDenied: If user doesn't have permission
            ServiceError: If revocation fails
        """
        try:
            share = PasswordShare.objects.select_related('password', 'shared_with').get(id=share_id)
            password = share.password

            # Check permission - only the sharer or password owner/group admin can revoke
            if not PasswordShareService._can_user_revoke_share(user, share):
                raise PermissionDenied("You don't have permission to revoke this share")

            # Store info for notification
            shared_with = share.shared_with
            password_title = password.title

            # Delete the share
            share.delete()

            logger.info(
                f"Share revoked for password '{password_title}' "
                f"by {user.email} (was shared with {shared_with.email})"
            )

            # Create notification if notification app exists
            try:
                from apps.notifications.services import NotificationService
                NotificationService.notify_share_revoked(shared_with, password_title, user)
            except ImportError:
                # Notification app not created yet, skip
                pass

            return True

        except PasswordShare.DoesNotExist:
            raise ServiceError("Share not found")
        except PermissionDenied:
            raise
        except Exception as e:
            logger.error(f"Share revocation failed: {str(e)}")
            raise ServiceError(f"Failed to revoke share: {str(e)}")

    @staticmethod
    @transaction.atomic
    def bulk_revoke_shares(user: User, share_ids: List[str]) -> Dict[str, int]:
        """
        Revoke multiple password shares at once.

        Args:
            user (User): User revoking the shares
            share_ids (List[str]): List of share IDs to revoke

        Returns:
            Dict: Count of successful and failed revocations

        Raises:
            PermissionDenied: If user doesn't have permission for any share
        """
        results = {'revoked': 0, 'failed': 0, 'forbidden': 0}

        for share_id in share_ids:
            try:
                PasswordShareService.revoke_share(user, share_id)
                results['revoked'] += 1
            except PermissionDenied:
                results['forbidden'] += 1
            except ServiceError:
                results['failed'] += 1

        return results

    @staticmethod
    @transaction.atomic
    def update_share_permission(
        user: User,
        share_id: str,
        permission: str
    ) -> PasswordShare:
        """
        Update permission level for a share.

        Args:
            user (User): User updating the share
            share_id (str): Share ID to update
            permission (str): New permission level

        Returns:
            PasswordShare: Updated share instance
        """
        try:
            share = PasswordShare.objects.select_related('password').get(id=share_id)

            # Check permission
            if not PasswordShareService._can_user_revoke_share(user, share):
                raise PermissionDenied("You don't have permission to modify this share")

            # Validate permission
            valid_permissions = [p[0] for p in PasswordShare.Permission.choices]
            if permission not in valid_permissions:
                raise CustomValidationError({
                    'permission': f'Invalid permission. Must be one of: {", ".join(valid_permissions)}'
                })

            # Update permission
            old_permission = share.permission
            share.permission = permission
            share.save(update_fields=['permission'])

            logger.info(
                f"Share permission updated for password '{share.password.title}' "
                f"from {old_permission} to {permission} by {user.email}"
            )

            return share

        except PasswordShare.DoesNotExist:
            raise ServiceError("Share not found")
        except CustomValidationError:
            raise
        except PermissionDenied:
            raise
        except Exception as e:
            logger.error(f"Share permission update failed: {str(e)}")
            raise ServiceError(f"Failed to update share permission: {str(e)}")

    @staticmethod
    @transaction.atomic
    def update_share_expiration(
        user: User,
        share_id: str,
        expires_at: Optional[datetime] = None
    ) -> PasswordShare:
        """
        Update expiration date for a share.

        Args:
            user (User): User updating the share
            share_id (str): Share ID to update
            expires_at (datetime): New expiration date (None for no expiration)

        Returns:
            PasswordShare: Updated share instance
        """
        try:
            share = PasswordShare.objects.select_related('password').get(id=share_id)

            # Check permission
            if not PasswordShareService._can_user_revoke_share(user, share):
                raise PermissionDenied("You don't have permission to modify this share")

            # Validate expiration date
            if expires_at and expires_at <= timezone.now():
                raise CustomValidationError({'expires_at': 'Expiration date must be in the future'})

            # Update expiration
            share.expires_at = expires_at
            share.save(update_fields=['expires_at'])

            logger.info(
                f"Share expiration updated for password '{share.password.title}' "
                f"by {user.email}"
            )

            return share

        except PasswordShare.DoesNotExist:
            raise ServiceError("Share not found")
        except CustomValidationError:
            raise
        except PermissionDenied:
            raise
        except Exception as e:
            logger.error(f"Share expiration update failed: {str(e)}")
            raise ServiceError(f"Failed to update share expiration: {str(e)}")

    @staticmethod
    def search_users(query: str, limit: int = 10, exclude_user: Optional[User] = None) -> List[User]:
        """
        Search users by email or name for sharing.

        Args:
            query (str): Search query
            limit (int): Maximum results to return
            exclude_user (User): User to exclude from results (e.g., self)

        Returns:
            List[User]: List of matching users
        """
        try:
            queryset = User.objects.filter(
                Q(email__icontains=query) | Q(full_name__icontains=query)
            ).filter(is_active=True, banned=False)

            if exclude_user:
                queryset = queryset.exclude(id=exclude_user.id)

            return list(queryset[:limit])

        except Exception as e:
            logger.error(f"User search failed: {str(e)}")
            raise ServiceError(f"Search failed: {str(e)}")

    @staticmethod
    def get_share_for_user(user: User, password_id: str) -> Optional[PasswordShare]:
        """
        Get the share record for a user and password.

        Args:
            user (User): User to check share for
            password_id (str): Password ID

        Returns:
            PasswordShare or None: Share record if exists and not expired
        """
        try:
            share = PasswordShare.objects.filter(
                password_id=password_id,
                shared_with=user
            ).select_related('password', 'shared_by').first()

            if share and share.is_expired():
                return None

            return share

        except Exception as e:
            logger.error(f"Get share for user failed: {str(e)}")
            return None

    @staticmethod
    def cleanup_expired_shares() -> int:
        """
        Delete expired shares (for maintenance).

        Returns:
            int: Number of shares deleted
        """
        try:
            count, _ = PasswordShare.objects.filter(
                expires_at__lt=timezone.now()
            ).delete()

            if count > 0:
                logger.info(f"Cleaned up {count} expired shares")

            return count

        except Exception as e:
            logger.error(f"Cleanup expired shares failed: {str(e)}")
            return 0

    @staticmethod
    def _can_user_share_password(user: User, password: Password) -> bool:
        """Check if user can share the password."""
        # Password creator can share
        if password.created_by == user:
            return True

        # Group owner can share
        if password.group.owner == user:
            return True

        # Group admins can share
        membership = UserGroup.objects.filter(user=user, group=password.group).first()
        return membership and membership.role == UserGroup.Role.ADMIN

    @staticmethod
    def _can_user_revoke_share(user: User, share: PasswordShare) -> bool:
        """Check if user can revoke the share."""
        # The person who created the share can revoke
        if share.shared_by == user:
            return True

        # Password owner can revoke
        if share.password.created_by == user:
            return True

        # Group owner can revoke
        if share.password.group.owner == user:
            return True

        # Group admins can revoke
        membership = UserGroup.objects.filter(user=user, group=share.password.group).first()
        return membership and membership.role == UserGroup.Role.ADMIN

    @staticmethod
    def can_user_view_via_share(user: User, password: Password) -> bool:
        """Check if user can view password via share."""
        share = PasswordShareService.get_share_for_user(user, str(password.id))
        return share is not None

    @staticmethod
    def can_user_copy_via_share(user: User, password: Password) -> bool:
        """Check if user can copy password via share."""
        share = PasswordShareService.get_share_for_user(user, str(password.id))
        if not share:
            return False

        # Copy permission allows copying
        if share.permission == PasswordShare.Permission.COPY:
            return True

        # Edit permission implies copy permission
        if share.permission == PasswordShare.Permission.EDIT:
            return True

        return False

    @staticmethod
    def can_user_edit_via_share(user: User, password: Password) -> bool:
        """Check if user can edit password via share."""
        share = PasswordShareService.get_share_for_user(user, str(password.id))
        return share and share.permission == PasswordShare.Permission.EDIT

    @staticmethod
    def get_user_permission_for_password(user: User, password: Password) -> Optional[str]:
        """
        Get the user's permission level for a password via share.

        Returns the permission level if user has access via share, None otherwise.
        """
        share = PasswordShareService.get_share_for_user(user, str(password.id))
        return share.permission if share else None
