from .models import Notification


def create_notification(*, recipient, ticket, notification_type, title, message):
    """Single centralized entry point for creating a Notification.

    Callers (assignment.services, tickets.services) are expected to
    invoke this from inside their own ``transaction.atomic()`` block, so
    the notification is committed (or rolled back) together with the
    ticket update and its history entry.
    """
    return Notification.objects.create(
        recipient=recipient,
        ticket=ticket,
        notification_type=notification_type,
        title=title,
        message=message,
    )


def notify_ticket_assigned(ticket, *, recipient):
    """A ticket received its first responsible (automatic or manual)."""
    return create_notification(
        recipient=recipient,
        ticket=ticket,
        notification_type=Notification.NotificationType.TICKET_ASSIGNED,
        title="Nuevo ticket asignado",
        message=f"Se te ha asignado el ticket {ticket.ticket_number}.",
    )


def notify_ticket_reassigned(ticket, *, recipient):
    """A ticket's responsible was replaced by a new one."""
    return create_notification(
        recipient=recipient,
        ticket=ticket,
        notification_type=Notification.NotificationType.TICKET_REASSIGNED,
        title="Ticket reasignado",
        message=f"Se te ha reasignado el ticket {ticket.ticket_number}.",
    )


def notify_ticket_status_changed(ticket, *, recipient):
    """A ticket's status changed via a valid transition.

    Reads ``ticket.status``/``ticket.get_status_display()`` directly
    (the ticket instance passed in has already been updated to the new
    status by the caller), so this only needs duck-typed access to the
    ticket object and never imports tickets.models.Ticket.
    """
    if ticket.status == "RESOLVED":
        message = (
            f"El ticket {ticket.ticket_number} fue marcado como "
            f"{ticket.get_status_display()}."
        )
    else:
        message = (
            f"El ticket {ticket.ticket_number} cambió a "
            f"{ticket.get_status_display()}."
        )
    return create_notification(
        recipient=recipient,
        ticket=ticket,
        notification_type=Notification.NotificationType.TICKET_STATUS_CHANGED,
        title="Estado del ticket actualizado",
        message=message,
    )


def notify_ticket_comment_added(ticket, *, author):
    """A new comment was added to ``ticket`` by ``author``.

    - If the comment's author is the ticket's creator, the currently
      assigned responsible (if any) is notified.
    - Otherwise (an area_manager or admin who can see the ticket
      commenting on it), the ticket's creator is notified.
    - Never notifies the comment's own author, and creates nothing if
      there is no valid recipient (e.g. an unassigned ticket commented
      on by its own creator).
    """
    recipient = ticket.assigned_to if author == ticket.created_by else ticket.created_by
    if recipient is None or recipient == author:
        return None
    return create_notification(
        recipient=recipient,
        ticket=ticket,
        notification_type=Notification.NotificationType.TICKET_COMMENT_ADDED,
        title="Nuevo comentario",
        message=f"Nuevo comentario en el ticket {ticket.ticket_number}.",
    )
