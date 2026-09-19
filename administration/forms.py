from django import forms
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm

from users.models import User

from .models import Area, Category


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        # `area` is a required ModelChoiceField (the model FK has no
        # null=True), so the form itself already refuses to save a
        # category without an area.
        fields = ["name", "area", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "area": forms.Select(attrs={"class": "form-select"}),
        }


class UserAdminForm(forms.ModelForm):
    """Deliberately limited to role/area/is_active.

    Never touches username, email, password or Django's own
    is_staff/is_superuser/permissions: those stay exclusively in
    Django's native auth mechanism (Django Admin / createsuperuser),
    per the Block 8 instruction not to reimplement authentication. Being
    a ModelForm, saving it runs full_clean() (and therefore
    User.clean()), so the existing employee/area_manager-requires-area
    rule is enforced here for free, in addition to the DB constraint.
    """

    class Meta:
        model = User
        fields = ["role", "area", "is_active"]
        widgets = {
            "role": forms.Select(attrs={"class": "form-select"}),
            "area": forms.Select(attrs={"class": "form-select"}),
        }


class UserCreateForm(DjangoUserCreationForm):
    """Reuses Django's own UserCreationForm (password1/password2,
    strength validation via AUTH_PASSWORD_VALIDATORS, hashing through
    ``set_password()`` on save, case-insensitive duplicate-username
    rejection) instead of reimplementing any of that.

    ``django.contrib.auth.forms.BaseUserCreationForm.Meta.model`` points
    at Django's own built-in ``auth.User`` (it is imported directly in
    that module), not at this project's swapped ``AUTH_USER_MODEL``.
    Per Django's documented pattern for custom user models, ``model``
    must be overridden explicitly here; only inheriting ``Meta`` is not
    enough.

    Being a ModelForm, saving it runs full_clean() (and therefore
    User.clean()), so the existing employee/area_manager-requires-area
    rule is enforced here too, exactly as it already is for
    UserAdminForm -- no validation is duplicated.

    Deliberately does not expose is_staff/is_superuser/permissions: new
    users created here get the model's own defaults for those fields
    (False/False), for every role, exactly like User.objects
    .create_user() already does. See administration/views.py for the
    documented consequence.
    """

    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("username", "email", "role", "area", "is_active")
        widgets = {
            "role": forms.Select(attrs={"class": "form-select"}),
            "area": forms.Select(attrs={"class": "form-select"}),
        }
