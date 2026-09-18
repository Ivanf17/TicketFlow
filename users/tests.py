from django.core.exceptions import ValidationError
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
        # createsuperuser-style creation does not call full_clean(), so a
        # superuser can still be created even with the default role
        # (employee) and no area.
        user = User.objects.create_superuser(
            username="root", email="root@example.com", password="pass12345"
        )
        self.assertTrue(user.is_superuser)
