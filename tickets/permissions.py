from .models import Ticket


def get_visible_tickets(user):
    """Basic role-based visibility for tickets (Block 3 scope only).

    - admin: every ticket.
    - area_manager: tickets whose category belongs to the manager's area.
    - employee: only the tickets they created.
    - management (or any other case): no ticket-lifecycle access yet.
    """
    Role = user.Role
    if user.role == Role.ADMIN:
        return Ticket.objects.all()
    if user.role == Role.AREA_MANAGER:
        return Ticket.objects.filter(category__area=user.area)
    if user.role == Role.EMPLOYEE:
        return Ticket.objects.filter(created_by=user)
    return Ticket.objects.none()


def can_manage_ticket_status(user, ticket):
    """Basic role-based check for advancing a ticket's status (Block 5).

    - admin: can change the status of any ticket.
    - area_manager: only tickets belonging to their own area.
    - employee / management: never change status directly; employees can
      only consult their own tickets, and management doesn't take part
      in the ticket's operational lifecycle.
    """
    if user.role == user.Role.ADMIN:
        return True
    if user.role == user.Role.AREA_MANAGER:
        return user.area_id == ticket.category.area_id
    return False
