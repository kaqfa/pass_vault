"""
Directory services for Pass-Man Enterprise Password Management System.

This module contains business logic for directory management including creation,
retrieval, updates, deletion, and access control.

Related Documentation:
- SRS.md: Section 4.2 Directory Management
- ARCHITECTURE.md: Service Layer Pattern
- CODING_STANDARDS.md: Service Layer Best Practices
"""

import logging
from typing import Dict, List, Optional
from django.db import transaction
from django.db.models import Q, Count
from django.core.exceptions import PermissionDenied

from apps.core.exceptions import ServiceError, ValidationError
from apps.directories.models import Directory
from apps.groups.models import Group, UserGroup
from apps.users.models import User
from apps.passwords.models import Password

logger = logging.getLogger(__name__)


class DirectoryService:
    """Service for directory management operations."""

    @staticmethod
    @transaction.atomic
    def create_directory(user: User, group_id: str, name: str, parent_id: str = None,
                         description: str = '') -> Directory:
        """
        Create a new directory in a group.

        Args:
            user (User): User creating the directory
            group_id (str): Group ID where directory will be created
            name (str): Directory name
            parent_id (str): Optional parent directory ID for subdirectories
            description (str): Optional directory description

        Returns:
            Directory: Created directory instance

        Raises:
            ValidationError: If directory data is invalid
            PermissionDenied: If user doesn't have permission
            ServiceError: If creation fails
        """
        try:
            # Get group
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                raise ValidationError({'group_id': 'Group not found'})

            # Check permissions - only owner or admin can create directories
            if not DirectoryService._can_user_manage_directories(user, group):
                raise PermissionDenied("You don't have permission to create directories in this group")

            # Validate parent directory if provided
            parent = None
            if parent_id:
                try:
                    parent = Directory.objects.get(id=parent_id, group=group)
                    # Enforce 2-level limit - parent must be a root directory
                    if parent.parent is not None:
                        raise ValidationError({'parent_id': 'Cannot create subdirectory at level 3. Maximum 2 levels allowed.'})
                except Directory.DoesNotExist:
                    raise ValidationError({'parent_id': 'Parent directory not found in this group'})

            # Check for duplicate directory name in same parent
            existing = Directory.objects.filter(
                group=group,
                name=name.strip(),
                parent=parent
            ).first()

            if existing:
                raise ValidationError({'name': 'A directory with this name already exists in this location'})

            # Create directory
            directory = Directory(
                name=name.strip(),
                description=description.strip(),
                group=group,
                parent=parent,
                created_by=user
            )

            directory.full_clean()
            directory.save()

            logger.info(f"Directory created: {directory.name} by {user.email}")
            return directory

        except (ValidationError, PermissionDenied):
            raise
        except Exception as e:
            logger.error(f"Directory creation failed: {str(e)}")
            raise ServiceError(f"Failed to create directory: {str(e)}")

    @staticmethod
    def get_directory(user: User, directory_id: str) -> Directory:
        """
        Get directory by ID with permission check.

        Args:
            user (User): User requesting the directory
            directory_id (str): Directory ID

        Returns:
            Directory: Directory instance

        Raises:
            PermissionDenied: If user doesn't have permission
            ServiceError: If retrieval fails
        """
        try:
            directory = Directory.objects.get(id=directory_id)

            # Check permissions - user must be member of the group
            if not DirectoryService._can_user_view_directory(user, directory):
                raise PermissionDenied("You don't have permission to view this directory")

            return directory

        except Directory.DoesNotExist:
            raise ServiceError("Directory not found")
        except PermissionDenied:
            raise
        except Exception as e:
            logger.error(f"Directory retrieval failed: {str(e)}")
            raise ServiceError(f"Failed to retrieve directory: {str(e)}")

    @staticmethod
    def get_group_directories(user: User, group_id: str) -> List[Directory]:
        """
        Get all directories in a group as a 2-level tree structure.

        Args:
            user (User): User requesting directories
            group_id (str): Group ID

        Returns:
            List[Directory]: List of root directories with subdirectories prefetched

        Raises:
            PermissionDenied: If user doesn't have permission
            ServiceError: If retrieval fails
        """
        try:
            # Get group
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                raise ServiceError("Group not found")

            # Check permissions
            if not DirectoryService._can_user_view_directory(user, group=group):
                raise PermissionDenied("You don't have permission to view directories in this group")

            # Get root directories (no parent) with subdirectories prefetched
            root_directories = Directory.objects.filter(
                group=group,
                parent__isnull=True
            ).select_related('created_by').prefetch_related(
                'subdirectories__created_by'
            ).annotate(
                password_count=Count('passwords'),
                subdirectory_count=Count('subdirectories')
            ).order_by('name')

            return list(root_directories)

        except PermissionDenied:
            raise
        except Exception as e:
            logger.error(f"Group directories retrieval failed: {str(e)}")
            raise ServiceError(f"Failed to retrieve directories: {str(e)}")

    @staticmethod
    @transaction.atomic
    def update_directory(user: User, directory_id: str, name: str = None,
                         description: str = None) -> Directory:
        """
        Update directory details.

        Args:
            user (User): User updating the directory
            directory_id (str): Directory ID
            name (str): New directory name (optional)
            description (str): New description (optional)

        Returns:
            Directory: Updated directory instance

        Raises:
            ValidationError: If data is invalid
            PermissionDenied: If user doesn't have permission
            ServiceError: If update fails
        """
        try:
            directory = DirectoryService.get_directory(user, directory_id)

            # Check edit permission
            if not DirectoryService._can_user_manage_directory(user, directory):
                raise PermissionDenied("You don't have permission to edit this directory")

            # Update name if provided
            if name is not None:
                new_name = name.strip()
                if new_name != directory.name:
                    # Check for duplicate name
                    existing = Directory.objects.filter(
                        group=directory.group,
                        parent=directory.parent,
                        name=new_name
                    ).exclude(id=directory.id).first()

                    if existing:
                        raise ValidationError({'name': 'A directory with this name already exists in this location'})

                    directory.name = new_name

            # Update description if provided
            if description is not None:
                directory.description = description.strip()

            directory.full_clean()
            directory.save()

            logger.info(f"Directory updated: {directory.name} by {user.email}")
            return directory

        except (ValidationError, PermissionDenied):
            raise
        except Exception as e:
            logger.error(f"Directory update failed: {str(e)}")
            raise ServiceError(f"Failed to update directory: {str(e)}")

    @staticmethod
    @transaction.atomic
    def delete_directory(user: User, directory_id: str, move_passwords_to: str = None) -> bool:
        """
        Delete directory with password handling options.

        Args:
            user (User): User deleting the directory
            directory_id (str): Directory ID
            move_passwords_to (str): Target directory ID to move passwords to (optional)

        Returns:
            bool: True if deletion successful

        Raises:
            PermissionDenied: If user doesn't have permission
            ServiceError: If deletion fails
        """
        try:
            directory = DirectoryService.get_directory(user, directory_id)

            # Check delete permission
            if not DirectoryService._can_user_manage_directory(user, directory):
                raise PermissionDenied("You don't have permission to delete this directory")

            # Get password count
            password_count = directory.passwords.count()

            # Handle passwords if move_passwords_to is specified
            if move_passwords_to:
                try:
                    target_directory = Directory.objects.get(id=move_passwords_to, group=directory.group)
                    # Move passwords to target directory
                    Password.objects.filter(directory=directory).update(directory=target_directory)
                    logger.info(f"Moved {password_count} passwords from {directory.name} to {target_directory.name}")
                except Directory.DoesNotExist:
                    raise ServiceError("Target directory not found in the same group")

            # Handle subdirectories - delete them first (cascade)
            subdirectory_count = directory.subdirectories.count()
            if subdirectory_count > 0:
                # Recursively delete subdirectories
                for subdir in directory.subdirectories.all():
                    DirectoryService.delete_directory(user, str(subdir.id))

            # Log password count for deletion
            if password_count > 0 and not move_passwords_to:
                # Passwords will be cascade deleted due to SET_NULL or need to be set to NULL
                # Update: Password has on_delete=SET_NULL for directory, so they won't be cascade deleted
                Password.objects.filter(directory=directory).update(directory=None)
                logger.info(f"Set passwords in {directory.name} to no directory")

            # Delete the directory
            directory_name = directory.name
            directory.delete()

            logger.info(f"Directory deleted: {directory_name} by {user.email}")
            return True

        except (PermissionDenied, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Directory deletion failed: {str(e)}")
            raise ServiceError(f"Failed to delete directory: {str(e)}")

    @staticmethod
    def get_directory_tree(user: User, group_id: str) -> List[Dict]:
        """
        Get directory tree structure for a group.

        Args:
            user (User): User requesting the tree
            group_id (str): Group ID

        Returns:
            List[Dict]: Tree structure with directories and their subdirectories
        """
        try:
            directories = DirectoryService.get_group_directories(user, group_id)

            tree = []
            for directory in directories:
                node = {
                    'id': str(directory.id),
                    'name': directory.name,
                    'description': directory.description,
                    'level': 1,
                    'password_count': directory.password_count,
                    'subdirectory_count': directory.subdirectory_count,
                    'created_at': directory.created_at.isoformat(),
                    'children': []
                }

                # Add subdirectories
                for subdir in directory.subdirectories.all():
                    subnode = {
                        'id': str(subdir.id),
                        'name': subdir.name,
                        'description': subdir.description,
                        'level': 2,
                        'password_count': subdir.passwords.count(),
                        'created_at': subdir.created_at.isoformat(),
                        'children': []
                    }
                    node['children'].append(subnode)

                tree.append(node)

            return tree

        except Exception as e:
            logger.error(f"Directory tree generation failed: {str(e)}")
            raise ServiceError(f"Failed to generate directory tree: {str(e)}")

    @staticmethod
    def get_directory_passwords(user: User, directory_id: str) -> List[Password]:
        """
        Get all passwords in a directory.

        Args:
            user (User): User requesting passwords
            directory_id (str): Directory ID

        Returns:
            List[Password]: List of passwords in the directory
        """
        try:
            directory = DirectoryService.get_directory(user, directory_id)

            passwords = Password.objects.filter(
                directory=directory,
                is_deleted=False
            ).select_related('group', 'created_by').order_by('-updated_at')

            return list(passwords)

        except Exception as e:
            logger.error(f"Directory passwords retrieval failed: {str(e)}")
            raise ServiceError(f"Failed to retrieve passwords: {str(e)}")

    @staticmethod
    def _can_user_manage_directories(user: User, group: Group) -> bool:
        """Check if user can manage directories in a group."""
        # Group owner can always manage
        if group.owner == user:
            return True

        # Check group membership and role
        membership = UserGroup.objects.filter(user=user, group=group).first()
        if not membership:
            return False

        # Only admins can manage directories
        return membership.role == UserGroup.Role.ADMIN

    @staticmethod
    def _can_user_view_directory(user: User, directory: Directory = None, group: Group = None) -> bool:
        """Check if user can view directory."""
        target_group = directory.group if directory else group

        # Group owner can always view
        if target_group.owner == user:
            return True

        # Check group membership
        return UserGroup.objects.filter(user=user, group=target_group).exists()

    @staticmethod
    def _can_user_manage_directory(user: User, directory: Directory) -> bool:
        """Check if user can manage a specific directory."""
        # Group owner can always manage
        if directory.group.owner == user:
            return True

        # Directory creator can always manage
        if directory.created_by == user:
            return True

        # Check if user is group admin
        membership = UserGroup.objects.filter(user=user, group=directory.group).first()
        return membership and membership.role == UserGroup.Role.ADMIN
