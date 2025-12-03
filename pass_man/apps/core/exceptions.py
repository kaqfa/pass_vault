"""
Custom exceptions for Pass-Man Enterprise Password Management System.

This module defines custom exception classes used throughout the application
for better error handling and user experience.

Related Documentation:
- CODING_STANDARDS.md: Error Handling Best Practices
- ARCHITECTURE.md: Exception Handling Strategy
"""

from typing import Dict, Any, Optional


class PassManException(Exception):
    """Base exception class for Pass-Man application."""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict] = None):
        """
        Initialize exception with message and optional details.
        
        Args:
            message (str): Human-readable error message
            code (str, optional): Error code for programmatic handling
            details (Dict, optional): Additional error details
        """
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            'error': self.message,
            'code': self.code,
            'details': self.details
        }


class ValidationError(PassManException):
    """Exception raised when data validation fails."""
    
    def __init__(self, errors: Dict[str, Any], message: str = "Validation failed"):
        """
        Initialize validation error with field errors.
        
        Args:
            errors (Dict): Dictionary of field validation errors
            message (str): General validation error message
        """
        super().__init__(message, code="VALIDATION_ERROR", details=errors)
        self.errors = errors


class ServiceError(PassManException):
    """Exception raised when a service operation fails."""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict] = None):
        """
        Initialize service error.
        
        Args:
            message (str): Error message
            code (str, optional): Specific error code
            details (Dict, optional): Additional error details
        """
        super().__init__(message, code or "SERVICE_ERROR", details)


class AuthenticationError(PassManException):
    """Exception raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", code: str = "AUTH_ERROR"):
        """
        Initialize authentication error.
        
        Args:
            message (str): Error message
            code (str): Error code
        """
        super().__init__(message, code)


class AuthorizationError(PassManException):
    """Exception raised when authorization fails."""
    
    def __init__(self, message: str = "Access denied", code: str = "ACCESS_DENIED"):
        """
        Initialize authorization error.
        
        Args:
            message (str): Error message
            code (str): Error code
        """
        super().__init__(message, code)


class EncryptionError(PassManException):
    """Exception raised when encryption/decryption operations fail."""
    
    def __init__(self, message: str, operation: str = "unknown"):
        """
        Initialize encryption error.
        
        Args:
            message (str): Error message
            operation (str): The operation that failed (encrypt/decrypt)
        """
        super().__init__(
            message, 
            code="ENCRYPTION_ERROR",
            details={'operation': operation}
        )


class GroupError(PassManException):
    """Exception raised for group-related operations."""
    
    def __init__(self, message: str, group_id: Optional[str] = None):
        """
        Initialize group error.
        
        Args:
            message (str): Error message
            group_id (str, optional): ID of the group involved
        """
        details = {'group_id': group_id} if group_id else {}
        super().__init__(message, code="GROUP_ERROR", details=details)


class PasswordError(PassManException):
    """Exception raised for password-related operations."""
    
    def __init__(self, message: str, password_id: Optional[str] = None):
        """
        Initialize password error.
        
        Args:
            message (str): Error message
            password_id (str, optional): ID of the password involved
        """
        details = {'password_id': password_id} if password_id else {}
        super().__init__(message, code="PASSWORD_ERROR", details=details)


class RateLimitError(PassManException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        """
        Initialize rate limit error.
        
        Args:
            message (str): Error message
            retry_after (int, optional): Seconds to wait before retrying
        """
        details = {'retry_after': retry_after} if retry_after else {}
        super().__init__(message, code="RATE_LIMIT_ERROR", details=details)


class ExternalServiceError(PassManException):
    """Exception raised when external service calls fail."""
    
    def __init__(self, message: str, service: str, status_code: Optional[int] = None):
        """
        Initialize external service error.
        
        Args:
            message (str): Error message
            service (str): Name of the external service
            status_code (int, optional): HTTP status code if applicable
        """
        details = {
            'service': service,
            'status_code': status_code
        }
        super().__init__(message, code="EXTERNAL_SERVICE_ERROR", details=details)


class ConfigurationError(PassManException):
    """Exception raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, setting: Optional[str] = None):
        """
        Initialize configuration error.
        
        Args:
            message (str): Error message
            setting (str, optional): Name of the problematic setting
        """
        details = {'setting': setting} if setting else {}
        super().__init__(message, code="CONFIGURATION_ERROR", details=details)


class DataIntegrityError(PassManException):
    """Exception raised when data integrity is compromised."""
    
    def __init__(self, message: str, model: Optional[str] = None, field: Optional[str] = None):
        """
        Initialize data integrity error.
        
        Args:
            message (str): Error message
            model (str, optional): Name of the model involved
            field (str, optional): Name of the field involved
        """
        details = {}
        if model:
            details['model'] = model
        if field:
            details['field'] = field
        
        super().__init__(message, code="DATA_INTEGRITY_ERROR", details=details)


class QuotaExceededError(PassManException):
    """Exception raised when user quotas are exceeded."""
    
    def __init__(self, message: str, quota_type: str, current: int, limit: int):
        """
        Initialize quota exceeded error.
        
        Args:
            message (str): Error message
            quota_type (str): Type of quota exceeded
            current (int): Current usage
            limit (int): Quota limit
        """
        details = {
            'quota_type': quota_type,
            'current': current,
            'limit': limit
        }
        super().__init__(message, code="QUOTA_EXCEEDED", details=details)


class MaintenanceError(PassManException):
    """Exception raised when system is under maintenance."""
    
    def __init__(self, message: str = "System is under maintenance", estimated_duration: Optional[int] = None):
        """
        Initialize maintenance error.
        
        Args:
            message (str): Error message
            estimated_duration (int, optional): Estimated maintenance duration in minutes
        """
        details = {'estimated_duration': estimated_duration} if estimated_duration else {}
        super().__init__(message, code="MAINTENANCE_ERROR", details=details)