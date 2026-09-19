from django import forms

from administration.models import Category
from users.models import User

from .models import Ticket
from .services import get_next_status


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description", "category"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "category": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active categories may be selected when creating a ticket.
        self.fields["category"].queryset = Category.objects.filter(is_active=True)


class TicketAssignForm(forms.Form):
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Responsable",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, ticket=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active Area Managers of the ticket's own area are eligible.
        # This mirrors the Round Robin pool and is enforced here (not just
        # hidden in the UI) so an out-of-area id cannot be submitted.
        self.fields["assigned_to"].queryset = User.objects.filter(
            role=User.Role.AREA_MANAGER,
            area=ticket.category.area,
            is_active=True,
        )


class TicketStatusChangeForm(forms.Form):
    status = forms.ChoiceField(choices=(), label="Nuevo estado")

    def __init__(self, *args, ticket=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only the single valid next status is ever offered, so a
        # manipulated POST can't request an arbitrary status: anything
        # else fails form validation before reaching the service layer.
        next_status = get_next_status(ticket.status)
        self.fields["status"].choices = (
            [(next_status, next_status.label)] if next_status else []
        )
