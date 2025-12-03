"""
Password validators for Pass-Man Enterprise Password Management System.

This module contains validation logic for password creation, updates,
and password strength validation.

Related Documentation:
- SRS.md: Section 4.1 Password Management
- CODING_STANDARDS.md: Validation Best Practices
"""

import re
from typing import Dict, List, Optional, Any
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError


class BaseValidator:
    """Base validator class with common validation methods."""
    
    def __init__(self, data: Dict, instance=None):
        self.data = data
        self.instance = instance
        self.errors = {}
    
    def is_valid(self) -> bool:
        """Check if data is valid."""
        self.errors = {}
        self.validate()
        return len(self.errors) == 0
    
    def validate(self):
        """Override in subclasses."""
        pass
    
    def add_error(self, field: str, message: str):
        """Add validation error."""
        if field not in self.errors:
            self.errors[field] = []
        self.errors[field].append(message)


class PasswordValidator(BaseValidator):
    """Validator for password creation and updates."""
    
    def validate(self):
        """Validate password data."""
        self._validate_title()
        self._validate_username()
        self._validate_url()
        self._validate_notes()
        self._validate_priority()
        self._validate_custom_fields()
        self._validate_tags()
        self._validate_expires_at()
    
    def _validate_title(self):
        """Validate password title."""
        title = self.data.get('title', '').strip()
        
        if not title:
            self.add_error('title', 'Title is required')
            return
        
        if len(title) < 2:
            self.add_error('title', 'Title must be at least 2 characters long')
        
        if len(title) > 255:
            self.add_error('title', 'Title cannot exceed 255 characters')
        
        # Check for invalid characters
        if re.search(r'[<>"\']', title):
            self.add_error('title', 'Title contains invalid characters')
    
    def _validate_username(self):
        """Validate username field."""
        username = self.data.get('username', '').strip()
        
        if username and len(username) > 255:
            self.add_error('username', 'Username cannot exceed 255 characters')
    
    def _validate_url(self):
        """Validate URL field."""
        url = self.data.get('url', '').strip()
        
        if url:
            if len(url) > 2000:
                self.add_error('url', 'URL cannot exceed 2000 characters')
            
            # Basic URL validation
            url_validator = URLValidator()
            try:
                url_validator(url)
            except DjangoValidationError:
                self.add_error('url', 'Enter a valid URL')
    
    def _validate_notes(self):
        """Validate notes field."""
        notes = self.data.get('notes', '').strip()
        
        if notes and len(notes) > 5000:
            self.add_error('notes', 'Notes cannot exceed 5000 characters')
    
    def _validate_priority(self):
        """Validate priority field."""
        priority = self.data.get('priority')
        
        if priority:
            from apps.passwords.models import Password
            valid_priorities = [choice[0] for choice in Password.Priority.choices]
            if priority not in valid_priorities:
                self.add_error('priority', f'Priority must be one of: {", ".join(valid_priorities)}')
    
    def _validate_custom_fields(self):
        """Validate custom fields."""
        custom_fields = self.data.get('custom_fields')
        
        if custom_fields is not None:
            if not isinstance(custom_fields, dict):
                self.add_error('custom_fields', 'Custom fields must be a valid JSON object')
                return
            
            # Validate field names and values
            for field_name, field_value in custom_fields.items():
                if not isinstance(field_name, str):
                    self.add_error('custom_fields', 'Field names must be strings')
                    continue
                
                if len(field_name) > 100:
                    self.add_error('custom_fields', f'Field name "{field_name}" is too long (max 100 characters)')
                
                if not isinstance(field_value, (str, int, float, bool)):
                    self.add_error('custom_fields', f'Field "{field_name}" has invalid value type')
                
                if isinstance(field_value, str) and len(field_value) > 1000:
                    self.add_error('custom_fields', f'Field "{field_name}" value is too long (max 1000 characters)')
    
    def _validate_tags(self):
        """Validate tags field."""
        tags = self.data.get('tags')
        
        if tags is not None:
            if not isinstance(tags, list):
                self.add_error('tags', 'Tags must be a list')
                return
            
            if len(tags) > 20:
                self.add_error('tags', 'Maximum 20 tags allowed')
                return
            
            for tag in tags:
                if not isinstance(tag, str):
                    self.add_error('tags', 'All tags must be strings')
                    continue
                
                tag = tag.strip()
                if not tag:
                    self.add_error('tags', 'Empty tags are not allowed')
                    continue
                
                if len(tag) > 50:
                    self.add_error('tags', f'Tag "{tag}" is too long (max 50 characters)')
                
                if re.search(r'[<>"\']', tag):
                    self.add_error('tags', f'Tag "{tag}" contains invalid characters')
    
    def _validate_expires_at(self):
        """Validate expiration date."""
        expires_at = self.data.get('expires_at')
        
        if expires_at:
            from django.utils import timezone
            from datetime import datetime
            
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except ValueError:
                    self.add_error('expires_at', 'Invalid date format')
                    return
            
            if expires_at <= timezone.now():
                self.add_error('expires_at', 'Expiration date must be in the future')


