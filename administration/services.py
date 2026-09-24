from users.models import User


def is_last_active_admin(user):
    """True if ``user`` is the only thing standing between the system and
    having zero active Admins.

    Only role=admin AND is_active=True count as "an active Admin": an
    inactive Admin account (or one already holding a different role)
    provides no real backup, so it must not be treated as one. This is
    a cross-row check (how many *other* active Admins exist), which is
    exactly why it lives here as application-level validation instead
    of a database CheckConstraint -- a CheckConstraint only ever sees
    the single row being written, never the rest of the table.

    Used from both administration.forms.UserAdminForm (edits, including
    an Admin editing themselves) and administration.views.user_delete
    (deletes, which don't go through that form), so the counting rule
    itself is defined exactly once.
    """
    if user.role != User.Role.ADMIN or not user.is_active:
        return False
    return not (
        User.objects.filter(role=User.Role.ADMIN, is_active=True)
        .exclude(pk=user.pk)
        .exists()
    )
