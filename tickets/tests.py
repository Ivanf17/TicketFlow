from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import ProtectedError
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from administration.models import Area, Category
from assignment.services import auto_assign_ticket
from notifications.models import Notification
from users.models import User

from .models import Ticket, TicketComment, TicketHistory
from .services import StatusTransitionError, change_ticket_status


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
        self.assertIsNone(entry.previous_status)
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

    def test_management_sees_no_tickets_in_ticket_list(self):
        # Regression guard for Block 7: the dashboard grants Management a
        # *global* view for reporting purposes only (reports.permissions
        # .get_dashboard_tickets_queryset). tickets.permissions
        # .get_visible_tickets, used by this view, must keep giving
        # Management no ticket-lifecycle access at all, exactly as before
        # the dashboard existed.
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(reverse("tickets:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["page_obj"]), [])

    def test_management_cannot_view_ticket_detail(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(reverse("tickets:detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 404)


class TicketListCreateButtonVisibilityTests(TestCase):
    """UI regression guard: ticket_list.html must only offer "Nuevo
    ticket" to roles that ticket_create actually lets through. Showing
    it to everyone led area_manager/admin/management into a 403 on
    click, even though the server-side permission itself was correct.
    """

    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.employee = User.objects.create_user(
            username="empleado1", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.area_manager = User.objects.create_user(
            username="jefe_ti", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.admin_user = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )
        self.management_user = User.objects.create_user(
            username="direccion1", password="pass12345", role=User.Role.MANAGEMENT,
        )

    def test_employee_sees_create_button(self):
        self.client.login(username="empleado1", password="pass12345")
        response = self.client.get(reverse("tickets:list"))
        self.assertContains(response, reverse("tickets:create"))
        self.assertContains(response, "Nuevo ticket")

    def test_area_manager_does_not_see_create_button(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(reverse("tickets:list"))
        self.assertNotContains(response, reverse("tickets:create"))
        self.assertNotContains(response, "Nuevo ticket")

    def test_admin_does_not_see_create_button(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(reverse("tickets:list"))
        self.assertNotContains(response, reverse("tickets:create"))
        self.assertNotContains(response, "Nuevo ticket")

    def test_management_does_not_see_create_button(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(reverse("tickets:list"))
        self.assertNotContains(response, reverse("tickets:create"))
        self.assertNotContains(response, "Nuevo ticket")


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


class TicketStatusTransitionTests(TestCase):
    """Service-level tests for the centralized status state machine."""

    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.manager = User.objects.create_user(
            username="jefe_ti", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.ticket = Ticket.objects.create_ticket(
            title="Impresora rota", description="desc",
            category=self.category, created_by=self.employee,
        )

    def test_ticket_starts_pending_with_single_initial_history_entry(self):
        self.assertEqual(self.ticket.status, Ticket.Status.PENDING)
        entries = list(TicketHistory.objects.filter(ticket=self.ticket))
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0].previous_status)
        self.assertEqual(entries[0].status, Ticket.Status.PENDING)

    def test_pending_to_in_process_succeeds(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROCESS)

    def test_in_process_to_resolved_succeeds(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
        )
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)

    def test_pending_to_resolved_is_rejected(self):
        with self.assertRaises(StatusTransitionError):
            change_ticket_status(
                self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager
            )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.PENDING)
        self.assertEqual(TicketHistory.objects.filter(ticket=self.ticket).count(), 1)

    def test_in_process_to_pending_is_rejected(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
        )
        with self.assertRaises(StatusTransitionError):
            change_ticket_status(
                self.ticket, new_status=Ticket.Status.PENDING, changed_by=self.manager
            )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROCESS)

    def test_resolved_to_in_process_is_rejected(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
        )
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager
        )
        with self.assertRaises(StatusTransitionError):
            change_ticket_status(
                self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
            )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)

    def test_resolved_to_pending_is_rejected(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
        )
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager
        )
        with self.assertRaises(StatusTransitionError):
            change_ticket_status(
                self.ticket, new_status=Ticket.Status.PENDING, changed_by=self.manager
            )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)

    def test_resolved_to_resolved_creates_no_extra_history(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
        )
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager
        )
        count_before = TicketHistory.objects.filter(ticket=self.ticket).count()
        with self.assertRaises(StatusTransitionError):
            change_ticket_status(
                self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager
            )
        self.assertEqual(
            TicketHistory.objects.filter(ticket=self.ticket).count(), count_before
        )

    def test_history_records_previous_and_new_status_user_and_order(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
        )
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager
        )
        entries = list(
            TicketHistory.objects.filter(ticket=self.ticket).order_by("created_at")
        )
        self.assertEqual(len(entries), 3)  # initial creation + 2 real transitions
        self.assertIsNone(entries[0].previous_status)
        self.assertEqual(entries[0].status, Ticket.Status.PENDING)
        self.assertEqual(entries[1].previous_status, Ticket.Status.PENDING)
        self.assertEqual(entries[1].status, Ticket.Status.IN_PROCESS)
        self.assertEqual(entries[1].changed_by, self.manager)
        self.assertEqual(entries[2].previous_status, Ticket.Status.IN_PROCESS)
        self.assertEqual(entries[2].status, Ticket.Status.RESOLVED)
        self.assertEqual(entries[2].changed_by, self.manager)
        self.assertLessEqual(entries[0].created_at, entries[1].created_at)
        self.assertLessEqual(entries[1].created_at, entries[2].created_at)


