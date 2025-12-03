"""
Django admin configuration for Group models.

This module configures the Django admin interface for group management
with appropriate fields, filters, and security considerations.

Related Documentation:
- CODING_STANDARDS.md: Admin Configuration Best Practices
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count

from .models import Group, UserGroup


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Admin configuration for Group model."""
    
    # List display
    list_display = [
        'name',
        'owner_link',
        'is_personal',
        'member_count',
        'password_count',
        'created_at',
        'updated_at'
    ]
    
    # List filters
    list_filter = [
        'is_personal',
        'created_at',
        'updated_at',
        'owner'
    ]
    
    # Search fields
    search_fields = ['name', 'description', 'owner__email', 'owner__full_name']
    
    # Ordering
    ordering = ['-created_at']
    
    # Read-only fields
    readonly_fields = [
        'id',
        'encryption_key',
        'created_at',
        'updated_at',
        'member_count_display',
        'password_count_display'
    ]
    
    # Fieldsets
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'owner')
        }),
        ('Settings', {
            'fields': ('is_personal',)
        }),
        ('Security', {
            'fields': ('encryption_key',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('member_count_display', 'password_count_display'),
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
    actions = ['make_shared', 'regenerate_encryption_keys']
    
    def owner_link(self, obj):
        """Link to owner admin page."""
        if obj.owner:
            url = reverse('admin:users_user_change', args=[obj.owner.pk])
            return format_html('<a href="{}">{}</a>', url, obj.owner.full_name)
        return '-'
    owner_link.short_description = 'Owner'
    
    def member_count(self, obj):
        """Display member count."""
        return obj.get_member_count()
    member_count.short_description = 'Members'
    
    def password_count(self, obj):
        """Display password count."""
        return obj.get_password_count()
    password_count.short_description = 'Passwords'
    
    def member_count_display(self, obj):
        """Display member count for readonly field."""
        return obj.get_member_count()
    member_count_display.short_description = 'Member Count'
    
    def password_count_display(self, obj):
        """Display password count for readonly field."""
        return obj.get_password_count()
    password_count_display.short_description = 'Password Count'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('owner')
    
    def make_shared(self, request, queryset):
        """Mark selected groups as shared (non-personal)."""
        updated = 0
        for group in queryset:
            if group.is_personal:
                group.is_personal = False
                group.save()
                updated += 1
        
        self.message_user(request, f'{updated} groups marked as shared.')
    make_shared.short_description = "Mark selected groups as shared"
    
    def regenerate_encryption_keys(self, request, queryset):
        """Regenerate encryption keys for selected groups."""
        updated = 0
        for group in queryset:
            group._generate_encryption_key()
            group.save()
            updated += 1
        
        self.message_user(request, f'Encryption keys regenerated for {updated} groups.')
    regenerate_encryption_keys.short_description = "Regenerate encryption keys"
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete groups."""
        return request.user.is_superuser


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    """Admin configuration for UserGroup model."""
    
    # List display
    list_display = [
        'user_link',
        'group_link',
        'role',
        'joined_at',
        'added_by_link'
    ]
    
    # List filters
    list_filter = [
        'role',
        'joined_at',
        'group__is_personal'
    ]
    
    # Search fields
    search_fields = [
        'user__email',
        'user__full_name',
        'group__name',
        'added_by__email',
        'added_by__full_name'
    ]
    
    # Ordering
    ordering = ['-joined_at']
    
    # Read-only fields
    readonly_fields = [
        'id',
        'joined_at',
        'created_at',
        'updated_at'
    ]
    
    # Fieldsets
    fieldsets = (
        ('Membership Information', {
            'fields': ('user', 'group', 'role')
        }),
        ('Metadata', {
            'fields': ('added_by', 'joined_at'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    # Filters
    date_hierarchy = 'joined_at'
    
    # Actions
    actions = ['promote_to_admin', 'demote_to_member']
    
    def user_link(self, obj):
        """Link to user admin page."""
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.full_name)
        return '-'
    user_link.short_description = 'User'
    
    def group_link(self, obj):
        """Link to group admin page."""
        if obj.group:
            url = reverse('admin:groups_group_change', args=[obj.group.pk])
            return format_html('<a href="{}">{}</a>', url, obj.group.name)
        return '-'
    group_link.short_description = 'Group'
    
    def added_by_link(self, obj):
        """Link to added_by user admin page."""
        if obj.added_by:
            url = reverse('admin:users_user_change', args=[obj.added_by.pk])
            return format_html('<a href="{}">{}</a>', url, obj.added_by.full_name)
        return '-'
    added_by_link.short_description = 'Added By'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user', 'group', 'added_by')
    
    def promote_to_admin(self, request, queryset):
        """Promote selected members to admin role."""
        updated = 0
        for membership in queryset:
            if membership.role == UserGroup.Role.MEMBER:
                membership.role = UserGroup.Role.ADMIN
                membership.save()
                updated += 1
        
        self.message_user(request, f'{updated} members promoted to admin.')
    promote_to_admin.short_description = "Promote selected members to admin"
    
    def demote_to_member(self, request, queryset):
        """Demote selected admins to member role."""
        updated = 0
        for membership in queryset:
            if membership.role == UserGroup.Role.ADMIN:
                membership.role = UserGroup.Role.MEMBER
                membership.save()
                updated += 1
        
        self.message_user(request, f'{updated} admins demoted to member.')
    demote_to_member.short_description = "Demote selected admins to member"
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete memberships."""
        return request.user.is_superuser


# Admin site customization
admin.site.site_header = 'Pass-Man Administration'
admin.site.site_title = 'Pass-Man Admin'
admin.site.index_title = 'Welcome to Pass-Man Administration'