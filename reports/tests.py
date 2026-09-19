import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from administration.models import Area, Category
from assignment.services import assign_ticket
from tickets.models import Ticket, TicketHistory
from tickets.services import change_ticket_status
from users.models import User


def make_ticket(category, created_by, title="Ticket"):
    return Ticket.objects.create_ticket(
        title=title, description="desc", category=category, created_by=created_by
    )


def resolve_ticket_after(ticket, manager, *, created_at, hours_to_resolve):
    """Force a ticket through IN_PROCESS -> RESOLVED with a known,
    deterministic resolution duration, for testing the average.
    """
    Ticket.objects.filter(pk=ticket.pk).update(created_at=created_at)
    ticket.refresh_from_db()

    change_ticket_status(ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=manager)
    change_ticket_status(ticket, new_status=Ticket.Status.RESOLVED, changed_by=manager)

    resolved_entry = TicketHistory.objects.get(
        ticket=ticket, status=Ticket.Status.RESOLVED
    )
    TicketHistory.objects.filter(pk=resolved_entry.pk).update(
        created_at=created_at + datetime.timedelta(hours=hours_to_resolve)
    )
    ticket.refresh_from_db()
    return ticket


class DashboardBaseTestCase(TestCase):
    def setUp(self):
        self.area_ti = Area.objects.create(name="TI")
        self.area_rrhh = Area.objects.create(name="RRHH")
        self.category_ti = Category.objects.create(name="Hardware", area=self.area_ti)
        self.category_rrhh = Category.objects.create(
            name="Vacaciones", area=self.area_rrhh
        )

        self.employee = User.objects.create_user(
            username="empleado", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area_ti,
        )
        self.employee_rrhh = User.objects.create_user(
            username="empleado_rrhh", password="pass12345",
            role=User.Role.EMPLOYEE, area=self.area_rrhh,
        )
        self.manager_ti = User.objects.create_user(
            username="jefe_ti", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area_ti,
        )
        self.manager_rrhh = User.objects.create_user(
            username="jefe_rrhh", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area_rrhh,
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role=User.Role.ADMIN,
        )
        self.management = User.objects.create_user(
            username="direccion1", password="pass12345", role=User.Role.MANAGEMENT,
        )

    def dashboard_url(self, **params):
        url = reverse("reports:dashboard")
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            return f"{url}?{query}"
        return url


class DashboardPermissionTests(DashboardBaseTestCase):
    def test_login_required(self):
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_employee_cannot_access_dashboard(self):
        self.client.login(username="empleado", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 403)

    def test_area_manager_can_access_dashboard(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_dashboard(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 200)

    def test_management_can_access_dashboard(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 200)

    def test_employee_does_not_see_dashboard_link_in_nav(self):
        self.client.login(username="empleado", password="pass12345")
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, reverse("reports:dashboard"))

    def test_area_manager_sees_dashboard_link_in_nav(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("reports:dashboard"))

    def test_admin_sees_dashboard_link_in_nav(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("reports:dashboard"))

    def test_management_sees_dashboard_link_in_nav(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("reports:dashboard"))


