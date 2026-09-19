from django.urls import path

from . import views

app_name = "administration"

urlpatterns = [
    path("", views.administration_home, name="home"),
    path("areas/", views.area_list, name="area_list"),
    path("areas/new/", views.area_create, name="area_create"),
    path("areas/<int:pk>/edit/", views.area_edit, name="area_edit"),
    path("areas/<int:pk>/delete/", views.area_delete, name="area_delete"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/new/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("users/", views.user_list, name="user_list"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),
]
