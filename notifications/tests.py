from django.conf import settings
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from administration.models import Area, Category
from tickets.models import Ticket
from users.models import User

from .models import Notification


class NotificationModelTests(TestCase):
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

    def test_notification_can_be_created(self):
        notification = Notification.objects.create(
            recipient=self.manager,
            ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_ASSIGNED,
            title="Nuevo ticket asignado",
            message=f"Se te ha asignado el ticket {self.ticket.ticket_number}.",
        )
        self.assertEqual(notification.recipient, self.manager)
        self.assertEqual(notification.ticket, self.ticket)

    def test_defaults_is_read_false_and_read_at_null(self):
        notification = Notification.objects.create(
            recipient=self.manager,
            ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_ASSIGNED,
            title="t",
            message="m",
        )
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_notification_type_choices(self):
        types = dict(Notification.NotificationType.choices)
        self.assertIn("TICKET_ASSIGNED", types)
        self.assertIn("TICKET_REASSIGNED", types)
        self.assertIn("TICKET_STATUS_CHANGED", types)
        self.assertIn("TICKET_COMMENT_ADDED", types)
        self.assertEqual(len(types), 4)

    def test_mark_as_read_sets_is_read_and_read_at(self):
        notification = Notification.objects.create(
            recipient=self.manager,
            ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_ASSIGNED,
            title="t",
            message="m",
        )
        notification.mark_as_read()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_mark_as_read_twice_does_not_change_read_at(self):
        notification = Notification.objects.create(
            recipient=self.manager,
            ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_ASSIGNED,
            title="t",
            message="m",
        )
        notification.mark_as_read()
        first_read_at = notification.read_at

        notification.mark_as_read()
        self.assertEqual(notification.read_at, first_read_at)


