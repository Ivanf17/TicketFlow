from django.contrib import admin

from .models import AreaAssignmentCursor, TicketAssignmentHistory


@admin.register(AreaAssignmentCursor)
class AreaAssignmentCursorAdmin(admin.ModelAdmin):
    list_display = ("area", "last_assigned_to")


@admin.register(TicketAssignmentHistory)
class TicketAssignmentHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "ticket",
        "previous_assigned_to",
        "new_assigned_to",
        "changed_by",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("ticket__ticket_number",)
