from users.models import User


def can_access_administration(user):
    """Only Admin manages users, areas and categories.

    Matches the Block 8 reference permission matrix exactly: "Gestionar
    usuarios/áreas/categorías" is Admin-only, No for every other role.
    Area Manager's own privileges (ticket visibility, assignment,
    status) already live in tickets/assignment and are untouched here;
    this module only gates the Users/Areas/Categories screens.
    """
    return user.role == User.Role.ADMIN