class NotificationInboxViewTests(TestCase):
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
        self.other_manager = User.objects.create_user(
            username="otro_jefe", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.ticket = Ticket.objects.create_ticket(
            title="Impresora rota", description="desc",
            category=self.category, created_by=self.employee,
        )
        self.own_notification = Notification.objects.create(
            recipient=self.manager,
            ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_ASSIGNED,
            title="Nuevo ticket asignado",
            message="Se te ha asignado el ticket.",
        )
        self.other_notification = Notification.objects.create(
            recipient=self.other_manager,
            ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_ASSIGNED,
            title="Otro ticket asignado",
            message="Notificación de otro usuario.",
        )

    def test_user_only_sees_own_notifications(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nuevo ticket asignado")
        self.assertNotContains(response, "Otro ticket asignado")

    def test_login_required_for_inbox(self):
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_user_can_mark_own_notification_as_read(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.post(
            reverse("notifications:mark_read", args=[self.own_notification.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.own_notification.refresh_from_db()
        self.assertTrue(self.own_notification.is_read)
        self.assertIsNotNone(self.own_notification.read_at)

    def test_user_cannot_mark_others_notification_as_read(self):
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.post(
            reverse("notifications:mark_read", args=[self.other_notification.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.other_notification.refresh_from_db()
        self.assertFalse(self.other_notification.is_read)

    def test_marking_already_read_notification_again_is_harmless(self):
        self.client.login(username="jefe_ti", password="pass12345")
        self.client.post(
            reverse("notifications:mark_read", args=[self.own_notification.pk])
        )
        self.own_notification.refresh_from_db()
        first_read_at = self.own_notification.read_at

        response = self.client.post(
            reverse("notifications:mark_read", args=[self.own_notification.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.own_notification.refresh_from_db()
        self.assertTrue(self.own_notification.is_read)
        self.assertEqual(self.own_notification.read_at, first_read_at)

    def test_mark_all_read_only_affects_own_unread_notifications(self):
        Notification.objects.create(
            recipient=self.manager,
            ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_STATUS_CHANGED,
            title="Segunda notificación propia",
            message="m",
        )
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.post(reverse("notifications:mark_all_read"))
        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            Notification.objects.filter(recipient=self.manager, is_read=False).exists()
        )
        self.other_notification.refresh_from_db()
        self.assertFalse(self.other_notification.is_read)


class UnreadNotificationsCounterTests(TestCase):
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
        self.other_manager = User.objects.create_user(
            username="otro_jefe", password="pass12345",
            role=User.Role.AREA_MANAGER, area=self.area,
        )
        self.ticket = Ticket.objects.create_ticket(
            title="Impresora rota", description="desc",
            category=self.category, created_by=self.employee,
        )

    def test_counter_shows_correct_unread_count_for_authenticated_user(self):
        Notification.objects.create(
            recipient=self.manager, ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_ASSIGNED,
            title="t1", message="m1",
        )
        Notification.objects.create(
            recipient=self.manager, ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_ASSIGNED,
            title="t2", message="m2",
        )
        read_one = Notification.objects.create(
            recipient=self.manager, ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_ASSIGNED,
            title="t3", message="m3",
        )
        read_one.mark_as_read()

        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Notificaciones (2)")

    def test_counter_only_counts_authenticated_users_own_notifications(self):
        Notification.objects.create(
            recipient=self.other_manager, ticket=self.ticket,
            notification_type=Notification.NotificationType.TICKET_ASSIGNED,
            title="t1", message="m1",
        )
        self.client.login(username="jefe_ti", password="pass12345")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Notificaciones (0)")


class NotificationListPaginationTests(TestCase):
    """Block 9: notification_list uses Paginator.get_page(), which must
    never turn an out-of-range or non-numeric ``?page=`` into a 500.
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
        self.ticket = Ticket.objects.create_ticket(
            title="Impresora rota", description="desc",
            category=self.category, created_by=self.employee,
        )
        for i in range(settings.PAGE_SIZE + 5):
            Notification.objects.create(
                recipient=self.manager, ticket=self.ticket,
                notification_type=Notification.NotificationType.TICKET_ASSIGNED,
                title=f"t{i}", message=f"m{i}",
            )
        self.client.login(username="jefe_ti", password="pass12345")

    def test_page_1_returns_at_most_page_size_items(self):
        response = self.client.get(reverse("notifications:list"), {"page": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), settings.PAGE_SIZE)

    def test_later_page_returns_remaining_items(self):
        response = self.client.get(reverse("notifications:list"), {"page": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 5)

    def test_out_of_range_page_falls_back_to_last_page_not_500(self):
        response = self.client.get(reverse("notifications:list"), {"page": 999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)

    def test_non_numeric_page_falls_back_to_first_page_not_500(self):
        response = self.client.get(reverse("notifications:list"), {"page": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)


class NotificationListQueryCountTests(TestCase):
    """Block 10: locks in the select_related("ticket") fix for
    notification_list's N+1 (the template reads notification.ticket.pk
    / .ticket_number per row). Checked at 1 row and 10 rows, since a
    single row can't reveal an N+1.
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
        self.ticket = Ticket.objects.create_ticket(
            title="Impresora rota", description="desc",
            category=self.category, created_by=self.employee,
        )
        self.client.login(username="jefe_ti", password="pass12345")

    def _create_notifications(self, n):
        for i in range(n):
            Notification.objects.create(
                recipient=self.manager, ticket=self.ticket,
                notification_type=Notification.NotificationType.TICKET_ASSIGNED,
                title=f"t{i}", message=f"m{i}",
            )

    def test_query_count_does_not_grow_with_more_notifications(self):
        self._create_notifications(1)
        with CaptureQueriesContext(connection) as one_row:
            self.client.get(reverse("notifications:list"))
        baseline = len(one_row.captured_queries)

        self._create_notifications(9)  # 10 notifications total
        with self.assertNumQueries(baseline):
            self.client.get(reverse("notifications:list"))


class NotificationCenterRedesignTests(TestCase):
    """Redesign: inbox tabs (unread / per type) and the same-site
    ``next`` redirect used by the top-bar dropdown."""

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
        Type = Notification.NotificationType
        self.assigned = Notification.objects.create(
            recipient=self.manager, ticket=self.ticket,
            notification_type=Type.TICKET_ASSIGNED, title="Asignado", message="m",
        )
        self.comment = Notification.objects.create(
            recipient=self.manager, ticket=self.ticket,
            notification_type=Type.TICKET_COMMENT_ADDED, title="Comentario",
            message="m", is_read=True,
        )
        Notification.objects.create(
            recipient=self.employee, ticket=self.ticket,
            notification_type=Type.TICKET_ASSIGNED, title="Ajena", message="m",
        )
        self.client.login(username="jefe_ti", password="pass12345")

    def _pks(self, response):
        return {n.pk for n in response.context["page_obj"]}

    def test_unread_filter(self):
        response = self.client.get(reverse("notifications:list"), {"filter": "unread"})
        self.assertEqual(self._pks(response), {self.assigned.pk})

    def test_type_filter(self):
        response = self.client.get(
            reverse("notifications:list"), {"filter": "TICKET_COMMENT_ADDED"}
        )
        self.assertEqual(self._pks(response), {self.comment.pk})

    def test_unknown_filter_shows_whole_own_inbox(self):
        response = self.client.get(reverse("notifications:list"), {"filter": "nope"})
        self.assertEqual(self._pks(response), {self.assigned.pk, self.comment.pk})
        self.assertEqual(response.context["total_count"], 2)

    def test_mark_read_redirects_to_same_site_next(self):
        next_url = reverse("tickets:detail", args=[self.ticket.pk])
        response = self.client.post(
            reverse("notifications:mark_read", args=[self.assigned.pk]),
            {"next": next_url},
        )
        self.assertRedirects(response, next_url, fetch_redirect_response=False)

    def test_mark_all_read_ignores_offsite_next(self):
        response = self.client.post(
            reverse("notifications:mark_all_read"),
            {"next": "https://evil.example.com/"},
        )
        self.assertRedirects(response, reverse("notifications:list"))

    def test_dropdown_lists_only_own_notifications(self):
        response = self.client.get(reverse("home"))
        titles = {n.title for n in response.context["recent_notifications"]}
        self.assertEqual(titles, {"Asignado", "Comentario"})
