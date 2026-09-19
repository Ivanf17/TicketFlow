from django.conf import settings
from django.db import models


class AreaAssignmentCursor(models.Model):
    """Persists Round Robin state per Area for automatic ticket assignment.

    Only the automatic assignment flow (see ``assignment.services``) reads
    and updates this cursor. Manual (re)assignments never touch it, so a
    manual change can never make the Round Robin lose track of who the
    next automatically-assigned responsible should be.
    """

    area = models.OneToOneField(
        "administration.Area",
        on_delete=models.CASCADE,
        related_name="assignment_cursor",
    )
    last_assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    def __str__(self):
        return f"Round Robin cursor for {self.area.name}"


class TicketAssignmentHistory(models.Model):
    """Append-only log of ticket assignment/reassignment changes.

    ``changed_by = None`` identifies an automatic (Round Robin) assignment
    performed by the system, as opposed to a human user performing a
    manual assignment or reassignment.
    """

    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.CASCADE,
        related_name="assignment_history",
    )
    previous_assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    new_assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Ticket assignment history entry"
        verbose_name_plural = "Ticket assignment history"

    def __str__(self):
        actor = self.changed_by.username if self.changed_by else "system"
        return (
            f"{self.ticket.ticket_number}: "
            f"{self.previous_assigned_to} -> {self.new_assigned_to} ({actor})"
        )
