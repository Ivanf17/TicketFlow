from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    """TicketFlow custom user.

    Extends Django's built-in AbstractUser (native auth/sessions are kept
    as-is) with the role and area needed by the rest of the system. This
    block only defines the structure; role-based permissions and screens
    are implemented in later blocks.
    """

    class Role(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        AREA_MANAGER = "area_manager", "Area Manager"
        ADMIN = "admin", "Admin"
        MANAGEMENT = "management", "Management"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
    )
    area = models.ForeignKey(
        "administration.Area",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    ROLES_REQUIRING_AREA = (Role.EMPLOYEE, Role.AREA_MANAGER)

    def clean(self):
        super().clean()
        if self.role in self.ROLES_REQUIRING_AREA and self.area_id is None:
            raise ValidationError(
                {"area": "This role requires an area to be set."}
            )

    def __str__(self):
        return self.username
