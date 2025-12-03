"""
User validators for Pass-Man Enterprise Password Management System.

This module contains validation logic for user-related operations including
registration, password validation, and profile updates.

Related Documentation:
- SRS.md: Section 3.1.1 User Registration Requirements
- CODING_STANDARDS.md: Input Validation Best Practices
"""

import re
from typing import Dict, List
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model

User = get_user_model()


class UserRegistrationValidator:
    """Validator for user registration data."""
    
    def __init__(self, data: Dict):
        """
        Initialize validator with registration data.
        
        Args:
            data (Dict): Registration data to validate
        """
        self.data = data
        self.errors = {}
    
    def is_valid(self) -> bool:
        """
        Validate all registration fields.
        
        Returns:
            bool: True if all validation passes
        """
        self._validate_email()
        self._validate_full_name()
        self._validate_password()
        self._validate_password_confirmation()
        
        return len(self.errors) == 0
    
    def _validate_email(self) -> None:
        """Validate email field."""
        email = self.data.get('email', '').strip().lower()
        
        if not email:
            self.errors['email'] = "Email is required"
            return
        
        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            self.errors['email'] = "Invalid email format"
            return
        
        # Check email length
        if len(email) > 254:  # RFC 5321 limit
            self.errors['email'] = "Email address too long"
            return
        
        # Check for business email domains (optional requirement)
        personal_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'protonmail.com'
        ]
        domain = email.split('@')[1] if '@' in email else ''
        
        # For enterprise version, we might want to restrict personal emails
        # This is configurable based on organization policy
        if hasattr(self, 'require_business_email') and self.require_business_email:
            if domain.lower() in personal_domains:
                self.errors['email'] = "Please use your business email address"
    
    def _validate_full_name(self) -> None:
        """Validate full name field."""
        full_name = self.data.get('full_name', '').strip()
        
        if not full_name:
            self.errors['full_name'] = "Full name is required"
            return
        
        # Check length
        if len(full_name) < 2:
            self.errors['full_name'] = "Full name must be at least 2 characters"
            return
        
        if len(full_name) > 150:
            self.errors['full_name'] = "Full name too long (max 150 characters)"
            return
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", full_name):
            self.errors['full_name'] = "Full name contains invalid characters"
            return
        
        # Check for reasonable format (at least first and last name)
        name_parts = full_name.split()
        if len(name_parts) < 2:
            self.errors['full_name'] = "Please provide both first and last name"
    
    def _validate_password(self) -> None:
        """Validate password field."""
        password = self.data.get('password', '')
        
        if not password:
            self.errors['password'] = "Password is required"
            return
        
        # Use Django's built-in password validation
        try:
            validate_password(password)
        except ValidationError as e:
            self.errors['password'] = list(e.messages)
            return
        
        # Additional custom password requirements
        password_validator = PasswordValidator({'password': password})
        if not password_validator.is_valid():
            self.errors.update(password_validator.errors)
    
    def _validate_password_confirmation(self) -> None:
        """Validate password confirmation field."""
        password = self.data.get('password', '')
        confirm_password = self.data.get('confirm_password', '')
        
        if not confirm_password:
            self.errors['confirm_password'] = "Password confirmation is required"
            return
        
        if password != confirm_password:
            self.errors['confirm_password'] = "Passwords do not match"


