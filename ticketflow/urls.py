"""
URL configuration for ticketflow project.

Only the base pieces (admin site, home page, auth) are wired in this
block. Each module (tickets, assignment, notifications, reports,
administration) will register its own urls.py and get included here
once its functionality is implemented.
"""
from django.contrib import admin
from django.urls import include, path

from .views import HomeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("users.urls")),
    path("tickets/", include("tickets.urls")),
    path("", HomeView.as_view(), name="home"),
]
