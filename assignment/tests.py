from django.test import TestCase

from administration.models import Area, Category
from notifications.models import Notification
from tickets.models import Ticket
from users.models import User

from .models import AreaAssignmentCursor, TicketAssignmentHistory
from .services import AssignmentError, assign_ticket, auto_assign_ticket


def make_ticket(category, created_by, title="Ticket"):
    return Ticket.objects.create_ticket(
        title=title, description="desc", category=category, created_by=created_by
    )


class RoundRobinTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )

    def make_manager(self, username, area=None, is_active=True):
        return User.objects.create_user(
            username=username, password="pass12345",
            role=User.Role.AREA_MANAGER, area=area or self.area,
            is_active=is_active,
        )

    def test_single_manager_receives_all_tickets(self):
        manager = self.make_manager("manager_a")
        for i in range(3):
            ticket = make_ticket(self.category, self.employee, f"Ticket {i}")
            auto_assign_ticket(ticket)
            ticket.refresh_from_db()
            self.assertEqual(ticket.assigned_to, manager)

    def test_two_managers_alternate(self):
        manager_a = self.make_manager("manager_a")
        manager_b = self.make_manager("manager_b")
        expected = [manager_a, manager_b, manager_a, manager_b]
        for i, expected_manager in enumerate(expected):
            ticket = make_ticket(self.category, self.employee, f"Ticket {i}")
            auto_assign_ticket(ticket)
            ticket.refresh_from_db()
            self.assertEqual(ticket.assigned_to, expected_manager)

    def test_three_managers_cycle(self):
        manager_a = self.make_manager("manager_a")
        manager_b = self.make_manager("manager_b")
        manager_c = self.make_manager("manager_c")
        expected = [manager_a, manager_b, manager_c, manager_a, manager_b]
        for i, expected_manager in enumerate(expected):
            ticket = make_ticket(self.category, self.employee, f"Ticket {i}")
            auto_assign_ticket(ticket)
            ticket.refresh_from_db()
            self.assertEqual(ticket.assigned_to, expected_manager)

    def test_only_active_managers_participate(self):
        active_manager = self.make_manager("activo")
        self.make_manager("inactivo", is_active=False)
        for i in range(3):
            ticket = make_ticket(self.category, self.employee, f"Ticket {i}")
            auto_assign_ticket(ticket)
            ticket.refresh_from_db()
            self.assertEqual(ticket.assigned_to, active_manager)

    def test_continues_correctly_when_last_responsible_becomes_unavailable(self):
        manager_a = self.make_manager("manager_a")
        manager_b = self.make_manager("manager_b")
        manager_c = self.make_manager("manager_c")

        ticket_1 = make_ticket(self.category, self.employee, "Uno")
        auto_assign_ticket(ticket_1)
        ticket_1.refresh_from_db()
        self.assertEqual(ticket_1.assigned_to, manager_a)

        # manager_a (the cursor's last assigned manager) stops being
        # available. The cycle must restart from the first manager that
        # is still active, not error out or get stuck.
        manager_a.is_active = False
        manager_a.save(update_fields=["is_active"])

        ticket_2 = make_ticket(self.category, self.employee, "Dos")
        auto_assign_ticket(ticket_2)
        ticket_2.refresh_from_db()
        self.assertEqual(ticket_2.assigned_to, manager_b)

        ticket_3 = make_ticket(self.category, self.employee, "Tres")
        auto_assign_ticket(ticket_3)
        ticket_3.refresh_from_db()
        self.assertEqual(ticket_3.assigned_to, manager_c)

    def test_only_managers_of_the_matching_area_participate(self):
        other_area = Area.objects.create(name="RRHH")
        self.make_manager("otro_area_manager", area=other_area)
        ticket = make_ticket(self.category, self.employee)
        auto_assign_ticket(ticket)
        ticket.refresh_from_db()
        self.assertIsNone(ticket.assigned_to)

    def test_employees_admins_and_management_never_participate(self):
        User.objects.create_user(
            username="otro_empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )
        User.objects.create_user(
            username="direccion1", password="pass12345", role=User.Role.MANAGEMENT,
        )
        ticket = make_ticket(self.category, self.employee)
        auto_assign_ticket(ticket)
        ticket.refresh_from_db()
        self.assertIsNone(ticket.assigned_to)


class NoResponsibleAvailableTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )

    def test_ticket_can_be_created_without_a_responsible(self):
        ticket = make_ticket(self.category, self.employee)
        auto_assign_ticket(ticket)  # should not raise
        ticket.refresh_from_db()
        self.assertIsNone(ticket.assigned_to)
        self.assertEqual(ticket.status, Ticket.Status.PENDING)


