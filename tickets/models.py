from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class TicketManager(models.Manager):
    def create_ticket(self, *, title, description, category, created_by):
        """Create a Ticket together with its initial TicketHistory entry."""
        with transaction.atomic():
            ticket = self.create(
                title=title,
                description=description,
                category=category,
                created_by=created_by,
                status=Ticket.Status.PENDING,
            )
            TicketHistory.objects.create(
                ticket=ticket,
                status=ticket.status,
                changed_by=created_by,
            )
        return ticket


class Ticket(models.Model):
    """A request reported by an employee.

    The area is never stored directly on the ticket: it is always
    obtained through ``ticket.category.area``, so Category remains the
    single source of truth for which area a ticket belongs to.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        IN_PROCESS = "IN_PROCESS", "En proceso"
        RESOLVED = "RESOLVED", "Resuelto"

    ticket_number = models.CharField(
        max_length=20, unique=True, editable=False, blank=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        "administration.Category",
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tickets",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TicketManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.ticket_number or f"Ticket #{self.pk}"

    @property
    def area(self):
        return self.category.area

    def clean(self):
        super().clean()
        if (
            self.assigned_to_id
            and self.category_id
            and self.assigned_to.area_id != self.category.area_id
        ):
            raise ValidationError(
                {"assigned_to": "The assigned user must belong to the ticket's area."}
            )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.ticket_number:
            self.ticket_number = f"TK-{self.pk:06d}"
            super().save(update_fields=["ticket_number"])


class TicketHistory(models.Model):
    """Append-only log of ticket status changes.

    This block only records the initial PENDING entry created together
    with the ticket; the full transition workflow is implemented in
    Block 5.
    """

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="history"
    )
    status = models.CharField(max_length=20, choices=Ticket.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ticket_history_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Ticket history entry"
        verbose_name_plural = "Ticket history"

    def __str__(self):
        return f"{self.ticket.ticket_number} -> {self.get_status_display()}"
