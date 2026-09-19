from django.contrib import admin

from .models import Ticket, TicketHistory


class TicketHistoryInline(admin.TabularInline):
    model = TicketHistory
    extra = 0
    readonly_fields = ("previous_status", "status", "changed_by", "created_at")
    can_delete = False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "title",
        "category",
        "status",
        "created_by",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "category__area", "category")
    search_fields = ("ticket_number", "title")
    # `status` is read-only here so the state machine can only ever be
    # advanced through tickets.services.change_ticket_status(), never by
    # editing the field directly (which would skip transition validation
    # and history logging, and could even "reopen" a RESOLVED ticket).
    readonly_fields = ("ticket_number", "status", "created_at", "updated_at")
    inlines = [TicketHistoryInline]


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ("ticket", "previous_status", "status", "changed_by", "created_at")
    list_filter = ("status",)