class PasswordValidator:
    """Validator for password requirements."""
    
    def __init__(self, data: Dict):
        """
        Initialize validator with password data.
        
        Args:
            data (Dict): Data containing password to validate
        """
        self.data = data
        self.errors = {}
    
    def is_valid(self) -> bool:
        """
        Validate password requirements.
        
        Returns:
            bool: True if password meets all requirements
        """
        self._validate_password_strength()
        return len(self.errors) == 0
    
    def _validate_password_strength(self) -> None:
        """Validate password strength requirements."""
        password = self.data.get('password', '')
        
        if not password:
            self.errors['password'] = "Password is required"
            return
        
        # Minimum length
        if len(password) < 8:
            self.errors['password'] = "Password must be at least 8 characters long"
            return
        
        # Maximum length (prevent DoS attacks)
        if len(password) > 128:
            self.errors['password'] = "Password too long (max 128 characters)"
            return
        
        # Character requirements
        requirements = []
        
        if not re.search(r'[a-z]', password):
            requirements.append("lowercase letter")
        
        if not re.search(r'[A-Z]', password):
            requirements.append("uppercase letter")
        
        if not re.search(r'\d', password):
            requirements.append("number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            requirements.append("special character")
        
        if requirements:
            self.errors['password'] = f"Password must contain at least one: {', '.join(requirements)}"
            return
        
        # Check for common weak patterns
        weak_patterns = [
            r'(.)\1{2,}',  # Three or more repeated characters
            r'(012|123|234|345|456|567|678|789|890)',  # Sequential numbers
            r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # Sequential letters
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, password.lower()):
                self.errors['password'] = "Password contains weak patterns (repeated or sequential characters)"
                return
        
        # Check against common passwords (basic check)
        common_passwords = [
            'password', '12345678', 'qwerty', 'abc123', 'password123',
            'admin', 'letmein', 'welcome', 'monkey', '1234567890'
        ]
        
        if password.lower() in common_passwords:
            self.errors['password'] = "Password is too common"


class ProfileUpdateValidator:
    """Validator for user profile updates."""
    
    def __init__(self, data: Dict, user=None):
        """
        Initialize validator with profile data.
        
        Args:
            data (Dict): Profile data to validate
            user: Current user instance (for email uniqueness check)
        """
        self.data = data
        self.user = user
        self.errors = {}
    
    def is_valid(self) -> bool:
        """
        Validate profile update data.
        
        Returns:
            bool: True if all validation passes
        """
        if 'email' in self.data:
            self._validate_email()
        
        if 'full_name' in self.data:
            self._validate_full_name()
        
        return len(self.errors) == 0
    
    def _validate_email(self) -> None:
        """Validate email field for profile update."""
        email = self.data.get('email', '').strip().lower()
        
        if not email:
            self.errors['email'] = "Email is required"
            return
        
        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            self.errors['email'] = "Invalid email format"
            return
        
        # Check email length
        if len(email) > 254:
            self.errors['email'] = "Email address too long"
            return
        
        # Check uniqueness (exclude current user)
        existing_user = User.objects.filter(email=email).first()
        if existing_user and existing_user != self.user:
            self.errors['email'] = "Email address already in use"
    
    def _validate_full_name(self) -> None:
        """Validate full name field for profile update."""
        full_name = self.data.get('full_name', '').strip()
        
        if not full_name:
            self.errors['full_name'] = "Full name is required"
            return
        
        # Check length
        if len(full_name) < 2:
            self.errors['full_name'] = "Full name must be at least 2 characters"
            return
        
        if len(full_name) > 150:
            self.errors['full_name'] = "Full name too long (max 150 characters)"
            return
        
        # Check for valid characters
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", full_name):
            self.errors['full_name'] = "Full name contains invalid characters"


class EmailValidator:
    """Validator specifically for email addresses."""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        Check if email is valid.
        
        Args:
            email (str): Email address to validate
            
        Returns:
            bool: True if email is valid
        """
        try:
            validate_email(email)
            return True
        except ValidationError:
            return False
    
    @staticmethod
    def get_email_errors(email: str) -> List[str]:
        """
        Get list of email validation errors.
        
        Args:
            email (str): Email address to validate
            
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        
        if not email:
            errors.append("Email is required")
            return errors
        
        email = email.strip()
        
        if len(email) > 254:
            errors.append("Email address too long")
        
        try:
            validate_email(email)
        except ValidationError:
            errors.append("Invalid email format")
        
        return errors


class PasswordStrengthValidator:
    """Validator for password strength assessment."""
    
    @staticmethod
    def calculate_strength(password: str) -> Dict:
        """
        Calculate password strength score and feedback.
        
        Args:
            password (str): Password to assess
            
        Returns:
            Dict: Contains score (0-100) and feedback list
        """
        if not password:
            return {'score': 0, 'feedback': ['Password is required']}
        
        score = 0
        feedback = []
        
        # Length scoring
        length = len(password)
        if length >= 8:
            score += 20
        elif length >= 6:
            score += 10
            feedback.append("Password should be at least 8 characters")
        else:
            feedback.append("Password is too short (minimum 8 characters)")
        
        # Character variety scoring
        has_lower = bool(re.search(r'[a-z]', password))
        has_upper = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        char_variety = sum([has_lower, has_upper, has_digit, has_special])
        score += char_variety * 15
        
        if not has_lower:
            feedback.append("Add lowercase letters")
        if not has_upper:
            feedback.append("Add uppercase letters")
        if not has_digit:
            feedback.append("Add numbers")
        if not has_special:
            feedback.append("Add special characters")
        
        # Bonus for length
        if length >= 12:
            score += 10
        if length >= 16:
            score += 10
        
        # Penalty for common patterns
        if re.search(r'(.)\1{2,}', password):
            score -= 10
            feedback.append("Avoid repeated characters")
        
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):
            score -= 15
            feedback.append("Avoid sequential numbers")
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        # Determine strength level
        if score >= 80:
            strength = "Very Strong"
        elif score >= 60:
            strength = "Strong"
        elif score >= 40:
            strength = "Medium"
        elif score >= 20:
            strength = "Weak"
        else:
            strength = "Very Weak"
        
        return {
            'score': score,
            'strength': strength,
            'feedback': feedback
        }