from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from users.models import User

from .forms import AreaForm, CategoryForm, UserAdminForm, UserCreateForm
from .models import Area, Category
from .permissions import can_access_administration


def _require_admin(request):
    """Server-side gate shared by every view in this module.

    Raises 403 for anyone whose role isn't admin, regardless of what
    the navigation shows: a user who knows the URL directly cannot
    bypass this by skipping the (already role-hidden) nav link.
    """
    if not can_access_administration(request.user):
        raise PermissionDenied("You do not have access to administration.")


@login_required
def administration_home(request):
    _require_admin(request)
    return render(request, "administration/home.html")


# --- Areas -------------------------------------------------------------


@login_required
def area_list(request):
    _require_admin(request)
    areas = Area.objects.order_by("name")
    return render(request, "administration/area_list.html", {"areas": areas})


@login_required
def area_create(request):
    _require_admin(request)
    if request.method == "POST":
        form = AreaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Área creada.")
            return redirect("administration:area_list")
    else:
        form = AreaForm()
    return render(
        request,
        "administration/area_form.html",
        {"form": form, "title": "Nueva área"},
    )


@login_required
def area_edit(request, pk):
    _require_admin(request)
    area = get_object_or_404(Area, pk=pk)
    if request.method == "POST":
        form = AreaForm(request.POST, instance=area)
        if form.is_valid():
            form.save()
            messages.success(request, "Área actualizada.")
            return redirect("administration:area_list")
    else:
        form = AreaForm(instance=area)
    return render(
        request,
        "administration/area_form.html",
        {"form": form, "title": f"Editar área: {area.name}"},
    )


@login_required
@require_POST
def area_delete(request, pk):
    _require_admin(request)
    area = get_object_or_404(Area, pk=pk)
    try:
        area.delete()
        messages.success(request, "Área eliminada.")
    except ProtectedError:
        # Area.categories uses on_delete=PROTECT (Block 2); surface that
        # as a normal message instead of a 500.
        messages.error(
            request,
            "No se puede eliminar el área porque tiene categorías asociadas.",
        )
    return redirect("administration:area_list")


# --- Categories ----------------------------------------------------------


@login_required
def category_list(request):
    _require_admin(request)
    categories = Category.objects.select_related("area").order_by("area__name", "name")
    return render(request, "administration/category_list.html", {"categories": categories})


@login_required
def category_create(request):
    _require_admin(request)
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría creada.")
            return redirect("administration:category_list")
    else:
        form = CategoryForm()
    return render(
        request,
        "administration/category_form.html",
        {"form": form, "title": "Nueva categoría"},
    )


@login_required
def category_edit(request, pk):
    _require_admin(request)
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría actualizada.")
            return redirect("administration:category_list")
    else:
        form = CategoryForm(instance=category)
    return render(
        request,
        "administration/category_form.html",
        {"form": form, "title": f"Editar categoría: {category.name}"},
    )


@login_required
@require_POST
def category_delete(request, pk):
    _require_admin(request)
    category = get_object_or_404(Category, pk=pk)
    try:
        category.delete()
        messages.success(request, "Categoría eliminada.")
    except ProtectedError:
        # Category.tickets uses on_delete=PROTECT (Block 3).
        messages.error(
            request,
            "No se puede eliminar la categoría porque tiene tickets asociados.",
        )
    return redirect("administration:category_list")


# --- Users -----------------------------------------------------------------


@login_required
def user_list(request):
    _require_admin(request)
    users = User.objects.select_related("area").order_by("username")
    return render(request, "administration/user_list.html", {"users": users})


@login_required
def user_create(request):
    _require_admin(request)
    # New users created here always get is_staff=False, is_superuser=False
    # (the model's own defaults), for every role, including admin: this
    # form never exposes those fields, exactly like User.objects
    # .create_user() already behaves. Django Admin access remains a
    # separate, staff-gated concern, untouched by this block.
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario creado.")
            return redirect("administration:user_list")
    else:
        form = UserCreateForm()
    return render(request, "administration/user_create.html", {"form": form})


@login_required
def user_edit(request, pk):
    _require_admin(request)
    target_user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserAdminForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario actualizado.")
            return redirect("administration:user_list")
    else:
        form = UserAdminForm(instance=target_user)
    return render(
        request,
        "administration/user_form.html",
        {"form": form, "target_user": target_user},
    )


@login_required
@require_POST
def user_delete(request, pk):
    _require_admin(request)
    target_user = get_object_or_404(User, pk=pk)
    try:
        target_user.delete()
        messages.success(request, "Usuario eliminado.")
    except ProtectedError:
        # E.g. Ticket.created_by / TicketHistory.changed_by use
        # on_delete=PROTECT (Blocks 3/5): a user with that kind of
        # history can't be hard-deleted. Deactivating (is_active=False
        # via the edit form) is the safe alternative.
        messages.error(
            request,
            "No se puede eliminar el usuario porque tiene tickets u otro "
            "historial asociado. Puedes desactivarlo en su lugar.",
        )
    return redirect("administration:user_list")
