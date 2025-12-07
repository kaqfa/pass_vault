from django import template
# Force reload
from apps.groups.models import UserGroup

register = template.Library()

@register.filter
def get_user_role(group, user):
    """
    Get the role of a user in a group.
    Usage: {{ group|get_user_role:user }}
    """
    if not user.is_authenticated:
        return None
        
    try:
        membership = UserGroup.objects.filter(group=group, user=user).first()
        return membership.role if membership else None
    except Exception:
        return None
