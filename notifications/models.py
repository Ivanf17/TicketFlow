from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """An in-app notification delivered to a single user about a ticket
    event (assignment, reassignment or status change).

    Notifications are personal inbox items, not organizational audit
    history (that role is already filled by ``tickets.TicketHistory`` and
    ``assignment.TicketAssignmentHistory``). Both foreign keys therefore
    use CASCADE: if the recipient user is removed, their personal inbox
    has no independent value and should go with them; if the related
    ticket is removed, a notification pointing at a ticket that no
    longer exists is meaningless (mirroring the CASCADE already used by
    TicketHistory/TicketAssignmentHistory on their own ``ticket`` FK).
    """

    class NotificationType(models.TextChoices):
        TICKET_ASSIGNED = "TICKET_ASSIGNED", "Ticket asignado"
        TICKET_REASSIGNED = "TICKET_REASSIGNED", "Ticket reasignado"
        TICKET_STATUS_CHANGED = "TICKET_STATUS_CHANGED", "Cambio de estado"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=30, choices=NotificationType.choices
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.title} -> {self.recipient.username}"

    def mark_as_read(self):
        """Mark this notification as read, unless it already is.

        Centralized here so the view (and any future caller) never
        duplicates the "already read -> no-op" rule.
        """
        if self.is_read:
            return
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "read_at"])
