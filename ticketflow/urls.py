"""
URL configuration for ticketflow project.

Root URL index: the Django admin site, the home page and each app's
own urls.py (users under accounts/, reports under dashboard/).
assignment has no urls.py: its manual-assignment screen is served by
tickets (tickets:assign).
"""
from django.contrib import admin
from django.urls import include, path

from .views import HomeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("users.urls")),
    path("tickets/", include("tickets.urls")),
    path("notifications/", include("notifications.urls")),
    path("dashboard/", include("reports.urls")),
    path("administration/", include("administration.urls")),
    path("", HomeView.as_view(), name="home"),
]