class DashboardAreaScopeTests(DashboardBaseTestCase):
    def setUp(self):
        super().setUp()
        make_ticket(self.category_ti, self.employee, "TI 1")
        make_ticket(self.category_rrhh, self.employee_rrhh, "RRHH 1")

    def test_area_manager_only_sees_own_area_stats(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.context["total"], 1)

    def test_area_manager_manipulated_area_param_has_no_effect(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(self.dashboard_url(area=self.area_rrhh.pk))
        # Still scoped to TI: manipulating ?area= must not leak RRHH data.
        self.assertEqual(response.context["total"], 1)
        area_names = [row["category__area__name"] for row in response.context["by_area"]]
        self.assertNotIn("RRHH", area_names)

    def test_admin_can_filter_by_any_area(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url(area=self.area_rrhh.pk))
        self.assertEqual(response.context["total"], 1)
        area_names = [row["category__area__name"] for row in response.context["by_area"]]
        self.assertEqual(area_names, ["RRHH"])

    def test_management_can_filter_by_any_area(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(self.dashboard_url(area=self.area_ti.pk))
        self.assertEqual(response.context["total"], 1)
        area_names = [row["category__area__name"] for row in response.context["by_area"]]
        self.assertEqual(area_names, ["TI"])

    def test_admin_without_area_filter_sees_global_total(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.context["total"], 2)

    def test_area_manager_date_filter_stays_within_own_area(self):
        old_ti = make_ticket(self.category_ti, self.employee, "TI viejo")
        Ticket.objects.filter(pk=old_ti.pk).update(
            created_at=timezone.now() - datetime.timedelta(days=30)
        )
        self.client.login(username="jefe_ti", password="pass12345")
        start = (timezone.now() - datetime.timedelta(days=1)).date().isoformat()
        response = self.client.get(self.dashboard_url(start_date=start))
        # Only the recent TI ticket from setUp; RRHH and the old TI
        # ticket must not appear regardless of the date filter.
        self.assertEqual(response.context["total"], 1)
        area_names = [row["category__area__name"] for row in response.context["by_area"]]
        self.assertEqual(area_names, ["TI"])

    def test_area_manager_combining_foreign_area_param_and_dates_stays_restricted(self):
        self.client.login(username="jefe_ti", password="pass12345")
        start = (timezone.now() - datetime.timedelta(days=1)).date().isoformat()
        response = self.client.get(
            self.dashboard_url(area=self.area_rrhh.pk, start_date=start)
        )
        self.assertEqual(response.context["total"], 1)
        area_names = [row["category__area__name"] for row in response.context["by_area"]]
        self.assertEqual(area_names, ["TI"])

    def test_area_manager_without_area_sees_no_tickets_and_no_leak(self):
        # area=None bypasses User.clean() (only enforced via full_clean()
        # / forms, not on create_user()), so this is a real state the
        # dashboard can encounter and must handle safely.
        User.objects.create_user(
            username="jefe_sin_area", password="pass12345",
            role=User.Role.AREA_MANAGER,
        )
        self.client.login(username="jefe_sin_area", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total"], 0)
        self.assertEqual(response.context["by_area"], [])


class DashboardDateFilterTests(DashboardBaseTestCase):
    def setUp(self):
        super().setUp()
        self.old_ticket = make_ticket(self.category_ti, self.employee, "Viejo")
        Ticket.objects.filter(pk=self.old_ticket.pk).update(
            created_at=timezone.now() - datetime.timedelta(days=30)
        )
        self.recent_ticket = make_ticket(self.category_ti, self.employee, "Reciente")

    def test_start_date_filter(self):
        self.client.login(username="admin1", password="pass12345")
        start = (timezone.now() - datetime.timedelta(days=1)).date().isoformat()
        response = self.client.get(self.dashboard_url(start_date=start))
        self.assertEqual(response.context["total"], 1)

    def test_end_date_filter(self):
        self.client.login(username="admin1", password="pass12345")
        end = (timezone.now() - datetime.timedelta(days=20)).date().isoformat()
        response = self.client.get(self.dashboard_url(end_date=end))
        self.assertEqual(response.context["total"], 1)

    def test_date_range_filter(self):
        self.client.login(username="admin1", password="pass12345")
        start = (timezone.now() - datetime.timedelta(days=35)).date().isoformat()
        end = (timezone.now() - datetime.timedelta(days=25)).date().isoformat()
        response = self.client.get(self.dashboard_url(start_date=start, end_date=end))
        self.assertEqual(response.context["total"], 1)

    def test_area_and_date_filters_combined(self):
        make_ticket(self.category_rrhh, self.employee_rrhh, "RRHH reciente")
        self.client.login(username="admin1", password="pass12345")
        start = (timezone.now() - datetime.timedelta(days=1)).date().isoformat()
        response = self.client.get(
            self.dashboard_url(area=self.area_ti.pk, start_date=start)
        )
        self.assertEqual(response.context["total"], 1)

    def test_invalid_dates_do_not_break_the_view(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(
            self.dashboard_url(start_date="not-a-date", end_date="also-bad")
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["start_date_error"])
        self.assertIsNotNone(response.context["end_date_error"])
        # Invalid filters are dropped, not applied: both tickets show.
        self.assertEqual(response.context["total"], 2)

    def test_start_date_after_end_date_is_rejected_not_misleading(self):
        self.client.login(username="admin1", password="pass12345")
        start = timezone.now().date().isoformat()
        end = (timezone.now() - datetime.timedelta(days=10)).date().isoformat()
        response = self.client.get(
            self.dashboard_url(start_date=start, end_date=end)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["date_range_error"])
        # Both filters are dropped instead of silently returning an
        # empty (and misleading) result: both tickets show.
        self.assertEqual(response.context["total"], 2)


class DashboardEmptyStateTests(DashboardBaseTestCase):
    def test_dashboard_renders_with_zero_tickets(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total"], 0)
        self.assertEqual(response.context["by_area"], [])
        self.assertIsNone(response.context["average_resolution_label"])
        self.assertContains(response, "No hay datos")
        self.assertContains(response, "No hay tickets para mostrar")


class DashboardStatusCountsTests(DashboardBaseTestCase):
    def test_status_counts_are_correct(self):
        make_ticket(self.category_ti, self.employee, "Uno")
        t2 = make_ticket(self.category_ti, self.employee, "Dos")
        t3 = make_ticket(self.category_ti, self.employee, "Tres")
        assign_ticket(t2, assigned_to=self.manager_ti, changed_by=self.admin)
        change_ticket_status(t2, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager_ti)
        assign_ticket(t3, assigned_to=self.manager_ti, changed_by=self.admin)
        change_ticket_status(t3, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager_ti)
        change_ticket_status(t3, new_status=Ticket.Status.RESOLVED, changed_by=self.manager_ti)

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.context["total"], 3)
        self.assertEqual(response.context["pending"], 1)
        self.assertEqual(response.context["in_process"], 1)
        self.assertEqual(response.context["resolved"], 1)


class DashboardResolutionTimeTests(DashboardBaseTestCase):
    def test_average_resolution_uses_ticket_history(self):
        base = timezone.now() - datetime.timedelta(days=10)
        ticket = make_ticket(self.category_ti, self.employee, "Resuelto")
        resolve_ticket_after(ticket, self.manager_ti, created_at=base, hours_to_resolve=2)

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.context["average_resolution_label"], "2.0 horas")

    def test_average_is_computed_only_over_resolved_tickets(self):
        base = timezone.now() - datetime.timedelta(days=10)
        resolved_ticket = make_ticket(self.category_ti, self.employee, "Resuelto")
        resolve_ticket_after(
            resolved_ticket, self.manager_ti, created_at=base, hours_to_resolve=4
        )
        # An open ticket must not distort the average.
        make_ticket(self.category_ti, self.employee, "Abierto")

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.context["average_resolution_label"], "4.0 horas")
        self.assertEqual(response.context["total"], 2)

    def test_average_of_multiple_resolved_tickets(self):
        base = timezone.now() - datetime.timedelta(days=10)
        t1 = make_ticket(self.category_ti, self.employee, "Uno")
        resolve_ticket_after(t1, self.manager_ti, created_at=base, hours_to_resolve=2)
        t2 = make_ticket(self.category_ti, self.employee, "Dos")
        resolve_ticket_after(t2, self.manager_ti, created_at=base, hours_to_resolve=6)

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.context["average_resolution_label"], "4.0 horas")

    def test_no_resolved_tickets_shows_no_data(self):
        make_ticket(self.category_ti, self.employee, "Pendiente")

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertIsNone(response.context["average_resolution_label"])
        self.assertContains(response, "No hay datos")

    def test_duration_starts_at_ticket_creation_not_at_in_process(self):
        # PENDING -> IN_PROCESS -> RESOLVED, with all three timestamps
        # distinct: the average must be resolved_at - created_at (the
        # PENDING creation time), never resolved_at - in_process_at.
        created = timezone.now() - datetime.timedelta(days=10)
        ticket = make_ticket(self.category_ti, self.employee, "Ticket")
        Ticket.objects.filter(pk=ticket.pk).update(created_at=created)
        ticket.refresh_from_db()

        change_ticket_status(
            ticket, new_status=Ticket.Status.IN_PROCESS, changed_by=self.manager_ti
        )
        in_process_entry = TicketHistory.objects.get(
            ticket=ticket, status=Ticket.Status.IN_PROCESS
        )
        TicketHistory.objects.filter(pk=in_process_entry.pk).update(
            created_at=created + datetime.timedelta(hours=3)
        )

        change_ticket_status(
            ticket, new_status=Ticket.Status.RESOLVED, changed_by=self.manager_ti
        )
        resolved_entry = TicketHistory.objects.get(
            ticket=ticket, status=Ticket.Status.RESOLVED
        )
        TicketHistory.objects.filter(pk=resolved_entry.pk).update(
            created_at=created + datetime.timedelta(hours=5)
        )

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        # 5.0 horas (from creation), not 2.0 horas (from IN_PROCESS).
        self.assertEqual(response.context["average_resolution_label"], "5.0 horas")

    def test_average_resolution_respects_area_manager_scope(self):
        base = timezone.now() - datetime.timedelta(days=10)
        ticket_ti = make_ticket(self.category_ti, self.employee, "TI resuelto")
        resolve_ticket_after(ticket_ti, self.manager_ti, created_at=base, hours_to_resolve=2)
        ticket_rrhh = make_ticket(self.category_rrhh, self.employee_rrhh, "RRHH resuelto")
        resolve_ticket_after(
            ticket_rrhh, self.manager_rrhh, created_at=base, hours_to_resolve=100
        )

        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.context["average_resolution_label"], "2.0 horas")

    def test_average_resolution_respects_management_global_scope(self):
        base = timezone.now() - datetime.timedelta(days=10)
        ticket_ti = make_ticket(self.category_ti, self.employee, "TI resuelto")
        resolve_ticket_after(ticket_ti, self.manager_ti, created_at=base, hours_to_resolve=2)
        ticket_rrhh = make_ticket(self.category_rrhh, self.employee_rrhh, "RRHH resuelto")
        resolve_ticket_after(ticket_rrhh, self.manager_rrhh, created_at=base, hours_to_resolve=6)

        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.context["average_resolution_label"], "4.0 horas")

    def test_average_resolution_respects_area_filter_for_admin(self):
        base = timezone.now() - datetime.timedelta(days=10)
        ticket_ti = make_ticket(self.category_ti, self.employee, "TI resuelto")
        resolve_ticket_after(ticket_ti, self.manager_ti, created_at=base, hours_to_resolve=2)
        ticket_rrhh = make_ticket(self.category_rrhh, self.employee_rrhh, "RRHH resuelto")
        resolve_ticket_after(ticket_rrhh, self.manager_rrhh, created_at=base, hours_to_resolve=8)

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url(area=self.area_ti.pk))
        self.assertEqual(response.context["average_resolution_label"], "2.0 horas")

    def test_average_resolution_respects_date_filter(self):
        old_base = timezone.now() - datetime.timedelta(days=30)
        recent_base = timezone.now() - datetime.timedelta(days=1)
        old_ticket = make_ticket(self.category_ti, self.employee, "Viejo resuelto")
        resolve_ticket_after(
            old_ticket, self.manager_ti, created_at=old_base, hours_to_resolve=100
        )
        recent_ticket = make_ticket(self.category_ti, self.employee, "Reciente resuelto")
        resolve_ticket_after(
            recent_ticket, self.manager_ti, created_at=recent_base, hours_to_resolve=2
        )

        self.client.login(username="admin1", password="pass12345")
        start = (timezone.now() - datetime.timedelta(days=5)).date().isoformat()
        response = self.client.get(self.dashboard_url(start_date=start))
        self.assertEqual(response.context["average_resolution_label"], "2.0 horas")


