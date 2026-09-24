from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

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


class PasswordResetTests(TestCase):
    """Block 9: password recovery via Django's native views.

    User.email is deliberately left non-unique/optional (see
    CLAUDE.md/README) -- these tests only verify the behaviour that
    follows from that decision, they do not require it to change.
    """

    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.user_with_email = User.objects.create_user(
            username="con_email", password="ViejaPass123!",
            role=User.Role.EMPLOYEE, area=self.area,
            email="con_email@example.com",
        )
        self.user_without_email = User.objects.create_user(
            username="sin_email", password="ViejaPass123!",
            role=User.Role.EMPLOYEE, area=self.area,
        )

    def test_valid_email_sends_exactly_one_reset_email(self):
        response = self.client.post(
            reverse("users:password_reset"), {"email": "con_email@example.com"}
        )
        self.assertRedirects(response, reverse("users:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("con_email@example.com", mail.outbox[0].to)

    def test_nonexistent_email_generates_no_email(self):
        response = self.client.post(
            reverse("users:password_reset"), {"email": "no_existe@example.com"}
        )
        self.assertRedirects(response, reverse("users:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_response_does_not_reveal_whether_the_account_exists(self):
        # Same request, same status code and same redirect target
        # whether or not the email belongs to a real account: nothing in
        # the response lets a caller distinguish the two cases.
        response_existing = self.client.post(
            reverse("users:password_reset"), {"email": "con_email@example.com"}
        )
        response_missing = self.client.post(
            reverse("users:password_reset"), {"email": "no_existe@example.com"}
        )
        self.assertEqual(response_existing.status_code, response_missing.status_code)
        self.assertEqual(response_existing.url, response_missing.url)

    def test_user_without_email_is_never_matched_by_reset_form(self):
        # "sin_email" has no email on file, so there is no value an
        # attacker could submit to reach them; get_users() (the same
        # lookup PasswordResetView.form_valid() uses) never returns them.
        matches = list(PasswordResetForm().get_users("sin_email@example.com"))
        self.assertNotIn(self.user_without_email, matches)
        self.assertEqual(matches, [])

    def test_full_reset_flow_allows_login_with_new_password(self):
        self.client.post(
            reverse("users:password_reset"), {"email": "con_email@example.com"}
        )
        self.assertEqual(len(mail.outbox), 1)

        uidb64 = urlsafe_base64_encode(force_bytes(self.user_with_email.pk))
        token = default_token_generator.make_token(self.user_with_email)
        confirm_url = reverse(
            "users:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )
        response = self.client.get(confirm_url, follow=True)
        self.assertEqual(response.status_code, 200)
        set_password_url = response.request["PATH_INFO"]

        response = self.client.post(
            set_password_url,
            {"new_password1": "NuevaPass456!", "new_password2": "NuevaPass456!"},
        )
        self.assertRedirects(response, reverse("users:password_reset_complete"))

        self.assertFalse(
            self.client.login(username="con_email", password="ViejaPass123!")
        )
        self.assertTrue(
            self.client.login(username="con_email", password="NuevaPass456!")
        )

    def test_invalid_token_is_rejected(self):
        uidb64 = urlsafe_base64_encode(force_bytes(self.user_with_email.pk))
        confirm_url = reverse(
            "users:password_reset_confirm",
            kwargs={"uidb64": uidb64, "token": "token-invalido"},
        )
        response = self.client.get(confirm_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no es válido")
