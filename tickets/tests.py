from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from administration.models import Area, Category
from users.models import User

from .models import Ticket, TicketHistory


class TicketModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.other_area = Area.objects.create(name="RRHH")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.creator = User.objects.create_user(
            username="creador", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )

    def test_ticket_requires_title(self):
        ticket = Ticket(
            description="desc", category=self.category, created_by=self.creator
        )
        with self.assertRaises(ValidationError) as cm:
            ticket.full_clean()
        self.assertIn("title", cm.exception.message_dict)

    def test_ticket_requires_description(self):
        ticket = Ticket(
            title="Sin descripción", category=self.category, created_by=self.creator
        )
        with self.assertRaises(ValidationError) as cm:
            ticket.full_clean()
        self.assertIn("description", cm.exception.message_dict)

    def test_ticket_requires_category(self):
        ticket = Ticket(
            title="Sin categoría", description="desc", created_by=self.creator
        )
        with self.assertRaises(ValidationError) as cm:
            ticket.full_clean()
        self.assertIn("category", cm.exception.message_dict)

    def test_ticket_starts_as_pending(self):
        ticket = Ticket.objects.create_ticket(
            title="Impresora rota",
            description="No enciende",
            category=self.category,
            created_by=self.creator,
        )
        self.assertEqual(ticket.status, Ticket.Status.PENDING)

    def test_assigned_to_can_be_null(self):
        ticket = Ticket.objects.create_ticket(
            title="Sin asignar",
            description="desc",
            category=self.category,
            created_by=self.creator,
        )
        self.assertIsNone(ticket.assigned_to)

    def test_category_determines_area(self):
        ticket = Ticket.objects.create_ticket(
            title="Ver área",
            description="desc",
            category=self.category,
            created_by=self.creator,
        )
        self.assertEqual(ticket.area, self.area)
        self.assertEqual(ticket.area, ticket.category.area)

    def test_category_uses_protect(self):
        Ticket.objects.create_ticket(
            title="No borrar categoría",
            description="desc",
            category=self.category,
            created_by=self.creator,
        )
        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_created_by_uses_protect(self):
        Ticket.objects.create_ticket(
            title="No borrar creador",
            description="desc",
            category=self.category,
            created_by=self.creator,
        )
        with self.assertRaises(ProtectedError):
            self.creator.delete()

    def test_assigned_to_uses_set_null(self):
        assignee = User.objects.create_user(
            username="asignado", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        ticket = Ticket.objects.create_ticket(
            title="Se puede reasignar",
            description="desc",
            category=self.category,
            created_by=self.creator,
        )
        ticket.assigned_to = assignee
        ticket.save()

        assignee.delete()
        ticket.refresh_from_db()
        self.assertIsNone(ticket.assigned_to)

    def test_ticket_number_is_unique_and_formatted(self):
        ticket_1 = Ticket.objects.create_ticket(
            title="Uno", description="desc", category=self.category,
            created_by=self.creator,
        )
        ticket_2 = Ticket.objects.create_ticket(
            title="Dos", description="desc", category=self.category,
            created_by=self.creator,
        )
        self.assertRegex(ticket_1.ticket_number, r"^TK-\d{6}$")
        self.assertRegex(ticket_2.ticket_number, r"^TK-\d{6}$")
        self.assertNotEqual(ticket_1.ticket_number, ticket_2.ticket_number)

    def test_initial_ticket_history_is_created(self):
        ticket = Ticket.objects.create_ticket(
            title="Con historial",
            description="desc",
            category=self.category,
            created_by=self.creator,
        )
        history = TicketHistory.objects.filter(ticket=ticket)
        self.assertEqual(history.count(), 1)
        entry = history.first()
        self.assertEqual(entry.status, Ticket.Status.PENDING)
        self.assertEqual(entry.changed_by, self.creator)

    def test_assigned_to_from_another_area_is_invalid(self):
        other_area_user = User.objects.create_user(
            username="otro_area", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.other_area,
        )
        ticket = Ticket.objects.create_ticket(
            title="Área incorrecta",
            description="desc",
            category=self.category,
            created_by=self.creator,
        )
        ticket.assigned_to = other_area_user
        with self.assertRaises(ValidationError):
            ticket.full_clean()

    def test_assigned_to_from_same_area_is_valid(self):
        same_area_user = User.objects.create_user(
            username="mismo_area", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        ticket = Ticket.objects.create_ticket(
            title="Área correcta",
            description="desc",
            category=self.category,
            created_by=self.creator,
        )
        ticket.assigned_to = same_area_user
        ticket.full_clean()  # should not raise


class TicketPermissionTests(TestCase):
    def setUp(self):
        self.area_ti = Area.objects.create(name="TI")
        self.area_rrhh = Area.objects.create(name="RRHH")
        self.category = Category.objects.create(name="Hardware", area=self.area_ti)

        self.employee = User.objects.create_user(
            username="empleado1", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area_ti,
        )
        self.other_employee = User.objects.create_user(
            username="empleado2", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area_ti,
        )
        self.area_manager = User.objects.create_user(
            username="jefe_ti", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area_ti,
        )
        self.other_area_manager = User.objects.create_user(
            username="jefe_rrhh", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area_rrhh,
        )
        self.admin_user = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )
        self.management_user = User.objects.create_user(
            username="direccion1", password="pass12345", role=User.Role.MANAGEMENT,
        )

        self.ticket = Ticket.objects.create_ticket(
            title="Impresora no funciona",
            description="La impresora del piso 2 no enciende.",
            category=self.category,
            created_by=self.employee,
        )

    def test_employee_can_create_ticket(self):
        self.client.login(username="empleado1", password="pass12345")
        response = self.client.post(
            reverse("tickets:create"),
            {
                "title": "Nuevo problema",
                "description": "Detalle del problema",
                "category": self.category.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ticket.objects.filter(created_by=self.employee).count(), 2)

    def test_area_manager_cannot_create_ticket(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.post(
            reverse("tickets:create"),
            {
                "title": "No debería crearse",
                "description": "Detalle del problema",
                "category": self.category.pk,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            Ticket.objects.filter(title="No debería crearse").count(), 0
        )

    def test_admin_cannot_create_ticket(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("tickets:create"),
            {
                "title": "No debería crearse",
                "description": "Detalle del problema",
                "category": self.category.pk,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            Ticket.objects.filter(title="No debería crearse").count(), 0
        )

    def test_management_cannot_create_ticket(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.post(
            reverse("tickets:create"),
            {
                "title": "No debería crearse",
                "description": "Detalle del problema",
                "category": self.category.pk,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            Ticket.objects.filter(title="No debería crearse").count(), 0
        )

    def test_employee_can_view_own_ticket(self):
        self.client.login(username="empleado1", password="pass12345")
        response = self.client.get(reverse("tickets:detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)

    def test_employee_cannot_view_others_ticket(self):
        self.client.login(username="empleado2", password="pass12345")
        response = self.client.get(reverse("tickets:detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 404)

    def test_area_manager_cannot_view_other_area_ticket(self):
        self.client.login(username="jefe_rrhh", password="pass12345")
        response = self.client.get(reverse("tickets:detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 404)

    def test_admin_can_view_any_ticket(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(reverse("tickets:detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)


class TicketAssignmentViewTests(TestCase):
    """Manual (re)assignment permissions, exercised through the view layer."""

    def setUp(self):
        self.area_ti = Area.objects.create(name="TI")
        self.area_rrhh = Area.objects.create(name="RRHH")
        self.category = Category.objects.create(name="Hardware", area=self.area_ti)

        self.employee = User.objects.create_user(
            username="empleado1", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area_ti,
        )
        self.manager_ti = User.objects.create_user(
            username="jefe_ti", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area_ti,
        )
        self.other_manager_ti = User.objects.create_user(
            username="jefe_ti_2", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area_ti,
        )
        self.manager_rrhh = User.objects.create_user(
            username="jefe_rrhh", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area_rrhh,
        )
        self.admin_user = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )
        self.management_user = User.objects.create_user(
            username="direccion1", password="pass12345", role=User.Role.MANAGEMENT,
        )

        self.ticket = Ticket.objects.create_ticket(
            title="Impresora no funciona",
            description="desc",
            category=self.category,
            created_by=self.employee,
        )

    def test_ticket_creation_triggers_automatic_assignment(self):
        self.client.login(username="empleado1", password="pass12345")
        response = self.client.post(
            reverse("tickets:create"),
            {
                "title": "Nuevo con auto asignación",
                "description": "desc",
                "category": self.category.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(title="Nuevo con auto asignación")
        self.assertEqual(ticket.assigned_to, self.manager_ti)
        self.assertEqual(ticket.status, Ticket.Status.PENDING)

    def test_employee_cannot_assign(self):
        self.client.login(username="empleado1", password="pass12345")
        response = self.client.get(reverse("tickets:assign", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 403)

    def test_management_cannot_assign(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(reverse("tickets:assign", args=[self.ticket.pk]))
        # Management has no visibility into any ticket in this block, so
        # the ticket lookup itself fails before the permission check.
        self.assertEqual(response.status_code, 404)

    def test_area_manager_can_assign_within_own_area(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.post(
            reverse("tickets:assign", args=[self.ticket.pk]),
            {"assigned_to": self.other_manager_ti.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.assigned_to, self.other_manager_ti)

    def test_area_manager_cannot_assign_ticket_of_another_area(self):
        self.client.login(username="jefe_rrhh", password="pass12345")
        response = self.client.get(reverse("tickets:assign", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 404)

    def test_area_manager_cannot_assign_to_manager_of_another_area(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.post(
            reverse("tickets:assign", args=[self.ticket.pk]),
            {"assigned_to": self.manager_rrhh.pk},
        )
        self.assertEqual(response.status_code, 200)  # re-renders form with error
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.assigned_to)

    def test_admin_can_assign_globally(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("tickets:assign", args=[self.ticket.pk]),
            {"assigned_to": self.manager_ti.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.assigned_to, self.manager_ti)
