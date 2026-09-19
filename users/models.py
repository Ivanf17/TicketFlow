from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models


class TicketFlowUserManager(UserManager):
    """Identical to Django's UserManager, except ``create_superuser``
    defaults the TicketFlow ``role`` to "admin" instead of leaving it at
    the model's default ("employee").

    ``role``/``area`` are not in ``REQUIRED_FIELDS``, so
    ``createsuperuser`` never asks for them and a superuser would
    otherwise be created with role=employee, area=None — a combination
    the ``user_area_required_for_employee_and_area_manager`` check
    constraint (added in Block 8) correctly rejects, since employees
    require an area. A superuser is an administrator of the whole
    system by definition, so "admin" (which never requires an area) is
    the only sensible default here. The caller can still pass an
    explicit ``role`` to override this.
    """

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        return super().create_superuser(username, email, password, **extra_fields)


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

    objects = TicketFlowUserManager()

    class Meta:
        # Enforced at the database level (not just clean()/full_clean(),
        # which never run on a plain .save() or on User.objects
        # .create_user(), e.g. from the ORM/shell/createsuperuser): an
        # employee or area_manager row can never be inserted or updated
        # without an area. Verified against the current database before
        # adding this (no existing employee/area_manager rows without an
        # area), so this migration applies cleanly.
        #
        # The role values are repeated as literals ("employee",
        # "area_manager") rather than referencing Role.EMPLOYEE /
        # Role.AREA_MANAGER here, because a nested Meta class body
        # cannot see names bound in the enclosing User class body
        # (ordinary Python class-scoping rule, not Django-specific).
        # Keep these in sync with Role.EMPLOYEE / Role.AREA_MANAGER.
        constraints = [
            models.CheckConstraint(
                check=~(
                    models.Q(role__in=["employee", "area_manager"])
                    & models.Q(area__isnull=True)
                ),
                name="user_area_required_for_employee_and_area_manager",
            ),
        ]

    def clean(self):
        super().clean()
        if self.role in self.ROLES_REQUIRING_AREA and self.area_id is None:
            raise ValidationError(
                {"area": "This role requires an area to be set."}
            )

    def __str__(self):
        return self.username
