"""
Django admin configuration for User model.

This module configures the Django admin interface for user management
with appropriate fields, filters, and permissions.

Related Documentation:
- CODING_STANDARDS.md: Admin Configuration Best Practices
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""
    
    # List display
    list_display = [
        'email',
        'full_name', 
        'email_verified',
        'is_active',
        'banned',
        'date_joined'
    ]
    
    # List filters
    list_filter = [
        'email_verified',
        'is_active',
        'banned',
        'is_staff',
        'date_joined'
    ]
    
    # Search fields
    search_fields = ['email', 'full_name']
    
    # Ordering
    ordering = ['full_name', 'email']
    
    # Read-only fields
    readonly_fields = [
        'id',
        'date_joined',
        'last_login',
        'last_password_change',
        'banned_at'
    ]
    
    # Fieldsets for add/edit forms
    fieldsets = (
        ('Basic Information', {
            'fields': ('email', 'full_name')
        }),
        ('Authentication', {
            'fields': ('password',)
        }),
        ('Email Verification', {
            'fields': ('email_verified', 'email_verification_token'),
            'classes': ('collapse',)
        }),
        ('Password Reset', {
            'fields': ('password_reset_token', 'password_reset_expires'),
            'classes': ('collapse',)
        }),
        ('Account Status', {
            'fields': ('is_active', 'banned', 'banned_at', 'banned_reason')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login', 'last_password_change'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id',),
            'classes': ('collapse',)
        })
    )
    
    # Add fieldsets (for creating new users)
    add_fieldsets = (
        ('Basic Information', {
            'fields': ('email', 'full_name', 'password1', 'password2')
        }),
        ('Account Status', {
            'fields': ('is_active', 'email_verified')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser'),
            'classes': ('collapse',)
        })
    )
    
    # Actions
    actions = ['ban_users', 'unban_users', 'verify_emails']
    
    def ban_users(self, request, queryset):
        """Ban selected users."""
        count = 0
        for user in queryset:
            if not user.banned:
                user.ban_user(reason="Banned by admin", banned_by=request.user)
                count += 1
        
        self.message_user(
            request,
            f"Successfully banned {count} user(s)."
        )
    ban_users.short_description = "Ban selected users"
    
    def unban_users(self, request, queryset):
        """Unban selected users."""
        count = 0
        for user in queryset:
            if user.banned:
                user.unban_user()
                count += 1
        
        self.message_user(
            request,
            f"Successfully unbanned {count} user(s)."
        )
    unban_users.short_description = "Unban selected users"
    
    def verify_emails(self, request, queryset):
        """Verify emails for selected users."""
        count = 0
        for user in queryset:
            if not user.email_verified:
                user.verify_email()
                count += 1
        
        self.message_user(
            request,
            f"Successfully verified {count} email(s)."
        )
    verify_emails.short_description = "Verify emails for selected users"
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related()
    
    def has_delete_permission(self, request, obj=None):
        """Restrict user deletion to superusers only."""
        return request.user.is_superuser
    
    def save_model(self, request, obj, form, change):
        """Custom save logic for admin."""
        if not change:  # Creating new user
            # Set email as verified if created by admin
            obj.email_verified = True
            obj.is_active = True
        
        super().save_model(request, obj, form, change)