class DashboardByAreaTests(DashboardBaseTestCase):
    def test_grouping_by_area_uses_category_area(self):
        make_ticket(self.category_ti, self.employee, "TI 1")
        make_ticket(self.category_ti, self.employee, "TI 2")
        make_ticket(self.category_rrhh, self.employee_rrhh, "RRHH 1")

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        by_area = {row["category__area__name"]: row["count"] for row in response.context["by_area"]}
        self.assertEqual(by_area["TI"], 2)
        self.assertEqual(by_area["RRHH"], 1)

    def test_area_manager_never_receives_other_areas_data(self):
        make_ticket(self.category_ti, self.employee, "TI 1")
        make_ticket(self.category_rrhh, self.employee_rrhh, "RRHH 1")

        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(self.dashboard_url())
        area_names = [row["category__area__name"] for row in response.context["by_area"]]
        self.assertEqual(area_names, ["TI"])


class DashboardRecentTicketsTests(DashboardBaseTestCase):
    def test_recent_tickets_respects_visibility(self):
        make_ticket(self.category_ti, self.employee, "TI 1")
        make_ticket(self.category_rrhh, self.employee_rrhh, "RRHH 1")

        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(self.dashboard_url())
        titles = [t.title for t in response.context["recent_tickets"]]
        self.assertEqual(titles, ["TI 1"])

    def test_recent_tickets_respects_limit(self):
        for i in range(15):
            make_ticket(self.category_ti, self.employee, f"Ticket {i}")

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(len(response.context["recent_tickets"]), 10)

    def test_recent_tickets_ordered_newest_first(self):
        t1 = make_ticket(self.category_ti, self.employee, "Primero")
        Ticket.objects.filter(pk=t1.pk).update(
            created_at=timezone.now() - datetime.timedelta(hours=5)
        )
        t2 = make_ticket(self.category_ti, self.employee, "Segundo")

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        titles = [t.title for t in response.context["recent_tickets"]]
        self.assertEqual(titles, ["Segundo", "Primero"])

    def test_recent_tickets_tie_broken_by_id_on_equal_created_at(self):
        same_moment = timezone.now() - datetime.timedelta(hours=1)
        t1 = make_ticket(self.category_ti, self.employee, "Empate 1")
        t2 = make_ticket(self.category_ti, self.employee, "Empate 2")
        # Force an exact tie in created_at, which real clocks can also
        # produce on fast/coarse-resolution systems; the id tiebreaker
        # must still yield a fully deterministic order.
        Ticket.objects.filter(pk__in=[t1.pk, t2.pk]).update(created_at=same_moment)

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        titles = [t.title for t in response.context["recent_tickets"]]
        # Higher id (created later) must come first despite the tie.
        self.assertEqual(titles, ["Empate 2", "Empate 1"])


