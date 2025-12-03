"""
Custom user managers for Pass-Man Enterprise Password Management System.

This module contains custom user managers that handle email-based authentication
without requiring a username field.

Related Documentation:
- SRS.md: Section 3.1 User Management
- ARCHITECTURE.md: Database Design - User Model
- CODING_STANDARDS.md: Model Design Best Practices
"""

from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class UserManager(BaseUserManager):
    """
    Custom user manager for email-based authentication.
    
    This manager handles user creation without requiring a username field,
    using email as the primary identifier instead.
    """
    
    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        
        Args:
            email (str): User's email address
            password (str): User's password
            **extra_fields: Additional fields for the user
            
        Returns:
            User: Created user instance
            
        Raises:
            ValueError: If email is not provided or invalid
        """
        if not email:
            raise ValueError('The Email field must be set')
        
        # Normalize and validate email
        email = self.normalize_email(email)
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError('Invalid email address')
        
        # Create user instance
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        return user
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        
        Args:
            email (str): User's email address
            password (str, optional): User's password
            **extra_fields: Additional fields for the user
            
        Returns:
            User: Created user instance
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', False)  # Inactive until email verification
        extra_fields.setdefault('email_verified', False)
        
        return self._create_user(email, password, **extra_fields)
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        
        Args:
            email (str): Superuser's email address
            password (str, optional): Superuser's password
            **extra_fields: Additional fields for the superuser
            
        Returns:
            User: Created superuser instance
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)  # Superusers are active by default
        extra_fields.setdefault('email_verified', True)  # Superusers are verified by default
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self._create_user(email, password, **extra_fields)
    
    def get_by_natural_key(self, email):
        """
        Get user by email (natural key).
        
        Args:
            email (str): User's email address
            
        Returns:
            User: User instance with the given email
        """
        return self.get(**{self.model.USERNAME_FIELD: email})


class ActiveUserManager(UserManager):
    """
    Manager that returns only active (non-banned) users.
    
    This manager filters out banned users from querysets by default.
    """
    
    def get_queryset(self):
        """Return queryset with only active (non-banned) users."""
        return super().get_queryset().filter(banned=False)


class AllUserManager(UserManager):
    """
    Manager that returns all users including banned ones.
    
    This manager is useful for admin operations where you need
    to access all users regardless of their status.
    """
    
    def get_queryset(self):
        """Return queryset with all users including banned ones."""
        return super().get_queryset()