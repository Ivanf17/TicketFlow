from users.models import User


def can_manage_ticket_assignment(user, ticket):
    """Basic role-based check for manual (re)assignment (Block 4 scope).

    - admin: can manage any ticket, from any area.
    - area_manager: can manage only tickets belonging to their own area.
    - employee / management: never allowed to assign or reassign.
    """
    if user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.AREA_MANAGER:
        return user.area_id == ticket.category.area_id
    return False
