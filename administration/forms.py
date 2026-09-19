from django import forms

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
