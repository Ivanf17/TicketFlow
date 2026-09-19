from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from administration.models import Area

from .models import User


class UserAreaByRoleTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")

    def test_employee_requires_area(self):
        user = User(username="empleado", role=User.Role.EMPLOYEE)
        with self.assertRaises(ValidationError):
            user.clean()

    def test_employee_with_area_is_valid(self):
        user = User(username="empleado", role=User.Role.EMPLOYEE, area=self.area)
        user.clean()  # should not raise

    def test_area_manager_requires_area(self):
        user = User(username="jefe_area", role=User.Role.AREA_MANAGER)
        with self.assertRaises(ValidationError):
            user.clean()

    def test_admin_does_not_require_area(self):
        user = User(username="admin_user", role=User.Role.ADMIN)
        user.clean()  # should not raise

    def test_management_does_not_require_area(self):
        user = User(username="direccion", role=User.Role.MANAGEMENT)
        user.clean()  # should not raise

    def test_superuser_creation_is_not_blocked_by_validation(self):
        # createsuperuser-style creation does not call full_clean(), and
        # role/area aren't in REQUIRED_FIELDS, so this must not depend on
        # validation to produce a valid row. TicketFlowUserManager
        # defaults the role to "admin" precisely so this satisfies the
        # DB-level constraint (admin never requires an area) without
        # needing full_clean() to run.
        user = User.objects.create_superuser(
            username="root", email="root@example.com", password="pass12345"
        )
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertIsNone(user.area)

    def test_superuser_creation_respects_explicit_role_override(self):
        user = User.objects.create_superuser(
            username="root2", email="root2@example.com", password="pass12345",
            role=User.Role.MANAGEMENT,
        )
        self.assertEqual(user.role, User.Role.MANAGEMENT)


class UserAreaDatabaseConstraintTests(TestCase):
    """DB-level enforcement of the same rule as User.clean(), verified
    with plain .save() (which never calls clean()/full_clean()), the
    exact gap the check constraint (Block 8) closes.
    """

    def setUp(self):
        self.area = Area.objects.create(name="TI")

    def test_employee_without_area_violates_constraint(self):
        user = User(username="empleado_sin_area", role=User.Role.EMPLOYEE)
        user.set_password("pass12345")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                user.save()

    def test_area_manager_without_area_violates_constraint(self):
        user = User(username="jefe_sin_area", role=User.Role.AREA_MANAGER)
        user.set_password("pass12345")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                user.save()

    def test_employee_with_area_satisfies_constraint(self):
        user = User(
            username="empleado_con_area", role=User.Role.EMPLOYEE, area=self.area
        )
        user.set_password("pass12345")
        user.save()  # should not raise
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

    def test_area_manager_with_area_satisfies_constraint(self):
        user = User(
            username="jefe_con_area", role=User.Role.AREA_MANAGER, area=self.area
        )
        user.set_password("pass12345")
        user.save()  # should not raise
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

    def test_admin_without_area_satisfies_constraint(self):
        user = User(username="admin_sin_area", role=User.Role.ADMIN)
        user.set_password("pass12345")
        user.save()  # should not raise
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

    def test_management_without_area_satisfies_constraint(self):
        user = User(username="direccion_sin_area", role=User.Role.MANAGEMENT)
        user.set_password("pass12345")
        user.save()  # should not raise
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

    def test_employee_losing_its_area_on_update_violates_constraint(self):
        user = User.objects.create_user(
            username="empleado_update", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        user.area = None
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                user.save()
