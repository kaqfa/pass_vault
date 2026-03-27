"""
Notification views for Pass-Man.
"""

import logging
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.http import JsonResponse

from apps.notifications.services import NotificationService
from apps.notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationListView(LoginRequiredMixin, View):
    """View for listing user notifications."""

    template_name = 'notifications/list.html'

    def get(self, request):
        notifications = NotificationService.get_user_notifications(
            request.user,
            unread_only=False
        )[:50]  # Limit to 50

        context = {
            'page_title': 'Notifications',
            'notifications': notifications,
            'unread_count': NotificationService.get_unread_count(request.user)
        }
        return render(request, self.template_name, context)


def get_unread_count(request):
    """AJAX endpoint to get unread notification count."""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})

    count = NotificationService.get_unread_count(request.user)
    return JsonResponse({'count': count})


def mark_as_read(request, notification_id):
    """AJAX endpoint to mark notification as read."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False}, status=401)

    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    success = NotificationService.mark_as_read(request.user, notification_id)
    return JsonResponse({'success': success})


def mark_all_as_read(request):
    """AJAX endpoint to mark all notifications as read."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False}, status=401)

    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    count = NotificationService.mark_all_as_read(request.user)
    return JsonResponse({'success': True, 'count': count})


def get_notification_dropdown(request):
    """AJAX endpoint to get notification dropdown content."""
    if not request.user.is_authenticated:
        return JsonResponse({'html': ''})

    notifications = NotificationService.get_user_notifications(
        request.user,
        unread_only=False
    )[:10]

    context = {
        'notifications': notifications
    }

    from django.template.loader import render_to_string
    html = render_to_string('notifications/partials/dropdown.html', context, request=request)

    return JsonResponse({'html': html, 'unread_count': NotificationService.get_unread_count(request.user)})
