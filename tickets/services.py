from django.db import transaction

from .models import Ticket, TicketHistory


class StatusTransitionError(Exception):
    """Raised when a ticket status transition is not allowed."""


# Single source of truth for the status state machine: PENDING -> IN_PROCESS
# -> RESOLVED, one step at a time. RESOLVED has no entry, so it is terminal
# (no reopening, no going back, no skipping).
ALLOWED_TRANSITIONS = {
    Ticket.Status.PENDING: Ticket.Status.IN_PROCESS,
    Ticket.Status.IN_PROCESS: Ticket.Status.RESOLVED,
}


def get_next_status(current_status):
    """The single allowed next status after ``current_status``, or None."""
    return ALLOWED_TRANSITIONS.get(current_status)


def change_ticket_status(ticket, *, new_status, changed_by):
    """Move ``ticket`` to ``new_status`` if, and only if, that is the one
    allowed next step in PENDING -> IN_PROCESS -> RESOLVED.

    This is the single place that enforces the status state machine, so
    no view duplicates the transition rules. The ticket row is locked
    with ``select_for_update`` and its status re-read from the database
    inside the transaction, so a concurrent change_ticket_status call on
    the same ticket can't race past a stale in-memory status. The ticket
    update and the TicketHistory entry are written atomically: if the
    transition is invalid, nothing is written at all (no ticket update,
    no history entry).
    """
    with transaction.atomic():
        current_status = (
            Ticket.objects.select_for_update()
            .values_list("status", flat=True)
            .get(pk=ticket.pk)
        )
        if new_status != get_next_status(current_status):
            raise StatusTransitionError(
                f"Cannot transition ticket from {current_status} to {new_status}."
            )

        ticket.status = new_status
        ticket.save(update_fields=["status", "updated_at"])
        TicketHistory.objects.create(
            ticket=ticket,
            previous_status=current_status,
            status=new_status,
            changed_by=changed_by,
        )
    return ticket