class TicketStatusViewTests(TestCase):
    """View-level permission and security tests for status changes."""

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
            title="Impresora no funciona", description="desc",
            category=self.category, created_by=self.employee,
        )

    def change_status_url(self, ticket=None):
        return reverse("tickets:change_status", args=[(ticket or self.ticket).pk])

    def test_login_required_for_status_change(self):
        response = self.client.post(
            self.change_status_url(), {"status": Ticket.Status.IN_PROCESS}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_employee_cannot_change_status(self):
        self.client.login(username="empleado1", password="pass12345")
        response = self.client.post(
            self.change_status_url(), {"status": Ticket.Status.IN_PROCESS}
        )
        self.assertEqual(response.status_code, 403)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.PENDING)

    def test_management_cannot_change_status(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.post(
            self.change_status_url(), {"status": Ticket.Status.IN_PROCESS}
        )
        # Management has no visibility into any ticket in this block, so
        # the ticket lookup itself fails before the permission check.
        self.assertEqual(response.status_code, 404)

    def test_area_manager_can_change_status_of_own_area_ticket(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.post(
            self.change_status_url(), {"status": Ticket.Status.IN_PROCESS}
        )
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROCESS)

    def test_area_manager_cannot_change_status_of_other_area_ticket(self):
        self.client.login(username="jefe_rrhh", password="pass12345")
        response = self.client.post(
            self.change_status_url(), {"status": Ticket.Status.IN_PROCESS}
        )
        self.assertEqual(response.status_code, 404)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.PENDING)

    def test_admin_can_change_status_of_any_ticket(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            self.change_status_url(), {"status": Ticket.Status.IN_PROCESS}
        )
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROCESS)

    def test_manipulated_post_cannot_skip_pending_to_resolved(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.post(
            self.change_status_url(), {"status": Ticket.Status.RESOLVED}
        )
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.PENDING)
        self.assertEqual(TicketHistory.objects.filter(ticket=self.ticket).count(), 1)

    def test_manipulated_post_cannot_go_in_process_to_pending(self):
        self.client.login(username="jefe_ti", password="pass12345")
        self.client.post(self.change_status_url(), {"status": Ticket.Status.IN_PROCESS})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROCESS)
        history_count = TicketHistory.objects.filter(ticket=self.ticket).count()

        response = self.client.post(
            self.change_status_url(), {"status": Ticket.Status.PENDING}
        )
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROCESS)
        self.assertEqual(
            TicketHistory.objects.filter(ticket=self.ticket).count(), history_count
        )

    def test_manipulated_post_cannot_reopen_resolved_to_in_process(self):
        self.client.login(username="jefe_ti", password="pass12345")
        self.client.post(self.change_status_url(), {"status": Ticket.Status.IN_PROCESS})
        self.client.post(self.change_status_url(), {"status": Ticket.Status.RESOLVED})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)
        history_count = TicketHistory.objects.filter(ticket=self.ticket).count()

        response = self.client.post(
            self.change_status_url(), {"status": Ticket.Status.IN_PROCESS}
        )
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)
        self.assertEqual(
            TicketHistory.objects.filter(ticket=self.ticket).count(), history_count
        )

    def test_area_manager_cannot_bypass_area_restriction_via_manipulated_post(self):
        self.client.login(username="jefe_rrhh", password="pass12345")
        response = self.client.post(
            self.change_status_url(), {"status": Ticket.Status.IN_PROCESS}
        )
        self.assertEqual(response.status_code, 404)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.PENDING)

    def test_resolved_ticket_has_no_further_actions(self):
        self.client.login(username="jefe_ti", password="pass12345")
        self.client.post(self.change_status_url(), {"status": Ticket.Status.IN_PROCESS})
        self.client.post(self.change_status_url(), {"status": Ticket.Status.RESOLVED})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)

        response = self.client.post(
            self.change_status_url(), {"status": Ticket.Status.IN_PROCESS}
        )
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)
        self.assertEqual(TicketHistory.objects.filter(ticket=self.ticket).count(), 3)


class TicketStatusNotificationTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.manager = User.objects.create_user(
            username="jefe_ti", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.ticket = Ticket.objects.create_ticket(
            title="Impresora rota", description="desc",
            category=self.category, created_by=self.employee,
        )

    def test_pending_to_in_process_notifies_creator(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
        )
        notifications = Notification.objects.filter(
            recipient=self.employee, ticket=self.ticket
        )
        self.assertEqual(notifications.count(), 1)
        notification = notifications.first()
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.TICKET_STATUS_CHANGED,
        )
        self.assertIn("En proceso", notification.message)

    def test_in_process_to_resolved_notifies_creator(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
        )
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager
        )
        notifications = Notification.objects.filter(
            recipient=self.employee,
            ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_STATUS_CHANGED,
        )
        self.assertEqual(notifications.count(), 2)
        # Order by id (monotonic, unlike created_at which can tie on
        # platforms with coarse clock resolution for two rapid creates).
        last_notification = notifications.order_by("id").last()
        self.assertIn("Resuelto", last_notification.message)

    def test_invalid_transition_generates_no_notification(self):
        with self.assertRaises(StatusTransitionError):
            change_ticket_status(
                self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager
            )
        self.assertEqual(Notification.objects.filter(ticket=self.ticket).count(), 0)

    def test_resolved_reopen_attempt_generates_no_notification(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
        )
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager
        )
        count_before = Notification.objects.filter(ticket=self.ticket).count()

        with self.assertRaises(StatusTransitionError):
            change_ticket_status(
                self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager
            )
        self.assertEqual(
            Notification.objects.filter(ticket=self.ticket).count(), count_before
        )


