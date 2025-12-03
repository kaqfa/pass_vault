"""
Django admin configuration for Password models.

This module configures the Django admin interface for password management
with appropriate fields, filters, and security considerations.

Related Documentation:
- CODING_STANDARDS.md: Admin Configuration Best Practices
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count

from .models import Password, PasswordHistory, PasswordAccessLog


@admin.register(Password)
class PasswordAdmin(admin.ModelAdmin):
    """Admin configuration for Password model."""
    
    # List display
    list_display = [
        'title',
        'username',
        'group_link',
        'created_by_link',
        'priority',
        'is_favorite',
        'access_count',
        'last_accessed',
        'is_deleted',
        'created_at'
    ]
    
    # List filters
    list_filter = [
        'priority',
        'is_favorite',
        'is_deleted',
        'group',
        'created_by',
        'created_at',
        'last_accessed'
    ]
    
    # Search fields
    search_fields = ['title', 'username', 'url', 'notes', 'tags']
    
    # Ordering
    ordering = ['-created_at']
    
    # Read-only fields
    readonly_fields = [
        'id',
        'encrypted_password',
        'created_at',
        'updated_at',
        'last_accessed',
        'access_count',
        'deleted_at',
        'deleted_by'
    ]
    
    # Fieldsets
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'username', 'url', 'notes')
        }),
        ('Organization', {
            'fields': ('group', 'directory', 'priority', 'tags', 'is_favorite')
        }),
        ('Custom Fields', {
            'fields': ('custom_fields',),
            'classes': ('collapse',)
        }),
        ('Security', {
            'fields': ('encrypted_password', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('created_by', 'last_accessed', 'access_count'),
            'classes': ('collapse',)
        }),
        ('Soft Delete', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    # Filters
    date_hierarchy = 'created_at'
    
    # Actions
    actions = ['mark_as_favorite', 'unmark_as_favorite', 'soft_delete_passwords', 'restore_passwords']
    
    def group_link(self, obj):
        """Link to group admin page."""
        if obj.group:
            url = reverse('admin:groups_group_change', args=[obj.group.pk])
            return format_html('<a href="{}">{}</a>', url, obj.group.name)
        return '-'
    group_link.short_description = 'Group'
    
    def created_by_link(self, obj):
        """Link to user admin page."""
        if obj.created_by:
            url = reverse('admin:users_user_change', args=[obj.created_by.pk])
            return format_html('<a href="{}">{}</a>', url, obj.created_by.email)
        return '-'
    created_by_link.short_description = 'Created By'
    
    def get_queryset(self, request):
        """Override queryset to include deleted passwords for superusers."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return Password.all_objects.select_related('group', 'created_by', 'directory')
        return qs.select_related('group', 'created_by', 'directory')
    
    def mark_as_favorite(self, request, queryset):
        """Mark selected passwords as favorite."""
        updated = queryset.update(is_favorite=True)
        self.message_user(request, f'{updated} passwords marked as favorite.')
    mark_as_favorite.short_description = "Mark selected passwords as favorite"
    
    def unmark_as_favorite(self, request, queryset):
        """Unmark selected passwords as favorite."""
        updated = queryset.update(is_favorite=False)
        self.message_user(request, f'{updated} passwords unmarked as favorite.')
    unmark_as_favorite.short_description = "Unmark selected passwords as favorite"
    
    def soft_delete_passwords(self, request, queryset):
        """Soft delete selected passwords."""
        updated = 0
        for password in queryset:
            if not password.is_deleted:
                password.soft_delete(request.user)
                updated += 1
        self.message_user(request, f'{updated} passwords soft deleted.')
    soft_delete_passwords.short_description = "Soft delete selected passwords"
    
    def restore_passwords(self, request, queryset):
        """Restore soft-deleted passwords."""
        updated = 0
        for password in queryset:
            if password.is_deleted:
                password.restore()
                updated += 1
        self.message_user(request, f'{updated} passwords restored.')
    restore_passwords.short_description = "Restore selected passwords"
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can permanently delete passwords."""
        return request.user.is_superuser


@admin.register(PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for PasswordHistory model."""
    
    # List display
    list_display = [
        'password_link',
        'change_type',
        'changed_by_link',
        'change_summary',
        'created_at'
    ]
    
    # List filters
    list_filter = [
        'change_type',
        'changed_by',
        'created_at'
    ]
    
    # Search fields
    search_fields = ['password__title', 'change_summary', 'changed_by__email']
    
    # Ordering
    ordering = ['-created_at']
    
    # Read-only fields (history should not be editable)
    readonly_fields = [
        'id',
        'password',
        'change_type',
        'changed_by',
        'previous_values',
        'change_summary',
        'created_at',
        'updated_at'
    ]
    
    # Fieldsets
    fieldsets = (
        ('Change Information', {
            'fields': ('password', 'change_type', 'changed_by', 'change_summary')
        }),
        ('Previous Values', {
            'fields': ('previous_values',),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    # Filters
    date_hierarchy = 'created_at'
    
    def password_link(self, obj):
        """Link to password admin page."""
        if obj.password:
            url = reverse('admin:passwords_password_change', args=[obj.password.pk])
            return format_html('<a href="{}">{}</a>', url, obj.password.title)
        return '-'
    password_link.short_description = 'Password'
    
    def changed_by_link(self, obj):
        """Link to user admin page."""
        if obj.changed_by:
            url = reverse('admin:users_user_change', args=[obj.changed_by.pk])
            return format_html('<a href="{}">{}</a>', url, obj.changed_by.email)
        return '-'
    changed_by_link.short_description = 'Changed By'
    
    def has_add_permission(self, request):
        """History entries should not be manually created."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """History entries should not be editable."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete history entries."""
        return request.user.is_superuser


@admin.register(PasswordAccessLog)
class PasswordAccessLogAdmin(admin.ModelAdmin):
    """Admin configuration for PasswordAccessLog model."""
    
    # List display
    list_display = [
        'password_link',
        'user_link',
        'accessed_at',
        'ip_address',
        'user_agent_short'
    ]
    
    # List filters
    list_filter = [
        'accessed_at',
        'user',
        'password__group'
    ]
    
    # Search fields
    search_fields = ['password__title', 'user__email', 'ip_address']
    
    # Ordering
    ordering = ['-accessed_at']
    
    # Read-only fields (access logs should not be editable)
    readonly_fields = [
        'id',
        'password',
        'user',
        'accessed_at',
        'ip_address',
        'user_agent',
        'created_at',
        'updated_at'
    ]
    
    # Fieldsets
    fieldsets = (
        ('Access Information', {
            'fields': ('password', 'user', 'accessed_at')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    # Filters
    date_hierarchy = 'accessed_at'
    
    def password_link(self, obj):
        """Link to password admin page."""
        if obj.password:
            url = reverse('admin:passwords_password_change', args=[obj.password.pk])
            return format_html('<a href="{}">{}</a>', url, obj.password.title)
        return '-'
    password_link.short_description = 'Password'
    
    def user_link(self, obj):
        """Link to user admin page."""
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return '-'
    user_link.short_description = 'User'
    
    def user_agent_short(self, obj):
        """Shortened user agent string."""
        if obj.user_agent:
            return obj.user_agent[:50] + '...' if len(obj.user_agent) > 50 else obj.user_agent
        return '-'
    user_agent_short.short_description = 'User Agent'
    
    def has_add_permission(self, request):
        """Access logs should not be manually created."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Access logs should not be editable."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete access logs."""
        return request.user.is_superuser


# Admin site customization
admin.site.site_header = 'Pass-Man Administration'
admin.site.site_title = 'Pass-Man Admin'
admin.site.index_title = 'Welcome to Pass-Man Administration'