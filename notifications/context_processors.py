from .models import Notification


def unread_notifications_count(request):
    """Adds ``unread_notifications_count`` to every template's context.

    Registered as a template context processor (settings.TEMPLATES) so
    templates/base.html can show the count on every page without every
    view having to remember to pass it in. Recomputed on each request
    (no caching, no real-time push), which satisfies "se puede
    actualizar al cargar una página" without any extra infrastructure.
    """
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0}
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return {"unread_notifications_count": count}
