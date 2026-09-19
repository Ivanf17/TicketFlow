from tickets.models import Ticket
from tickets.permissions import get_visible_tickets
from users.models import User

DASHBOARD_ROLES = (User.Role.AREA_MANAGER, User.Role.ADMIN, User.Role.MANAGEMENT)


def can_access_dashboard(user):
    """Only Area Manager, Admin and Management may see the dashboard.

    Employee never gets here (no dashboard link, and the view itself
    rejects it even if the URL is requested directly).
    """
    return user.role in DASHBOARD_ROLES


def get_dashboard_tickets_queryset(user):
    """Base, role-scoped ticket queryset the dashboard is built from.

    This is the single point where "which tickets can this user see on
    the dashboard" is decided; every metric (counts, by-area breakdown,
    average resolution time, recent tickets) is derived from this same
    queryset (further narrowed by the date/area filters), so nothing on
    the page is ever computed over a different set of tickets.

    Reuses ``tickets.permissions.get_visible_tickets`` directly for
    admin/area_manager (identical rule: no duplicated logic). Management
    is the one deliberate exception: Block 7 explicitly grants
    management a *global* dashboard view, even though
    ``get_visible_tickets`` gives management no ticket-lifecycle access
    at all (out of scope for tickets themselves, but the dashboard is a
    reporting concern management is explicitly meant to see).
    """
    if user.role == User.Role.MANAGEMENT:
        return Ticket.objects.all()
    return get_visible_tickets(user)
