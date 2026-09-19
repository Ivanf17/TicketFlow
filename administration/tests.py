from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from tickets.models import Ticket
from users.models import User

from .models import Area, Category


class CategoryAreaRelationTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")

    def test_category_requires_area(self):
        category = Category(name="Hardware")
        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_category_belongs_to_exactly_one_area(self):
        category = Category.objects.create(name="Hardware", area=self.area)
        self.assertEqual(category.area, self.area)
        self.assertIn(category, self.area.categories.all())

    def test_area_with_categories_cannot_be_deleted(self):
        Category.objects.create(name="Hardware", area=self.area)
        with self.assertRaises(ProtectedError):
            self.area.delete()

    def test_area_without_categories_can_be_deleted(self):
        empty_area = Area.objects.create(name="Vacía")
        empty_area.delete()
        self.assertFalse(Area.objects.filter(pk=empty_area.pk).exists())


class AdministrationAccessTests(TestCase):
    """Role-based access to the administration section as a whole
    (Block 8): only admin gets in, everyone else is rejected server-side
    regardless of what the navigation shows.
    """

    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.manager = User.objects.create_user(
            username="jefe", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )
        self.management = User.objects.create_user(
            username="direccion", password="pass12345", role=User.Role.MANAGEMENT,
        )

    def test_login_required(self):
        response = self.client.get(reverse("administration:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_employee_cannot_access_administration(self):
        self.client.login(username="empleado", password="pass12345")
        response = self.client.get(reverse("administration:home"))
        self.assertEqual(response.status_code, 403)

    def test_area_manager_cannot_access_administration(self):
        self.client.login(username="jefe", password="pass12345")
        response = self.client.get(reverse("administration:home"))
        self.assertEqual(response.status_code, 403)

    def test_management_cannot_access_administration(self):
        self.client.login(username="direccion", password="pass12345")
        response = self.client.get(reverse("administration:home"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_administration(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(reverse("administration:home"))
        self.assertEqual(response.status_code, 200)

    def test_admin_sees_administration_link_in_nav(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("administration:home"))

    def test_employee_does_not_see_administration_link_in_nav(self):
        self.client.login(username="empleado", password="pass12345")
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, reverse("administration:home"))

    def test_area_manager_does_not_see_administration_link_in_nav(self):
        self.client.login(username="jefe", password="pass12345")
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, reverse("administration:home"))

    def test_management_does_not_see_administration_link_in_nav(self):
        self.client.login(username="direccion", password="pass12345")
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, reverse("administration:home"))


class AreaAdministrationTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.manager = User.objects.create_user(
            username="jefe", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.management = User.objects.create_user(
            username="direccion", password="pass12345", role=User.Role.MANAGEMENT,
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )

    def test_non_admin_roles_get_403_on_area_list(self):
        for username in ("empleado", "jefe", "direccion"):
            self.client.login(username=username, password="pass12345")
            response = self.client.get(reverse("administration:area_list"))
            self.assertEqual(response.status_code, 403, username)
            self.client.logout()

    def test_admin_can_list_areas(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(reverse("administration:area_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TI")

    def test_admin_can_create_area(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:area_create"),
            {"name": "Mantenimiento", "description": "", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Area.objects.filter(name="Mantenimiento").exists())

    def test_non_admin_cannot_create_area_via_post(self):
        for username in ("empleado", "jefe", "direccion"):
            self.client.login(username=username, password="pass12345")
            response = self.client.post(
                reverse("administration:area_create"),
                {"name": "Hackeo", "description": "", "is_active": "on"},
            )
            self.assertEqual(response.status_code, 403, username)
            self.assertFalse(Area.objects.filter(name="Hackeo").exists())
            self.client.logout()

    def test_admin_can_edit_area(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:area_edit", args=[self.area.pk]),
            {"name": "TI Renombrada", "description": "", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.area.refresh_from_db()
        self.assertEqual(self.area.name, "TI Renombrada")

    def test_non_admin_cannot_edit_area_via_post(self):
        self.client.login(username="jefe", password="pass12345")
        response = self.client.post(
            reverse("administration:area_edit", args=[self.area.pk]),
            {"name": "Hackeada", "description": "", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 403)
        self.area.refresh_from_db()
        self.assertEqual(self.area.name, "TI")

    def test_admin_deleting_area_with_categories_is_protected(self):
        Category.objects.create(name="Hardware", area=self.area)
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:area_delete", args=[self.area.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Area.objects.filter(pk=self.area.pk).exists())

    def test_admin_can_delete_empty_area(self):
        empty_area = Area.objects.create(name="Vacía")
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:area_delete", args=[empty_area.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Area.objects.filter(pk=empty_area.pk).exists())

    def test_non_admin_cannot_delete_area(self):
        self.client.login(username="jefe", password="pass12345")
        response = self.client.post(
            reverse("administration:area_delete", args=[self.area.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Area.objects.filter(pk=self.area.pk).exists())

    def test_area_delete_requires_post(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(
            reverse("administration:area_delete", args=[self.area.pk])
        )
        self.assertEqual(response.status_code, 405)


class CategoryAdministrationTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.other_area = Area.objects.create(name="RRHH")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.manager = User.objects.create_user(
            username="jefe", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.other_manager = User.objects.create_user(
            username="jefe_rrhh", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.other_area,
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )

    def test_area_manager_cannot_manage_categories_of_any_area(self):
        # Per the reference matrix, category administration is
        # Admin-only; an area_manager of the category's own area is
        # blocked exactly like one from a different area.
        self.client.login(username="jefe", password="pass12345")
        response = self.client.get(reverse("administration:category_list"))
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        self.client.login(username="jefe_rrhh", password="pass12345")
        response = self.client.post(
            reverse("administration:category_edit", args=[self.category.pk]),
            {"name": "Hackeada", "area": self.other_area.pk, "is_active": "on"},
        )
        self.assertEqual(response.status_code, 403)
        self.category.refresh_from_db()
        self.assertEqual(self.category.area, self.area)

    def test_category_cannot_be_created_without_area(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:category_create"),
            {"name": "Sin área", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 200)  # form re-rendered, invalid
        self.assertFalse(Category.objects.filter(name="Sin área").exists())

    def test_admin_can_create_category_with_area(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:category_create"),
            {"name": "Software", "area": self.area.pk, "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Category.objects.filter(name="Software", area=self.area).exists()
        )

    def test_category_can_only_belong_to_one_area_at_a_time(self):
        # Category.area is a single ForeignKey (no M2M): re-editing it
        # re-points it to exactly one area, it is never associated with
        # two areas simultaneously.
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:category_edit", args=[self.category.pk]),
            {"name": "Hardware", "area": self.other_area.pk, "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.category.refresh_from_db()
        self.assertEqual(self.category.area, self.other_area)

    def test_admin_deleting_category_with_tickets_is_protected(self):
        Ticket.objects.create_ticket(
            title="t", description="d", category=self.category, created_by=self.employee
        )
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:category_delete", args=[self.category.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_non_admin_cannot_delete_category(self):
        self.client.login(username="jefe", password="pass12345")
        response = self.client.post(
            reverse("administration:category_delete", args=[self.category.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())


class UserAdministrationTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.other_area = Area.objects.create(name="RRHH")
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.manager = User.objects.create_user(
            username="jefe", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )
        self.management = User.objects.create_user(
            username="direccion", password="pass12345", role=User.Role.MANAGEMENT,
        )

    def test_non_admin_cannot_manage_users(self):
        for username in ("empleado", "jefe", "direccion"):
            self.client.login(username=username, password="pass12345")
            response = self.client.get(reverse("administration:user_list"))
            self.assertEqual(response.status_code, 403, username)
            self.client.logout()

    def test_admin_can_list_users(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(reverse("administration:user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "empleado")

    def test_admin_can_change_user_area(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_edit", args=[self.employee.pk]),
            {"role": User.Role.EMPLOYEE, "area": self.other_area.pk, "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.area, self.other_area)

    def test_cannot_save_employee_without_area_via_admin_form(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_edit", args=[self.employee.pk]),
            {"role": User.Role.EMPLOYEE, "area": "", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 200)  # re-rendered, invalid
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.area, self.area)

    def test_cannot_save_area_manager_without_area_via_admin_form(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_edit", args=[self.manager.pk]),
            {"role": User.Role.AREA_MANAGER, "area": "", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.area, self.area)

    def test_admin_can_leave_admin_role_without_area(self):
        target = User.objects.create_user(
            username="admin2", password="pass12345", role=User.Role.ADMIN,
        )
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_edit", args=[target.pk]),
            {"role": User.Role.ADMIN, "area": "", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)

    def test_non_admin_cannot_edit_user_via_post(self):
        self.client.login(username="jefe", password="pass12345")
        response = self.client.post(
            reverse("administration:user_edit", args=[self.employee.pk]),
            {"role": User.Role.ADMIN, "area": "", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 403)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.role, User.Role.EMPLOYEE)

    def test_admin_deleting_user_with_ticket_history_is_protected(self):
        category = Category.objects.create(name="Hardware", area=self.area)
        Ticket.objects.create_ticket(
            title="t", description="d", category=category, created_by=self.employee
        )
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_delete", args=[self.employee.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.employee.pk).exists())

    def test_non_admin_cannot_delete_user(self):
        self.client.login(username="jefe", password="pass12345")
        response = self.client.post(
            reverse("administration:user_delete", args=[self.employee.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.employee.pk).exists())


class UserCreationTests(TestCase):
    """Block 8.1: creating users from /administration/users/new/."""

    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.manager = User.objects.create_user(
            username="jefe", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )
        self.management = User.objects.create_user(
            username="direccion", password="pass12345", role=User.Role.MANAGEMENT,
        )

    def valid_payload(self, **overrides):
        payload = {
            "username": "nuevo_usuario",
            "email": "nuevo@example.com",
            "role": User.Role.EMPLOYEE,
            "area": self.area.pk,
            "is_active": "on",
            "password1": "S0lidP4ssw0rd!",
            "password2": "S0lidP4ssw0rd!",
        }
        payload.update(overrides)
        return payload

    # --- Access -------------------------------------------------------

    def test_login_required(self):
        response = self.client.get(reverse("administration:user_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_admin_can_access_user_create(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(reverse("administration:user_create"))
        self.assertEqual(response.status_code, 200)

    def test_employee_cannot_access_user_create(self):
        self.client.login(username="empleado", password="pass12345")
        response = self.client.get(reverse("administration:user_create"))
        self.assertEqual(response.status_code, 403)

    def test_area_manager_cannot_access_user_create(self):
        self.client.login(username="jefe", password="pass12345")
        response = self.client.get(reverse("administration:user_create"))
        self.assertEqual(response.status_code, 403)

    def test_management_cannot_access_user_create(self):
        self.client.login(username="direccion", password="pass12345")
        response = self.client.get(reverse("administration:user_create"))
        self.assertEqual(response.status_code, 403)

    def test_non_admin_cannot_create_user_via_post(self):
        for username in ("empleado", "jefe", "direccion"):
            self.client.login(username=username, password="pass12345")
            response = self.client.post(
                reverse("administration:user_create"),
                self.valid_payload(username="colado"),
            )
            self.assertEqual(response.status_code, 403, username)
            self.assertFalse(User.objects.filter(username="colado").exists())
            self.client.logout()

    # --- Valid creation -------------------------------------------------

    def test_admin_can_create_employee_with_area(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_create"),
            self.valid_payload(
                username="nuevo_empleado", role=User.Role.EMPLOYEE, area=self.area.pk
            ),
        )
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(username="nuevo_empleado")
        self.assertEqual(created.role, User.Role.EMPLOYEE)
        self.assertEqual(created.area, self.area)
        self.assertTrue(created.is_active)

    def test_admin_can_create_area_manager_with_area(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_create"),
            self.valid_payload(
                username="nuevo_jefe", role=User.Role.AREA_MANAGER, area=self.area.pk
            ),
        )
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(username="nuevo_jefe")
        self.assertEqual(created.role, User.Role.AREA_MANAGER)
        self.assertEqual(created.area, self.area)

    def test_admin_can_create_admin_without_area(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_create"),
            self.valid_payload(username="nuevo_admin", role=User.Role.ADMIN, area=""),
        )
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(username="nuevo_admin")
        self.assertEqual(created.role, User.Role.ADMIN)
        self.assertIsNone(created.area)

    def test_admin_can_create_management_without_area(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_create"),
            self.valid_payload(
                username="nueva_direccion", role=User.Role.MANAGEMENT, area=""
            ),
        )
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(username="nueva_direccion")
        self.assertEqual(created.role, User.Role.MANAGEMENT)
        self.assertIsNone(created.area)

    def test_created_user_appears_in_user_list(self):
        self.client.login(username="admin1", password="pass12345")
        self.client.post(
            reverse("administration:user_create"),
            self.valid_payload(username="visible_en_lista"),
        )
        response = self.client.get(reverse("administration:user_list"))
        self.assertContains(response, "visible_en_lista")

    # --- Validation -------------------------------------------------------

    def test_employee_without_area_is_rejected(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_create"),
            self.valid_payload(
                username="empleado_sin_area", role=User.Role.EMPLOYEE, area=""
            ),
        )
        self.assertEqual(response.status_code, 200)  # form re-rendered, invalid
        self.assertFalse(User.objects.filter(username="empleado_sin_area").exists())

    def test_area_manager_without_area_is_rejected(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_create"),
            self.valid_payload(
                username="jefe_sin_area", role=User.Role.AREA_MANAGER, area=""
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="jefe_sin_area").exists())

    def test_duplicate_username_is_rejected(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_create"),
            self.valid_payload(username="empleado"),  # already exists (setUp)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="empleado").count(), 1)

    def test_mismatched_passwords_are_rejected(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_create"),
            self.valid_payload(
                username="password_mismatch",
                password1="S0lidP4ssw0rd!",
                password2="OtraContrasena!9",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="password_mismatch").exists())

    def test_missing_required_fields_are_rejected(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_create"),
            {"username": "", "role": "", "password1": "", "password2": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 4)  # unchanged from setUp

    # --- Password security ---------------------------------------------

    def test_password_is_hashed_not_stored_in_plain_text(self):
        self.client.login(username="admin1", password="pass12345")
        self.client.post(
            reverse("administration:user_create"),
            self.valid_payload(
                username="password_check",
                password1="S0lidP4ssw0rd!",
                password2="S0lidP4ssw0rd!",
            ),
        )
        created = User.objects.get(username="password_check")
        self.assertNotEqual(created.password, "S0lidP4ssw0rd!")
        self.assertTrue(created.password.startswith("pbkdf2_"))
        self.assertTrue(created.check_password("S0lidP4ssw0rd!"))
        self.assertFalse(created.check_password("wrong-password"))

    # --- is_staff / is_superuser -----------------------------------------

    def test_created_users_never_get_staff_or_superuser_regardless_of_role(self):
        self.client.login(username="admin1", password="pass12345")
        roles_and_areas = [
            (User.Role.EMPLOYEE, self.area.pk),
            (User.Role.AREA_MANAGER, self.area.pk),
            (User.Role.ADMIN, ""),
            (User.Role.MANAGEMENT, ""),
        ]
        for role, area in roles_and_areas:
            username = f"staff_check_{role}"
            self.client.post(
                reverse("administration:user_create"),
                self.valid_payload(username=username, role=role, area=area),
            )
            created = User.objects.get(username=username)
            self.assertFalse(created.is_staff, role)
            self.assertFalse(created.is_superuser, role)


class UserEditRegressionTests(TestCase):
    """Confirms editing users still works exactly as before Block 8.1."""

    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.other_area = Area.objects.create(name="RRHH")
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )

    def test_edit_still_changes_role_and_area(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_edit", args=[self.employee.pk]),
            {
                "role": User.Role.AREA_MANAGER,
                "area": self.other_area.pk,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.role, User.Role.AREA_MANAGER)
        self.assertEqual(self.employee.area, self.other_area)

    def test_edit_still_toggles_active_status(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_edit", args=[self.employee.pk]),
            {"role": User.Role.EMPLOYEE, "area": self.area.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)

    def test_edit_still_enforces_area_required_for_employee(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("administration:user_edit", args=[self.employee.pk]),
            {"role": User.Role.EMPLOYEE, "area": "", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.area, self.area)  # unchanged

    def test_edit_does_not_touch_password(self):
        original_password_hash = self.employee.password
        self.client.login(username="admin1", password="pass12345")
        self.client.post(
            reverse("administration:user_edit", args=[self.employee.pk]),
            {"role": User.Role.EMPLOYEE, "area": self.area.pk, "is_active": "on"},
        )
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.password, original_password_hash)