class TicketCommentTests(TestCase):
    """Block 9: TicketComment visibility/creation, reusing
    get_visible_tickets exactly like ticket_detail (no separate
    permission matrix), and its RESOLVED/state-machine independence.
    """

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
        self.manager_ti = User.objects.create_user(
            username="jefe_ti", password="pass12345",
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
            title="Impresora no funciona", description="desc",
            category=self.category, created_by=self.employee,
        )
        self.ticket.assigned_to = self.manager_ti
        self.ticket.save()

    def comment_url(self, ticket=None):
        return reverse("tickets:comment_create", args=[(ticket or self.ticket).pk])

    def test_employee_can_comment_on_own_ticket(self):
        self.client.login(username="empleado1", password="pass12345")
        response = self.client.post(self.comment_url(), {"content": "Hola"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TicketComment.objects.filter(ticket=self.ticket).count(), 1)
        comment = TicketComment.objects.get(ticket=self.ticket)
        self.assertEqual(comment.author, self.employee)
        self.assertEqual(comment.content, "Hola")

    def test_employee_cannot_comment_on_others_ticket(self):
        self.client.login(username="empleado2", password="pass12345")
        response = self.client.post(self.comment_url(), {"content": "Intento"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(TicketComment.objects.filter(ticket=self.ticket).count(), 0)

    def test_area_manager_can_comment_on_own_area_ticket(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.post(self.comment_url(), {"content": "Revisando"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TicketComment.objects.filter(ticket=self.ticket).count(), 1)

    def test_area_manager_cannot_comment_on_other_area_ticket(self):
        self.client.login(username="jefe_rrhh", password="pass12345")
        response = self.client.post(self.comment_url(), {"content": "Intento"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(TicketComment.objects.filter(ticket=self.ticket).count(), 0)

    def test_admin_can_comment_on_any_ticket(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(self.comment_url(), {"content": "Nota admin"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TicketComment.objects.filter(ticket=self.ticket).count(), 1)

    def test_management_cannot_comment(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.post(self.comment_url(), {"content": "Intento"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(TicketComment.objects.filter(ticket=self.ticket).count(), 0)

    def test_get_request_is_not_allowed(self):
        self.client.login(username="empleado1", password="pass12345")
        response = self.client.get(self.comment_url())
        self.assertEqual(response.status_code, 405)

    def test_empty_content_is_rejected(self):
        self.client.login(username="empleado1", password="pass12345")
        response = self.client.post(self.comment_url(), {"content": ""})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TicketComment.objects.filter(ticket=self.ticket).count(), 0)

    def test_can_comment_on_resolved_ticket(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager_ti
        )
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager_ti
        )
        self.client.login(username="empleado1", password="pass12345")
        response = self.client.post(self.comment_url(), {"content": "Gracias"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TicketComment.objects.filter(ticket=self.ticket).count(), 1)

    def test_comment_does_not_change_ticket_status_or_reopen_resolved(self):
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager_ti
        )
        change_ticket_status(
            self.ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager_ti
        )
        history_count = TicketHistory.objects.filter(ticket=self.ticket).count()

        self.client.login(username="empleado1", password="pass12345")
        self.client.post(self.comment_url(), {"content": "Comentario"})

        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)
        self.assertEqual(
            TicketHistory.objects.filter(ticket=self.ticket).count(), history_count
        )

    def test_comment_does_not_change_assignment(self):
        self.client.login(username="admin1", password="pass12345")
        self.client.post(self.comment_url(), {"content": "Comentario"})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.assigned_to, self.manager_ti)

    def test_comments_are_ordered_oldest_first(self):
        self.client.login(username="empleado1", password="pass12345")
        self.client.post(self.comment_url(), {"content": "Primero"})
        self.client.post(self.comment_url(), {"content": "Segundo"})
        contents = list(
            TicketComment.objects.filter(ticket=self.ticket).values_list(
                "content", flat=True
            )
        )
        self.assertEqual(contents, ["Primero", "Segundo"])


class TicketCommentNotificationTests(TestCase):
    """Block 9: who gets notified when a comment is added."""

    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.manager = User.objects.create_user(
            username="jefe_ti", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.admin_user = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )
        self.ticket = Ticket.objects.create_ticket(
            title="Impresora rota", description="desc",
            category=self.category, created_by=self.employee,
        )
        self.ticket.assigned_to = self.manager
        self.ticket.save()

    def comment_url(self):
        return reverse("tickets:comment_create", args=[self.ticket.pk])

    def test_employee_comment_notifies_assigned_to(self):
        self.client.login(username="empleado", password="pass12345")
        self.client.post(self.comment_url(), {"content": "Sigue fallando"})
        notifications = Notification.objects.filter(
            recipient=self.manager,
            ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_COMMENT_ADDED,
        )
        self.assertEqual(notifications.count(), 1)

    def test_area_manager_comment_notifies_creator(self):
        self.client.login(username="jefe_ti", password="pass12345")
        self.client.post(self.comment_url(), {"content": "Ya lo estoy viendo"})
        notifications = Notification.objects.filter(
            recipient=self.employee,
            ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_COMMENT_ADDED,
        )
        self.assertEqual(notifications.count(), 1)

    def test_admin_comment_notifies_creator(self):
        self.client.login(username="admin1", password="pass12345")
        self.client.post(self.comment_url(), {"content": "Nota admin"})
        notifications = Notification.objects.filter(
            recipient=self.employee,
            ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_COMMENT_ADDED,
        )
        self.assertEqual(notifications.count(), 1)

    def test_no_self_notification(self):
        # Force the (otherwise unreachable via the UI, since only
        # employees create tickets and only area_managers get assigned)
        # edge case where the computed recipient equals the author, to
        # confirm the guard in notify_ticket_comment_added holds.
        Ticket.objects.filter(pk=self.ticket.pk).update(assigned_to=self.employee)
        self.ticket.refresh_from_db()
        self.client.login(username="empleado", password="pass12345")
        self.client.post(self.comment_url(), {"content": "Nota"})
        self.assertEqual(
            Notification.objects.filter(
                ticket=self.ticket,
                notification_type=Notification.NotificationType.TICKET_COMMENT_ADDED,
            ).count(),
            0,
        )

    def test_no_notification_without_assigned_to(self):
        self.ticket.assigned_to = None
        self.ticket.save()
        self.client.login(username="empleado", password="pass12345")
        self.client.post(self.comment_url(), {"content": "Nadie asignado"})
        self.assertEqual(
            Notification.objects.filter(
                ticket=self.ticket,
                notification_type=Notification.NotificationType.TICKET_COMMENT_ADDED,
            ).count(),
            0,
        )

    def test_invalid_comment_generates_no_notification(self):
        self.client.login(username="empleado", password="pass12345")
        self.client.post(self.comment_url(), {"content": ""})
        self.assertEqual(
            Notification.objects.filter(
                ticket=self.ticket,
                notification_type=Notification.NotificationType.TICKET_COMMENT_ADDED,
            ).count(),
            0,
        )


class TicketListPaginationTests(TestCase):
    """Block 9: ticket_list uses Paginator.get_page(), which must never
    turn an out-of-range or non-numeric ``?page=`` into a 500.
    """

    def setUp(self):
        from django.conf import settings

        self.page_size = settings.PAGE_SIZE
        self.area = Area.objects.create(name="TI")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.admin_user = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        for i in range(self.page_size + 3):
            Ticket.objects.create_ticket(
                title=f"Ticket {i}", description="desc",
                category=self.category, created_by=self.employee,
            )
        self.client.login(username="admin1", password="pass12345")

    def test_page_1_returns_at_most_page_size_items(self):
        response = self.client.get(reverse("tickets:list"), {"page": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), self.page_size)

    def test_out_of_range_page_falls_back_to_last_page_not_500(self):
        response = self.client.get(reverse("tickets:list"), {"page": 999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)

    def test_non_numeric_page_falls_back_to_first_page_not_500(self):
        response = self.client.get(reverse("tickets:list"), {"page": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)


class TicketListQueryCountTests(TestCase):
    """Block 10: locks in the select_related fix for ticket_list's N+1
    (category, category.area, created_by, assigned_to were each fetched
    with a separate query per row before the fix). A single ticket
    can't reveal an N+1 -- it must be checked against a bigger page too.
    """

    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        # An Area Manager so every ticket actually gets an assigned_to
        # (otherwise the assigned_to FK is always NULL and its would-be
        # per-row query never happens, hiding part of the N+1).
        User.objects.create_user(
            username="jefe_ti", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.client.login(username="admin1", password="pass12345")

    def _create_tickets(self, n):
        for i in range(n):
            ticket = Ticket.objects.create_ticket(
                title=f"Ticket {i}", description="desc",
                category=self.category, created_by=self.employee,
            )
            auto_assign_ticket(ticket)

    def test_query_count_does_not_grow_with_more_tickets(self):
        self._create_tickets(1)
        with CaptureQueriesContext(connection) as one_row:
            self.client.get(reverse("tickets:list"))
        baseline = len(one_row.captured_queries)

        self._create_tickets(9)  # 10 tickets total
        with self.assertNumQueries(baseline):
            self.client.get(reverse("tickets:list"))


class InactiveCategoryTicketCreationTests(TestCase):
    """Block 10: closes the test gap around tickets/forms.py:23
    (TicketCreateForm restricting `category` to active ones)."""

    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.active_category = Category.objects.create(
            name="Hardware", area=self.area, is_active=True
        )
        self.inactive_category = Category.objects.create(
            name="Descontinuada", area=self.area, is_active=False
        )
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.client.login(username="empleado", password="pass12345")

    def test_inactive_category_not_offered_in_create_form(self):
        response = self.client.get(reverse("tickets:create"))
        queryset = response.context["form"].fields["category"].queryset
        self.assertIn(self.active_category, queryset)
        self.assertNotIn(self.inactive_category, queryset)

    def test_direct_post_with_inactive_category_id_is_rejected(self):
        response = self.client.post(
            reverse("tickets:create"),
            {
                "title": "Intento con categoría inactiva",
                "description": "desc",
                "category": self.inactive_category.pk,
            },
        )
        self.assertEqual(response.status_code, 200)  # form re-rendered, invalid
        self.assertFalse(
            Ticket.objects.filter(title="Intento con categoría inactiva").exists()
        )

    def test_active_category_is_still_accepted(self):
        response = self.client.post(
            reverse("tickets:create"),
            {
                "title": "Con categoría activa",
                "description": "desc",
                "category": self.active_category.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Ticket.objects.filter(title="Con categoría activa").exists())


class TicketLifecycleAcceptanceTests(TestCase):
    """Block 10: end-to-end acceptance test. Walks the full ticket
    lifecycle through the Django test client with one real session per
    role (not isolated service calls), confirming every piece -- Round
    Robin, status transitions, notifications, history and the dashboard
    -- integrates the way an actual user would experience it.
    """

    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.manager = User.objects.create_user(
            username="jefe_ti", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )

    def test_full_ticket_lifecycle_across_roles(self):
        employee_client = Client()
        manager_client = Client()
        admin_client = Client()
        self.assertTrue(
            employee_client.login(username="empleado", password="pass12345")
        )
        self.assertTrue(
            manager_client.login(username="jefe_ti", password="pass12345")
        )
        self.assertTrue(admin_client.login(username="admin1", password="pass12345"))

        # 1. Employee creates a ticket and sees it in their own list, PENDING.
        response = employee_client.post(
            reverse("tickets:create"),
            {
                "title": "Impresora no enciende",
                "description": "La impresora del piso 2 no enciende.",
                "category": self.category.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(title="Impresora no enciende")
        self.assertEqual(ticket.status, Ticket.Status.PENDING)

        response = employee_client.get(reverse("tickets:list"))
        self.assertContains(response, ticket.ticket_number)
        self.assertContains(response, "Pendiente")

        # 2. Round Robin auto-assigned it to the area's only manager.
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_to, self.manager)

        # 3. The Area Manager sees it in their area and moves it forward.
        response = manager_client.get(reverse("tickets:list"))
        self.assertContains(response, ticket.ticket_number)

        response = manager_client.post(
            reverse("tickets:change_status", args=[ticket.pk]),
            {"status": Ticket.Status.IN_PROCESS},
        )
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.IN_PROCESS)

        # 4. The employee is notified and sees it in their own inbox.
        notification = Notification.objects.get(
            recipient=self.employee, ticket=ticket,
            notification_type=Notification.NotificationType.TICKET_STATUS_CHANGED,
        )
        response = employee_client.get(reverse("notifications:list"))
        self.assertContains(response, notification.title)

        # 5. The Area Manager resolves the ticket.
        response = manager_client.post(
            reverse("tickets:change_status", args=[ticket.pk]),
            {"status": Ticket.Status.RESOLVED},
        )
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.RESOLVED)

        # 6. The employee sees the final status and the full history.
        response = employee_client.get(reverse("tickets:detail", args=[ticket.pk]))
        self.assertContains(response, "Resuelto")
        history = list(TicketHistory.objects.filter(ticket=ticket).order_by("created_at"))
        self.assertEqual(len(history), 3)  # created + IN_PROCESS + RESOLVED
        self.assertIsNone(history[0].previous_status)
        self.assertEqual(history[1].status, Ticket.Status.IN_PROCESS)
        self.assertEqual(history[2].status, Ticket.Status.RESOLVED)

        # 7. The Admin sees it reflected in the dashboard's metrics.
        response = admin_client.get(reverse("reports:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total"], 1)
        self.assertEqual(response.context["resolved"], 1)
        self.assertContains(response, ticket.ticket_number)
