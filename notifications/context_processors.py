from .models import Notification

RECENT_NOTIFICATIONS_LIMIT = 5


def unread_notifications_count(request):
    """Adds ``unread_notifications_count`` to every template's context.

    Registered as a template context processor (settings.TEMPLATES) so
    templates/base.html can show the count on every page without every
    view having to remember to pass it in. Recomputed on each request
    (no caching, no real-time push), which satisfies "se puede
    actualizar al cargar una página" without any extra infrastructure.
    """
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0, "recent_notifications": []}
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    # Latest few notifications for the top-bar dropdown. Querysets are
    # lazy, so this only hits the database on pages that actually render
    # the dropdown; scoped to request.user exactly like the inbox view.
    recent = Notification.objects.filter(recipient=request.user).select_related(
        "ticket"
    )[:RECENT_NOTIFICATIONS_LIMIT]
    return {"unread_notifications_count": count, "recent_notifications": recent}
