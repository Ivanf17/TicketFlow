from django.db import transaction

from notifications.services import notify_ticket_assigned, notify_ticket_reassigned
from users.models import User

from .models import AreaAssignmentCursor, TicketAssignmentHistory


class AssignmentError(Exception):
    """Raised when an assignment/reassignment violates a business rule."""


def get_active_area_managers(area):
    """Active Area Managers belonging to ``area``, in a stable order.

    Only users with role=area_manager, area=area and is_active=True are
    eligible: no employees, no admins, no management users.
    """
    return list(
        User.objects.filter(
            role=User.Role.AREA_MANAGER,
            area=area,
            is_active=True,
        ).order_by("id")
    )


def pick_next_area_manager(area):
    """Return the next Area Manager for ``area`` per Round Robin, or None.

    The "next responsible" is derived from a persistent per-area cursor
    (``AreaAssignmentCursor.last_assigned_to``) rather than from counting
    tickets, so reassignments or historical tickets cannot skew the
    distribution. ``select_for_update`` keeps concurrent ticket creations
    from picking the same manager twice.
    """
    managers = get_active_area_managers(area)
    if not managers:
        return None

    with transaction.atomic():
        cursor, _ = AreaAssignmentCursor.objects.select_for_update().get_or_create(
            area=area
        )
        manager_ids = [manager.id for manager in managers]
        if cursor.last_assigned_to_id in manager_ids:
            next_index = (manager_ids.index(cursor.last_assigned_to_id) + 1) % len(
                managers
            )
        else:
            next_index = 0
        next_manager = managers[next_index]
        cursor.last_assigned_to = next_manager
        cursor.save(update_fields=["last_assigned_to"])
    return next_manager


def assign_ticket(ticket, *, assigned_to, changed_by):
    """Assign or reassign ``ticket`` to ``assigned_to``.

    ``changed_by`` is the acting user, or ``None`` for an automatic
    (Round Robin) assignment. A history entry is only recorded when the
    responsible actually changes; reassigning to the same person is a
    no-op. This function never touches the Round Robin cursor, so manual
    (re)assignments cannot make automatic assignment lose track of the
    next responsible.

    A notification is sent to the new responsible, inside the same
    transaction as the ticket update and history entry: "Nuevo ticket
    asignado" when there was no previous responsible (first assignment,
    whether automatic or manual), "Ticket reasignado" when a real
    reassignment replaces a previous responsible. No notification is
    sent when there is no active manager to assign to, and none is sent
    to the previous responsible.
    """
    if assigned_to.area_id != ticket.category.area_id:
        raise AssignmentError(
            "The assigned user must belong to the ticket's area."
        )

    previous = ticket.assigned_to
    if previous is not None and previous.id == assigned_to.id:
        return ticket

    with transaction.atomic():
        ticket.assigned_to = assigned_to
        ticket.save(update_fields=["assigned_to", "updated_at"])
        TicketAssignmentHistory.objects.create(
            ticket=ticket,
            previous_assigned_to=previous,
            new_assigned_to=assigned_to,
            changed_by=changed_by,
        )
        if previous is None:
            notify_ticket_assigned(ticket, recipient=assigned_to)
        else:
            notify_ticket_reassigned(ticket, recipient=assigned_to)
    return ticket


def auto_assign_ticket(ticket):
    """Attempt automatic Round Robin assignment right after creation.

    If the ticket's area has no active Area Manager, the ticket is left
    with ``assigned_to = None`` and no error is raised.
    """
    manager = pick_next_area_manager(ticket.category.area)
    if manager is None:
        return ticket
    return assign_ticket(ticket, assigned_to=manager, changed_by=None)