class PasswordStrengthValidator(BaseValidator):
    """Validator for password strength."""
    
    def validate(self):
        """Validate password strength."""
        password = self.data.get('password', '')
        
        if not password:
            self.add_error('password', 'Password is required')
            return
        
        self._validate_length(password)
        self._validate_complexity(password)
        self._validate_patterns(password)
        self._validate_common_passwords(password)
    
    def _validate_length(self, password: str):
        """Validate password length."""
        if len(password) < 8:
            self.add_error('password', 'Password must be at least 8 characters long')
        
        if len(password) > 128:
            self.add_error('password', 'Password cannot exceed 128 characters')
    
    def _validate_complexity(self, password: str):
        """Validate password complexity."""
        has_lowercase = bool(re.search(r'[a-z]', password))
        has_uppercase = bool(re.search(r'[A-Z]', password))
        has_numbers = bool(re.search(r'\d', password))
        has_symbols = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        complexity_count = sum([has_lowercase, has_uppercase, has_numbers, has_symbols])
        
        if complexity_count < 3:
            self.add_error('password', 'Password must contain at least 3 of: lowercase, uppercase, numbers, symbols')
        
        # Additional requirements for strong passwords
        if len(password) >= 12:
            if not has_symbols:
                self.add_error('password', 'Passwords 12+ characters should include special characters')
    
    def _validate_patterns(self, password: str):
        """Validate against weak patterns."""
        # Check for repeated characters
        if re.search(r'(.)\1{2,}', password):
            self.add_error('password', 'Password contains weak patterns (repeated characters)')
        
        # Check for sequential characters
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):
            self.add_error('password', 'Password contains weak patterns (sequential numbers)')
        
        if re.search(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):
            self.add_error('password', 'Password contains weak patterns (sequential letters)')
        
        # Check for keyboard patterns
        keyboard_patterns = [
            'qwerty', 'asdf', 'zxcv', '1234', 'qwer', 'asdfg', 'zxcvb'
        ]
        
        for pattern in keyboard_patterns:
            if pattern in password.lower():
                self.add_error('password', 'Password contains weak patterns (keyboard sequences)')
                break
    
    def _validate_common_passwords(self, password: str):
        """Validate against common passwords."""
        # List of most common passwords
        common_passwords = [
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey',
            '1234567890', 'password1', '123123', 'qwerty123',
            'iloveyou', 'princess', 'admin123', 'welcome123'
        ]
        
        if password.lower() in common_passwords:
            self.add_error('password', 'Password is too common and easily guessable')
        
        # Check for variations with numbers/symbols
        base_password = re.sub(r'[0-9!@#$%^&*(),.?":{}|<>]', '', password.lower())
        if base_password in common_passwords:
            self.add_error('password', 'Password is based on a common password')


class PasswordSearchValidator(BaseValidator):
    """Validator for password search parameters."""
    
    def validate(self):
        """Validate search parameters."""
        self._validate_query()
        self._validate_filters()
    
    def _validate_query(self):
        """Validate search query."""
        query = self.data.get('query', '').strip()
        
        if query and len(query) > 255:
            self.add_error('query', 'Search query cannot exceed 255 characters')
        
        # Check for potentially dangerous characters
        if query and re.search(r'[<>"\']', query):
            self.add_error('query', 'Search query contains invalid characters')
    
    def _validate_filters(self):
        """Validate search filters."""
        filters = self.data.get('filters', {})
        
        if not isinstance(filters, dict):
            self.add_error('filters', 'Filters must be a valid object')
            return
        
        # Validate group_id filter
        group_id = filters.get('group_id')
        if group_id:
            try:
                import uuid
                uuid.UUID(str(group_id))
            except ValueError:
                self.add_error('filters', 'Invalid group_id format')
        
        # Validate priority filter
        priority = filters.get('priority')
        if priority:
            from apps.passwords.models import Password
            valid_priorities = [choice[0] for choice in Password.Priority.choices]
            if priority not in valid_priorities:
                self.add_error('filters', f'Invalid priority. Must be one of: {", ".join(valid_priorities)}')
        
        # Validate tags filter
        tags = filters.get('tags')
        if tags:
            if not isinstance(tags, list):
                self.add_error('filters', 'Tags filter must be a list')
            else:
                for tag in tags:
                    if not isinstance(tag, str):
                        self.add_error('filters', 'All tag filters must be strings')
                        break
                    if len(tag) > 50:
                        self.add_error('filters', 'Tag filter too long (max 50 characters)')
                        break


class PasswordGeneratorValidator(BaseValidator):
    """Validator for password generator parameters."""
    
    def validate(self):
        """Validate generator parameters."""
        self._validate_length()
        self._validate_character_types()
        self._validate_custom_symbols()
    
    def _validate_length(self):
        """Validate password length."""
        length = self.data.get('length', 16)
        
        if not isinstance(length, int):
            self.add_error('length', 'Length must be an integer')
            return
        
        if length < 4:
            self.add_error('length', 'Password length must be at least 4 characters')
        
        if length > 128:
            self.add_error('length', 'Password length cannot exceed 128 characters')
    
    def _validate_character_types(self):
        """Validate character type selections."""
        include_uppercase = self.data.get('include_uppercase', True)
        include_lowercase = self.data.get('include_lowercase', True)
        include_numbers = self.data.get('include_numbers', True)
        include_symbols = self.data.get('include_symbols', True)
        
        # At least one character type must be selected
        if not any([include_uppercase, include_lowercase, include_numbers, include_symbols]):
            self.add_error('character_types', 'At least one character type must be selected')
    
    def _validate_custom_symbols(self):
        """Validate custom symbols."""
        custom_symbols = self.data.get('custom_symbols')
        
        if custom_symbols is not None:
            if not isinstance(custom_symbols, str):
                self.add_error('custom_symbols', 'Custom symbols must be a string')
                return
            
            if len(custom_symbols) > 100:
                self.add_error('custom_symbols', 'Custom symbols cannot exceed 100 characters')
            
            # Check for potentially problematic characters
            if re.search(r'[<>"\']', custom_symbols):
                self.add_error('custom_symbols', 'Custom symbols contain invalid characters')