from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Read-only admin view for administrative inspection.

    Notifications are system-generated facts about real ticket events;
    the admin can consult them, but add/change is disabled so the admin
    can't be used to fabricate or tamper with notification data and
    bypass the normal notification rules.
    """

    list_display = ("recipient", "ticket", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("recipient__username", "ticket__ticket_number", "title")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
