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
