"""
Group services for Pass-Man Enterprise Password Management System.

This module contains business logic for group management including creation,
membership management, and default group setup.

Related Documentation:
- SRS.md: Section 3.2 Group Management
- ARCHITECTURE.md: Service Layer Pattern
- CODING_STANDARDS.md: Service Layer Best Practices
"""

import uuid
from typing import Dict, List, Optional
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.exceptions import ServiceError, ValidationError
from apps.groups.models import Group, UserGroup

import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class GroupService:
    """Service for group management operations."""
    
    @staticmethod
    @transaction.atomic
    def create_default_personal_group(user: User) -> Group:
        """
        Create default personal group for new user.
        
        Args:
            user (User): User to create personal group for
            
        Returns:
            Group: Created personal group
            
        Raises:
            ServiceError: If group creation fails
        """
        try:
            # Check if user already has a personal group
            existing_group = Group.objects.filter(
                owner=user,
                name__endswith="'s Personal Vault"
            ).first()
            
            if existing_group:
                logger.info(f"Personal group already exists for user: {user.email}")
                return existing_group
            
            # Create personal group
            group_name = f"{user.full_name}'s Personal Vault"
            group = Group.objects.create(
                name=group_name,
                description="Personal password vault",
                owner=user,
                is_personal=True
            )
            
            # Add user as member (owner is automatically a member)
            UserGroup.objects.create(
                user=user,
                group=group,
                role=UserGroup.Role.OWNER,
                joined_at=timezone.now()
            )
            
            logger.info(f"Personal group created for user: {user.email}")
            
            return group
            
        except Exception as e:
            logger.error(f"Failed to create personal group for user {user.email}: {str(e)}")
            raise ServiceError(f"Failed to create personal group: {str(e)}")
    
    @staticmethod
    def get_user_groups(user: User, query: str = None, role_filter: str = None) -> List[Group]:
        """
        Get groups accessible to user with optional filtering.
        
        Args:
            user (User): User requesting groups
            query (str): Search query for group names
            role_filter (str): Filter by user's role in group
            
        Returns:
            List[Group]: List of accessible groups
        """
        try:
            # Get groups where user is owner or member
            from django.db.models import Q
            
            queryset = Group.objects.filter(
                Q(owner=user) | Q(usergroup__user=user)
            ).distinct().select_related('owner').prefetch_related('usergroup_set__user')
            
            # Apply search query
            if query:
                queryset = queryset.filter(name__icontains=query)
            
            # Apply role filter
            if role_filter:
                if role_filter == 'owner':
                    queryset = queryset.filter(owner=user)
                else:
                    queryset = queryset.filter(usergroup__user=user, usergroup__role=role_filter)
            
            return list(queryset.order_by('name'))
            
        except Exception as e:
            logger.error(f"Get user groups failed: {str(e)}")
            raise ServiceError(f"Failed to get groups: {str(e)}")
    
    @staticmethod
    def get_group(user: User, group_id: str) -> Group:
        """
        Get group by ID with permission check.
        
        Args:
            user (User): User requesting the group
            group_id (str): Group ID
            
        Returns:
            Group: Group instance
            
        Raises:
            ServiceError: If group not found or no permission
        """
        try:
            group = Group.objects.select_related('owner').get(id=group_id)
            
            # Check if user has access to this group
            if not (group.owner == user or UserGroup.objects.filter(user=user, group=group).exists()):
                raise ServiceError("You don't have permission to access this group")
            
            return group
            
        except Group.DoesNotExist:
            raise ServiceError("Group not found")
        except Exception as e:
            logger.error(f"Get group failed: {str(e)}")
            raise ServiceError(f"Failed to get group: {str(e)}")
    
    @staticmethod
    def get_group_members(user: User, group_id: str) -> List[UserGroup]:
        """
        Get group members with permission check.
        
        Args:
            user (User): User requesting members
            group_id (str): Group ID
            
        Returns:
            List[UserGroup]: List of group memberships
            
        Raises:
            ServiceError: If no permission or group not found
        """
        try:
            group = GroupService.get_group(user, group_id)
            
            return list(UserGroup.objects.filter(
                group=group
            ).select_related('user', 'added_by').order_by('-joined_at'))
            
        except Exception as e:
            logger.error(f"Get group members failed: {str(e)}")
            raise ServiceError(f"Failed to get group members: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def update_group(user: User, group_id: str, group_data: Dict) -> Group:
        """
        Update group information.
        
        Args:
            user (User): User updating the group
            group_id (str): Group ID
            group_data (Dict): Updated group data
            
        Returns:
            Group: Updated group instance
            
        Raises:
            ValidationError: If data is invalid
            ServiceError: If update fails or no permission
        """
        try:
            group = GroupService.get_group(user, group_id)
            
            # Check edit permission
            if not GroupService._can_user_edit_group(user, group):
                raise ServiceError("You don't have permission to edit this group")
            
            # Validate data
            if 'name' in group_data:
                name = group_data['name'].strip()
                if not name:
                    raise ValidationError({'name': 'Group name is required'})
                
                if len(name) > 100:
                    raise ValidationError({'name': 'Group name cannot exceed 100 characters'})
                
                # Check for duplicate name (excluding current group)
                if Group.objects.filter(owner=group.owner, name=name).exclude(id=group.id).exists():
                    raise ValidationError({'name': 'A group with this name already exists'})
                
                group.name = name
            
            if 'description' in group_data:
                group.description = group_data['description'].strip()
            
            group.save()
            
            logger.info(f"Group updated: {group.name} by {user.email}")
            return group
            
        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Group update failed: {str(e)}")
            raise ServiceError(f"Failed to update group: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def delete_group(user: User, group_id: str) -> bool:
        """
        Delete group.
        
        Args:
            user (User): User deleting the group
            group_id (str): Group ID
            
        Returns:
            bool: True if deletion successful
            
        Raises:
            ServiceError: If deletion fails or no permission
        """
        try:
            group = GroupService.get_group(user, group_id)
            
            # Only owner can delete group
            if group.owner != user:
                raise ServiceError("Only group owner can delete the group")
            
            # Cannot delete personal group
            if group.is_personal:
                raise ServiceError("Personal groups cannot be deleted")
            
            group_name = group.name
            group.delete()
            
            logger.info(f"Group deleted: {group_name} by {user.email}")
            return True
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"Group deletion failed: {str(e)}")
            raise ServiceError(f"Failed to delete group: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def add_member(user: User, group_id: str, email: str, role: str = UserGroup.Role.MEMBER) -> UserGroup:
        """
        Add member to group.
        
        Args:
            user (User): User adding the member
            group_id (str): Group ID
            email (str): Email of user to add
            role (str): Role to assign
            
        Returns:
            UserGroup: Created membership
            
        Raises:
            ValidationError: If data is invalid
            ServiceError: If addition fails or no permission
        """
        try:
            group = GroupService.get_group(user, group_id)
            
            # Check permission
            if not group.can_user_manage_members(user):
                raise ServiceError("You don't have permission to manage members")
            
            # Find user to add
            try:
                user_to_add = User.objects.get(email=email)
            except User.DoesNotExist:
                raise ValidationError({'email': 'User with this email not found'})
            
            # Check if user is already a member
            if UserGroup.objects.filter(user=user_to_add, group=group).exists():
                raise ValidationError({'email': 'User is already a member of this group'})
            
            # Cannot add owner as member
            if user_to_add == group.owner:
                raise ValidationError({'email': 'Group owner is automatically a member'})
            
            # Validate role
            if role not in [choice[0] for choice in UserGroup.Role.choices]:
                raise ValidationError({'role': 'Invalid role'})
            
            # Create membership
            membership = UserGroup.objects.create(
                user=user_to_add,
                group=group,
                role=role,
                added_by=user
            )
            
            logger.info(f"Member added to group: {user_to_add.email} to {group.name} by {user.email}")
            return membership
            
        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Add member failed: {str(e)}")
            raise ServiceError(f"Failed to add member: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def remove_member(user: User, group_id: str, member_id: str) -> bool:
        """
        Remove member from group.
        
        Args:
            user (User): User removing the member
            group_id (str): Group ID
            member_id (str): Membership ID
            
        Returns:
            bool: True if removal successful
            
        Raises:
            ServiceError: If removal fails or no permission
        """
        try:
            group = GroupService.get_group(user, group_id)
            
            # Check permission
            if not group.can_user_manage_members(user):
                raise ServiceError("You don't have permission to manage members")
            
            # Get membership
            try:
                membership = UserGroup.objects.get(id=member_id, group=group)
            except UserGroup.DoesNotExist:
                raise ServiceError("Member not found")
            
            # Cannot remove group owner
            if membership.user == group.owner:
                raise ServiceError("Cannot remove group owner")
            
            member_email = membership.user.email
            membership.delete()
            
            logger.info(f"Member removed from group: {member_email} from {group.name} by {user.email}")
            return True
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"Remove member failed: {str(e)}")
            raise ServiceError(f"Failed to remove member: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def change_member_role(user: User, group_id: str, member_id: str, new_role: str) -> UserGroup:
        """
        Change member role in group.
        
        Args:
            user (User): User changing the role
            group_id (str): Group ID
            member_id (str): Membership ID
            new_role (str): New role to assign
            
        Returns:
            UserGroup: Updated membership
            
        Raises:
            ValidationError: If role is invalid
            ServiceError: If change fails or no permission
        """
        try:
            group = GroupService.get_group(user, group_id)
            
            # Check permission
            if not group.can_user_manage_members(user):
                raise ServiceError("You don't have permission to manage members")
            
            # Get membership
            try:
                membership = UserGroup.objects.get(id=member_id, group=group)
            except UserGroup.DoesNotExist:
                raise ServiceError("Member not found")
            
            # Cannot change owner role
            if membership.user == group.owner:
                raise ServiceError("Cannot change group owner role")
            
            # Validate role
            if new_role not in [choice[0] for choice in UserGroup.Role.choices]:
                raise ValidationError({'role': 'Invalid role'})
            
            membership.role = new_role
            membership.save()
            
            logger.info(f"Member role changed: {membership.user.email} to {new_role} in {group.name} by {user.email}")
            return membership
            
        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Change member role failed: {str(e)}")
            raise ServiceError(f"Failed to change member role: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def create_group(user: User, group_data: Dict) -> Group:
        """
        Create new group with user as owner.
        
        Args:
            user (User): User creating the group
            group_data (Dict): Group data
            
        Returns:
            Group: Created group
            
        Raises:
            ValidationError: If group data is invalid
            ServiceError: If group creation fails
        """
        try:
            # Validate group data
            if not group_data.get('name', '').strip():
                raise ValidationError({'name': 'Group name is required'})
            
            name = group_data['name'].strip()
            if len(name) > 100:
                raise ValidationError({'name': 'Group name too long (max 100 characters)'})
            
            # Check if user already has a group with this name
            if Group.objects.filter(owner=user, name=name).exists():
                raise ValidationError({'name': 'You already have a group with this name'})
            
            # Create group
            group = Group.objects.create(
                name=name,
                description=group_data.get('description', '').strip(),
                owner=user,
                is_personal=False
            )
            
            # Add owner as member (optional, since owner has implicit access)
            UserGroup.objects.create(
                user=user,
                group=group,
                role=UserGroup.Role.OWNER,
                joined_at=timezone.now()
            )
            
            logger.info(f"Group created: {name} by {user.email}")
            
            return group
            
        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Failed to create group: {str(e)}")
            raise ServiceError(f"Failed to create group: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def delete_group(user: User, group_id: str) -> bool:
        """
        Delete group.
        
        Args:
            user (User): User deleting the group
            group_id (str): Group ID
            
        Returns:
            bool: True if deletion successful
            
        Raises:
            ServiceError: If deletion fails or no permission
        """
        try:
            group = GroupService.get_group(user, group_id)
            
            # Only owner can delete group
            if group.owner != user:
                raise ServiceError("Only group owner can delete the group")
            
            # Cannot delete personal group
            if group.is_personal:
                raise ServiceError("Personal groups cannot be deleted")
            
            group_name = group.name
            group.delete()
            
            logger.info(f"Group deleted: {group_name} by {user.email}")
            return True
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"Group deletion failed: {str(e)}")
            raise ServiceError(f"Failed to delete group: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def add_member(user: User, group_id: str, email: str, role: str = UserGroup.Role.MEMBER) -> UserGroup:
        """
        Add member to group.
        
        Args:
            user (User): User adding the member
            group_id (str): Group ID
            email (str): Email of user to add
            role (str): Role to assign
            
        Returns:
            UserGroup: Created membership
            
        Raises:
            ValidationError: If data is invalid
            ServiceError: If addition fails or no permission
        """
        try:
            group = GroupService.get_group(user, group_id)
            
            # Check permission
            if not group.can_user_manage_members(user):
                raise ServiceError("You don't have permission to manage members")
            
            # Find user to add
            try:
                user_to_add = User.objects.get(email=email)
            except User.DoesNotExist:
                raise ValidationError({'email': 'User with this email not found'})
            
            # Check if user is already a member
            if UserGroup.objects.filter(user=user_to_add, group=group).exists():
                raise ValidationError({'email': 'User is already a member of this group'})
            
            # Cannot add owner as member
            if user_to_add == group.owner:
                raise ValidationError({'email': 'Group owner is automatically a member'})
            
            # Validate role
            if role not in [choice[0] for choice in UserGroup.Role.choices]:
                raise ValidationError({'role': 'Invalid role'})
            
            # Create membership
            membership = UserGroup.objects.create(
                user=user_to_add,
                group=group,
                role=role,
                added_by=user
            )
            
            logger.info(f"Member added to group: {user_to_add.email} to {group.name} by {user.email}")
            return membership
            
        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Add member failed: {str(e)}")
            raise ServiceError(f"Failed to add member: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def remove_member(user: User, group_id: str, member_id: str) -> bool:
        """
        Remove member from group.
        
        Args:
            user (User): User removing the member
            group_id (str): Group ID
            member_id (str): Membership ID
            
        Returns:
            bool: True if removal successful
            
        Raises:
            ServiceError: If removal fails or no permission
        """
        try:
            group = GroupService.get_group(user, group_id)
            
            # Check permission
            if not group.can_user_manage_members(user):
                raise ServiceError("You don't have permission to manage members")
            
            # Get membership
            try:
                membership = UserGroup.objects.get(id=member_id, group=group)
            except UserGroup.DoesNotExist:
                raise ServiceError("Member not found")
            
            # Cannot remove group owner
            if membership.user == group.owner:
                raise ServiceError("Cannot remove group owner")
            
            member_email = membership.user.email
            membership.delete()
            
            logger.info(f"Member removed from group: {member_email} from {group.name} by {user.email}")
            return True
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"Remove member failed: {str(e)}")
            raise ServiceError(f"Failed to remove member: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def change_member_role(user: User, group_id: str, member_id: str, new_role: str) -> UserGroup:
        """
        Change member role in group.
        
        Args:
            user (User): User changing the role
            group_id (str): Group ID
            member_id (str): Membership ID
            new_role (str): New role to assign
            
        Returns:
            UserGroup: Updated membership
            
        Raises:
            ValidationError: If role is invalid
            ServiceError: If change fails or no permission
        """
        try:
            group = GroupService.get_group(user, group_id)
            
            # Check permission
            if not group.can_user_manage_members(user):
                raise ServiceError("You don't have permission to manage members")
            
            # Get membership
            try:
                membership = UserGroup.objects.get(id=member_id, group=group)
            except UserGroup.DoesNotExist:
                raise ServiceError("Member not found")
            
            # Cannot change owner role
            if membership.user == group.owner:
                raise ServiceError("Cannot change group owner role")
            
            # Validate role
            if new_role not in [choice[0] for choice in UserGroup.Role.choices]:
                raise ValidationError({'role': 'Invalid role'})
            
            membership.role = new_role
            membership.save()
            
            logger.info(f"Member role changed: {membership.user.email} to {new_role} in {group.name} by {user.email}")
            return membership
            
        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Change member role failed: {str(e)}")
            raise ServiceError(f"Failed to change member role: {str(e)}")
    
    @staticmethod
    def _can_user_edit_group(user: User, group: Group) -> bool:
        """Check if user can edit group."""
        # Only owner can edit group
        return group.owner == user