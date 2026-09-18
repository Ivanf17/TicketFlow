from django.contrib import admin

from .models import Area, Category


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 0


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    inlines = [CategoryInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "is_active", "created_at")
    list_filter = ("area", "is_active")
    search_fields = ("name",)
