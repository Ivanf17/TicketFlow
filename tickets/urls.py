from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("new/", views.ticket_create, name="create"),
    path("<int:pk>/", views.ticket_detail, name="detail"),
    path("<int:pk>/assign/", views.ticket_assign, name="assign"),
    path("<int:pk>/status/", views.ticket_change_status, name="change_status"),
]