class DashboardManagementRecentTicketsScopeTests(DashboardBaseTestCase):
    """Management's dashboard scope is management-level reporting, not
    individual ticket content: the "recent tickets" widget (which would
    otherwise link to a ticket detail page that tickets.permissions
    .get_visible_tickets correctly denies management, i.e. a 404) must
    be fully absent for this role, without weakening any other role's
    view of it.
    """

    def setUp(self):
        super().setUp()
        make_ticket(self.category_ti, self.employee, "TI 1")
        make_ticket(self.category_rrhh, self.employee_rrhh, "RRHH 1")

    def test_management_can_access_dashboard(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 200)

    def test_management_receives_no_recent_tickets(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertFalse(response.context["show_recent_tickets"])
        self.assertEqual(list(response.context["recent_tickets"]), [])

    def test_management_does_not_see_recent_tickets_widget(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertNotContains(response, "Tickets recientes")
        self.assertNotContains(response, "TI 1")
        self.assertNotContains(response, "RRHH 1")

    def test_management_still_sees_dashboard_metrics(self):
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.context["total"], 2)
        by_area = {row["category__area__name"]: row["count"] for row in response.context["by_area"]}
        self.assertEqual(by_area["TI"], 1)
        self.assertEqual(by_area["RRHH"], 1)
        self.assertContains(response, "statusChart")
        self.assertContains(response, "areaChart")

    def test_admin_still_sees_recent_tickets(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertTrue(response.context["show_recent_tickets"])
        self.assertContains(response, "Tickets recientes")
        self.assertContains(response, "TI 1")
        self.assertContains(response, "RRHH 1")

    def test_area_manager_still_sees_recent_tickets_scoped_to_own_area(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(self.dashboard_url())
        self.assertTrue(response.context["show_recent_tickets"])
        self.assertContains(response, "Tickets recientes")
        self.assertContains(response, "TI 1")
        self.assertNotContains(response, "RRHH 1")

    def test_management_still_cannot_access_ticket_detail(self):
        # Confirms the fix does not grant management any new access to
        # tickets.views.ticket_detail; tickets/permissions.py was not
        # touched by this change.
        ticket = Ticket.objects.filter(category=self.category_ti).first()
        self.client.login(username="direccion1", password="pass12345")
        response = self.client.get(reverse("tickets:detail", args=[ticket.pk]))
        self.assertEqual(response.status_code, 404)