class AreaRestrictionTests(TestCase):
    def setUp(self):
        self.area_ti = Area.objects.create(name="TI")
        self.area_mant = Area.objects.create(name="Mantenimiento")
        self.category = Category.objects.create(name="Hardware", area=self.area_ti)
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area_ti,
        )
        self.manager_mant = User.objects.create_user(
            username="jefe_mant", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area_mant,
        )

    def test_cannot_assign_ticket_to_manager_of_another_area(self):
        ticket = make_ticket(self.category, self.employee)
        with self.assertRaises(AssignmentError):
            assign_ticket(ticket, assigned_to=self.manager_mant, changed_by=self.employee)


class ReassignmentTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.manager_a = User.objects.create_user(
            username="manager_a", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.manager_b = User.objects.create_user(
            username="manager_b", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )

    def test_reassignment_updates_assigned_to_and_records_history(self):
        ticket = make_ticket(self.category, self.employee)
        assign_ticket(ticket, assigned_to=self.manager_a, changed_by=self.admin)

        assign_ticket(ticket, assigned_to=self.manager_b, changed_by=self.admin)
        ticket.refresh_from_db()

        self.assertEqual(ticket.assigned_to, self.manager_b)
        entries = list(TicketAssignmentHistory.objects.filter(ticket=ticket))
        self.assertEqual(len(entries), 2)
        last_entry = entries[-1]
        self.assertEqual(last_entry.previous_assigned_to, self.manager_a)
        self.assertEqual(last_entry.new_assigned_to, self.manager_b)
        self.assertEqual(last_entry.changed_by, self.admin)

    def test_reassigning_to_the_same_manager_creates_no_extra_history(self):
        ticket = make_ticket(self.category, self.employee)
        assign_ticket(ticket, assigned_to=self.manager_a, changed_by=self.admin)
        self.assertEqual(
            TicketAssignmentHistory.objects.filter(ticket=ticket).count(), 1
        )

        assign_ticket(ticket, assigned_to=self.manager_a, changed_by=self.admin)
        self.assertEqual(
            TicketAssignmentHistory.objects.filter(ticket=ticket).count(), 1
        )

    def test_automatic_assignment_is_recorded_with_no_human_actor(self):
        ticket = make_ticket(self.category, self.employee)
        auto_assign_ticket(ticket)
        entry = TicketAssignmentHistory.objects.get(ticket=ticket)
        self.assertIsNone(entry.changed_by)
        self.assertIsNone(entry.previous_assigned_to)
        self.assertEqual(entry.new_assigned_to, self.manager_a)

    def test_manual_reassignment_does_not_break_round_robin_cursor(self):
        # Automatic assignment: ticket 1 -> manager_a, ticket 2 -> manager_b.
        ticket_1 = make_ticket(self.category, self.employee, "Uno")
        auto_assign_ticket(ticket_1)
        ticket_2 = make_ticket(self.category, self.employee, "Dos")
        auto_assign_ticket(ticket_2)

        # Manual reassignment of ticket 1 away from manager_a must not
        # affect the Round Robin cursor, which only automatic assignment
        # updates.
        assign_ticket(ticket_1, assigned_to=self.manager_b, changed_by=self.admin)

        # The cursor should still reflect the last *automatic* assignment
        # (manager_b, from ticket_2), unaffected by the manual reassignment.
        cursor = AreaAssignmentCursor.objects.get(area=self.area)
        self.assertEqual(cursor.last_assigned_to, self.manager_b)

        # The next automatic assignment must continue the cycle from the
        # last automatic assignment (manager_b -> manager_a), unaffected
        # by the manual reassignment above.
        ticket_3 = make_ticket(self.category, self.employee, "Tres")
        auto_assign_ticket(ticket_3)
        ticket_3.refresh_from_db()
        self.assertEqual(ticket_3.assigned_to, self.manager_a)


class AssignmentNotificationTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(name="TI")
        self.other_area = Area.objects.create(name="Mantenimiento")
        self.category = Category.objects.create(name="Hardware", area=self.area)
        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area,
        )
        self.manager_a = User.objects.create_user(
            username="manager_a", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.manager_b = User.objects.create_user(
            username="manager_b", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.other_area_manager = User.objects.create_user(
            username="jefe_mant", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.other_area,
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )

    def test_automatic_assignment_notifies_the_new_manager(self):
        ticket = make_ticket(self.category, self.employee)
        auto_assign_ticket(ticket)

        notifications = Notification.objects.filter(
            recipient=self.manager_a, ticket=ticket
        )
        self.assertEqual(notifications.count(), 1)
        notification = notifications.first()
        self.assertEqual(
            notification.notification_type, Notification.NotificationType.TICKET_ASSIGNED
        )
        self.assertIn(ticket.ticket_number, notification.message)

    def test_no_manager_available_generates_no_notification(self):
        area_without_managers = Area.objects.create(name="RRHH")
        empty_category = Category.objects.create(
            name="Sin managers", area=area_without_managers
        )
        ticket = make_ticket(empty_category, self.employee)
        auto_assign_ticket(ticket)
        self.assertIsNone(ticket.assigned_to)
        self.assertEqual(Notification.objects.filter(ticket=ticket).count(), 0)

    def test_manual_first_assignment_notifies_new_manager_as_assigned(self):
        # A manual assignment of a still-unassigned ticket (previous=None)
        # must be classified the same way as an automatic first
        # assignment: TICKET_ASSIGNED, not TICKET_REASSIGNED.
        ticket = make_ticket(self.category, self.employee)
        assign_ticket(ticket, assigned_to=self.manager_a, changed_by=self.admin)

        notifications = Notification.objects.filter(
            recipient=self.manager_a, ticket=ticket
        )
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(
            notifications.first().notification_type,
            Notification.NotificationType.TICKET_ASSIGNED,
        )

    def test_manual_reassignment_notifies_only_the_new_manager(self):
        ticket = make_ticket(self.category, self.employee)
        assign_ticket(ticket, assigned_to=self.manager_a, changed_by=self.admin)
        Notification.objects.filter(ticket=ticket).delete()  # isolate the reassignment

        assign_ticket(ticket, assigned_to=self.manager_b, changed_by=self.admin)

        new_manager_notifications = Notification.objects.filter(
            recipient=self.manager_b, ticket=ticket
        )
        self.assertEqual(new_manager_notifications.count(), 1)
        self.assertEqual(
            new_manager_notifications.first().notification_type,
            Notification.NotificationType.TICKET_REASSIGNED,
        )
        # The previous responsible must not be notified of losing the ticket.
        self.assertEqual(
            Notification.objects.filter(recipient=self.manager_a, ticket=ticket).count(),
            0,
        )

    def test_reassigning_to_the_same_manager_creates_no_duplicate_notification(self):
        ticket = make_ticket(self.category, self.employee)
        assign_ticket(ticket, assigned_to=self.manager_a, changed_by=self.admin)
        count_before = Notification.objects.filter(ticket=ticket).count()

        assign_ticket(ticket, assigned_to=self.manager_a, changed_by=self.admin)

        self.assertEqual(
            Notification.objects.filter(ticket=ticket).count(), count_before
        )

    def test_failed_assignment_leaves_no_orphaned_notification(self):
        ticket = make_ticket(self.category, self.employee)
        with self.assertRaises(AssignmentError):
            assign_ticket(
                ticket, assigned_to=self.other_area_manager, changed_by=self.admin
            )
        self.assertEqual(Notification.objects.filter(ticket=ticket).count(), 0)
