from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class TicketFlowUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("TicketFlow", {"fields": ("role", "area")}),
    )
    list_display = UserAdmin.list_display + ("role", "area")
    list_filter = UserAdmin.list_filter + ("role", "area")
