from django.conf import settings
from django.test import TestCase
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
