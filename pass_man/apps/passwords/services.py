"""
Password services for Pass-Man Enterprise Password Management System.

This module contains business logic for password management including creation,
encryption, decryption, search, and access control.

Related Documentation:
- SRS.md: Section 4.1 Password Management
- ARCHITECTURE.md: Service Layer Pattern
- CODING_STANDARDS.md: Service Layer Best Practices
"""

import logging
import secrets
import string
import re
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count

from apps.core.exceptions import ServiceError, ValidationError
from apps.passwords.models import Password, PasswordHistory, PasswordAccessLog
from apps.passwords.validators import PasswordValidator, PasswordStrengthValidator
from apps.groups.models import Group, UserGroup
from apps.users.models import User

logger = logging.getLogger(__name__)


class PasswordService:
    """Service for password management operations."""
    
    @staticmethod
    @transaction.atomic
    def create_password(user: User, password_data: Dict) -> Password:
        """
        Create a new password entry.
        
        Args:
            user (User): User creating the password
            password_data (Dict): Password data
            
        Returns:
            Password: Created password instance
            
        Raises:
            ValidationError: If password data is invalid
            PermissionDenied: If user doesn't have permission
            ServiceError: If creation fails
        """
        try:
            # Validate password data
            validator = PasswordValidator(password_data)
            if not validator.is_valid():
                raise ValidationError(validator.errors)
            
            # Get and validate group
            group_id = password_data.get('group_id')
            if not group_id:
                raise ValidationError({'group_id': 'Group is required'})
            
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                raise ValidationError({'group_id': 'Group not found'})
            
            # Check permissions
            if not PasswordService._can_user_create_password(user, group):
                raise PermissionDenied("You don't have permission to create passwords in this group")
            
            # Create password instance
            password = Password(
                title=password_data['title'].strip(),
                username=password_data.get('username', '').strip(),
                url=password_data.get('url', '').strip(),
                notes=password_data.get('notes', '').strip(),
                group=group,
                created_by=user,
                priority=password_data.get('priority', Password.Priority.MEDIUM),
                custom_fields=password_data.get('custom_fields', {}),
                tags=password_data.get('tags', [])
            )
            
            # Set directory if provided
            # directory_id = password_data.get('directory_id')
            # if directory_id:
            #     from apps.directories.models import Directory
            #     try:
            #         directory = Directory.objects.get(id=directory_id, group=group)
            #         password.directory = directory
            #     except Directory.DoesNotExist:
            #         raise ValidationError({'directory_id': 'Directory not found in this group'})
            
            # Encrypt and set password
            plain_password = password_data.get('password', '')
            if not plain_password:
                raise ValidationError({'password': 'Password is required'})
            
            # Validate password strength
            strength_validator = PasswordStrengthValidator({'password': plain_password})
            if not strength_validator.is_valid():
                raise ValidationError(strength_validator.errors)
            
            password.set_password(plain_password)
            password.save()
            
            # Create history entry
            PasswordHistory.objects.create(
                password=password,
                change_type=PasswordHistory.ChangeType.CREATED,
                changed_by=user,
                change_summary=f"Password '{password.title}' created"
            )
            
            logger.info(f"Password created: {password.title} by {user.email}")
            return password
            
        except (ValidationError, PermissionDenied):
            raise
        except Exception as e:
            logger.error(f"Password creation failed: {str(e)}")
            raise ServiceError(f"Failed to create password: {str(e)}")
    
    @staticmethod
    def get_password(user: User, password_id: str, record_access: bool = True) -> Password:
        """
        Get password with decryption.
        
        Args:
            user (User): User requesting the password
            password_id (str): Password ID
            record_access (bool): Whether to record access
            
        Returns:
            Password: Password instance with decrypted password
            
        Raises:
            PermissionDenied: If user doesn't have permission
            ServiceError: If retrieval fails
        """
        try:
            password = Password.objects.get(id=password_id)
            
            # Check permissions
            if not PasswordService._can_user_view_password(user, password):
                raise PermissionDenied("You don't have permission to view this password")
            
            # Record access if requested
            if record_access:
                password.record_access(user)
            
            logger.info(f"Password accessed: {password.title} by {user.email}")
            return password
            
        except Password.DoesNotExist:
            raise ServiceError("Password not found")
        except PermissionDenied:
            raise
        except Exception as e:
            logger.error(f"Password retrieval failed: {str(e)}")
            raise ServiceError(f"Failed to retrieve password: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def update_password(user: User, password_id: str, password_data: Dict) -> Password:
        """
        Update password entry.
        
        Args:
            user (User): User updating the password
            password_id (str): Password ID
            password_data (Dict): Updated password data
            
        Returns:
            Password: Updated password instance
            
        Raises:
            ValidationError: If password data is invalid
            PermissionDenied: If user doesn't have permission
            ServiceError: If update fails
        """
        try:
            password = Password.objects.get(id=password_id)
            
            # Check permissions
            if not PasswordService._can_user_edit_password(user, password):
                raise PermissionDenied("You don't have permission to edit this password")
            
            # Validate password data
            validator = PasswordValidator(password_data, instance=password)
            if not validator.is_valid():
                raise ValidationError(validator.errors)
            
            # Store previous values for history
            previous_values = {
                'title': password.title,
                'username': password.username,
                'url': password.url,
                'notes': password.notes,
                'priority': password.priority,
                'custom_fields': password.custom_fields,
                'tags': password.tags,
            }
            
            # Update fields
            password.title = password_data.get('title', password.title).strip()
            password.username = password_data.get('username', password.username).strip()
            password.url = password_data.get('url', password.url).strip()
            password.notes = password_data.get('notes', password.notes).strip()
            password.priority = password_data.get('priority', password.priority)
            password.custom_fields = password_data.get('custom_fields', password.custom_fields)
            password.tags = password_data.get('tags', password.tags)
            
            # Update password if provided
            change_type = PasswordHistory.ChangeType.UPDATED
            if 'password' in password_data and password_data['password']:
                # Validate password strength
                strength_validator = PasswordStrengthValidator({'password': password_data['password']})
                if not strength_validator.is_valid():
                    raise ValidationError(strength_validator.errors)
                
                password.set_password(password_data['password'])
                change_type = PasswordHistory.ChangeType.PASSWORD_CHANGED
            
            password.save()
            
            # Create history entry
            PasswordHistory.objects.create(
                password=password,
                change_type=change_type,
                changed_by=user,
                previous_values=previous_values,
                change_summary=f"Password '{password.title}' updated"
            )
            
            logger.info(f"Password updated: {password.title} by {user.email}")
            return password
            
        except Password.DoesNotExist:
            raise ServiceError("Password not found")
        except (ValidationError, PermissionDenied):
            raise
        except Exception as e:
            logger.error(f"Password update failed: {str(e)}")
            raise ServiceError(f"Failed to update password: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def delete_password(user: User, password_id: str, permanent: bool = False) -> bool:
        """
        Delete password (soft or permanent).
        
        Args:
            user (User): User deleting the password
            password_id (str): Password ID
            permanent (bool): Whether to permanently delete
            
        Returns:
            bool: True if deletion successful
            
        Raises:
            PermissionDenied: If user doesn't have permission
            ServiceError: If deletion fails
        """
        try:
            if permanent:
                password = Password.all_objects.get(id=password_id)
            else:
                password = Password.objects.get(id=password_id)
            
            # Check permissions
            if not PasswordService._can_user_delete_password(user, password):
                raise PermissionDenied("You don't have permission to delete this password")
            
            if permanent:
                # Permanent deletion
                title = password.title
                password.delete()
                
                logger.info(f"Password permanently deleted: {title} by {user.email}")
            else:
                # Soft deletion
                password.soft_delete(user)
                
                # Create history entry
                PasswordHistory.objects.create(
                    password=password,
                    change_type=PasswordHistory.ChangeType.DELETED,
                    changed_by=user,
                    change_summary=f"Password '{password.title}' deleted"
                )
                
                logger.info(f"Password soft deleted: {password.title} by {user.email}")
            
            return True
            
        except Password.DoesNotExist:
            raise ServiceError("Password not found")
        except PermissionDenied:
            raise
        except Exception as e:
            logger.error(f"Password deletion failed: {str(e)}")
            raise ServiceError(f"Failed to delete password: {str(e)}")
    
    @staticmethod
    def search_passwords(user: User, query: str, filters: Dict = None) -> List[Password]:
        """
        Search passwords for user.
        
        Args:
            user (User): User performing search
            query (str): Search query
            filters (Dict): Additional filters
            
        Returns:
            List[Password]: List of matching passwords
        """
        try:
            # Get user's accessible groups
            user_groups = PasswordService._get_user_accessible_groups(user)
            
            # Base queryset
            queryset = Password.objects.filter(group__in=user_groups)
            
            # Apply search query
            if query:
                queryset = queryset.filter(
                    Q(title__icontains=query) |
                    Q(username__icontains=query) |
                    Q(url__icontains=query) |
                    Q(notes__icontains=query) |
                    Q(tags__icontains=query)
                )
            
            # Apply filters
            if filters:
                if 'group_id' in filters:
                    queryset = queryset.filter(group_id=filters['group_id'])
                
                if 'priority' in filters:
                    queryset = queryset.filter(priority=filters['priority'])
                
                if 'is_favorite' in filters:
                    queryset = queryset.filter(is_favorite=filters['is_favorite'])
                
                if 'tags' in filters:
                    for tag in filters['tags']:
                        queryset = queryset.filter(tags__icontains=tag)
                
                if 'expires_soon' in filters and filters['expires_soon']:
                    from datetime import timedelta
                    soon = timezone.now() + timedelta(days=30)
                    queryset = queryset.filter(expires_at__lte=soon, expires_at__isnull=False)
            
            return list(queryset.select_related('group', 'created_by'))
            
        except Exception as e:
            logger.error(f"Password search failed: {str(e)}")
            raise ServiceError(f"Search failed: {str(e)}")
    
    @staticmethod
    def get_user_passwords(user: User, group_id: str = None) -> List[Password]:
        """
        Get passwords accessible to user.
        
        Args:
            user (User): User requesting passwords
            group_id (str): Optional group filter
            
        Returns:
            List[Password]: List of accessible passwords
        """
        try:
            # Get user's accessible groups
            user_groups = PasswordService._get_user_accessible_groups(user)
            
            # Filter by specific group if provided
            if group_id:
                user_groups = user_groups.filter(id=group_id)
            
            # Get passwords
            passwords = Password.objects.filter(
                group__in=user_groups
            ).select_related('group', 'created_by').order_by('-updated_at')
            
            return list(passwords)
            
        except Exception as e:
            logger.error(f"Get user passwords failed: {str(e)}")
            raise ServiceError(f"Failed to get passwords: {str(e)}")
    
    @staticmethod
    def _get_user_accessible_groups(user: User):
        """Get groups accessible to user."""
        return Group.objects.filter(
            Q(owner=user) | Q(usergroup__user=user)
        ).distinct()
    
    @staticmethod
    def _can_user_create_password(user: User, group: Group) -> bool:
        """Check if user can create passwords in group."""
        # Group owner can always create
        if group.owner == user:
            return True
        
        # Check group membership and role
        membership = UserGroup.objects.filter(user=user, group=group).first()
        if not membership:
            return False
        
        # Members and admins can create passwords
        return membership.role in [UserGroup.Role.MEMBER, UserGroup.Role.ADMIN]
    
    @staticmethod
    def _can_user_view_password(user: User, password: Password) -> bool:
        """Check if user can view password."""
        # Password creator can always view
        if password.created_by == user:
            return True
        
        # Group owner can always view
        if password.group.owner == user:
            return True
        
        # Check group membership
        return UserGroup.objects.filter(user=user, group=password.group).exists()
    
    @staticmethod
    def _can_user_edit_password(user: User, password: Password) -> bool:
        """Check if user can edit password."""
        # Password creator can always edit
        if password.created_by == user:
            return True
        
        # Group owner can always edit
        if password.group.owner == user:
            return True
        
        # Check if user is group admin
        membership = UserGroup.objects.filter(user=user, group=password.group).first()
        return membership and membership.role == UserGroup.Role.ADMIN
    
    @staticmethod
    def _can_user_delete_password(user: User, password: Password) -> bool:
        """Check if user can delete password."""
        # Same permissions as edit
        return PasswordService._can_user_edit_password(user, password)


class PasswordGeneratorService:
    """Service for password generation."""
    
    @staticmethod
    def generate_password(
        length: int = 16,
        include_uppercase: bool = True,
        include_lowercase: bool = True,
        include_numbers: bool = True,
        include_symbols: bool = True,
        exclude_ambiguous: bool = True,
        custom_symbols: str = None
    ) -> str:
        """
        Generate secure password.
        
        Args:
            length (int): Password length
            include_uppercase (bool): Include uppercase letters
            include_lowercase (bool): Include lowercase letters
            include_numbers (bool): Include numbers
            include_symbols (bool): Include symbols
            exclude_ambiguous (bool): Exclude ambiguous characters
            custom_symbols (str): Custom symbol set
            
        Returns:
            str: Generated password
        """
        if length < 4:
            raise ValueError("Password length must be at least 4 characters")
        
        # Build character set
        chars = ""
        
        if include_lowercase:
            chars += string.ascii_lowercase
            if exclude_ambiguous:
                chars = chars.replace('l', '').replace('o', '')
        
        if include_uppercase:
            chars += string.ascii_uppercase
            if exclude_ambiguous:
                chars = chars.replace('I', '').replace('O', '')
        
        if include_numbers:
            chars += string.digits
            if exclude_ambiguous:
                chars = chars.replace('0', '').replace('1', '')
        
        if include_symbols:
            if custom_symbols:
                chars += custom_symbols
            else:
                symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
                if exclude_ambiguous:
                    symbols = symbols.replace('|', '').replace('`', '')
                chars += symbols
        
        if not chars:
            raise ValueError("At least one character type must be selected")
        
        # Generate password
        password = ''.join(secrets.choice(chars) for _ in range(length))
        
        # Ensure at least one character from each selected type
        required_chars = []
        if include_lowercase:
            required_chars.append(secrets.choice(string.ascii_lowercase))
        if include_uppercase:
            required_chars.append(secrets.choice(string.ascii_uppercase))
        if include_numbers:
            required_chars.append(secrets.choice(string.digits))
        if include_symbols:
            symbol_set = custom_symbols if custom_symbols else "!@#$%^&*"
            required_chars.append(secrets.choice(symbol_set))
        
        # Replace random positions with required characters
        if required_chars:
            password_list = list(password)
            for i, char in enumerate(required_chars):
                if i < len(password_list):
                    password_list[i] = char
            
            # Shuffle to randomize positions
            secrets.SystemRandom().shuffle(password_list)
            password = ''.join(password_list)
        
        return password
    
    @staticmethod
    def check_password_strength(password: str) -> Dict:
        """
        Check password strength.
        
        Args:
            password (str): Password to check
            
        Returns:
            Dict: Strength analysis
        """
        analysis = {
            'score': 0,
            'strength': 'Very Weak',
            'feedback': [],
            'length': len(password),
            'has_lowercase': bool(re.search(r'[a-z]', password)),
            'has_uppercase': bool(re.search(r'[A-Z]', password)),
            'has_numbers': bool(re.search(r'\d', password)),
            'has_symbols': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
        }
        
        # Length scoring
        if analysis['length'] >= 12:
            analysis['score'] += 25
        elif analysis['length'] >= 8:
            analysis['score'] += 15
        else:
            analysis['feedback'].append('Use at least 8 characters')
        
        # Character type scoring
        if analysis['has_lowercase']:
            analysis['score'] += 15
        else:
            analysis['feedback'].append('Add lowercase letters')
        
        if analysis['has_uppercase']:
            analysis['score'] += 15
        else:
            analysis['feedback'].append('Add uppercase letters')
        
        if analysis['has_numbers']:
            analysis['score'] += 15
        else:
            analysis['feedback'].append('Add numbers')
        
        if analysis['has_symbols']:
            analysis['score'] += 20
        else:
            analysis['feedback'].append('Add special characters')
        
        # Bonus for length
        if analysis['length'] >= 16:
            analysis['score'] += 10
        
        # Penalty for common patterns
        import re
        if re.search(r'(.)\1{2,}', password):  # Repeated characters
            analysis['score'] -= 10
            analysis['feedback'].append('Avoid repeated characters')
        
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):
            analysis['score'] -= 10
            analysis['feedback'].append('Avoid sequential numbers')
        
        # Determine strength
        if analysis['score'] >= 80:
            analysis['strength'] = 'Very Strong'
        elif analysis['score'] >= 60:
            analysis['strength'] = 'Strong'
        elif analysis['score'] >= 40:
            analysis['strength'] = 'Medium'
        elif analysis['score'] >= 20:
            analysis['strength'] = 'Weak'
        else:
            analysis['strength'] = 'Very Weak'
        
        return analysis