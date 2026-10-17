from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Notification

# Inbox filters offered as tabs in the notification center. "unread" is
# a read-state filter; the rest map 1:1 to Notification.NotificationType.
UNREAD_FILTER = "unread"


def _redirect_back(request, fallback="notifications:list"):
    """Redirect to a same-site ``next`` (e.g. the page the top-bar
    dropdown was opened from), or to ``fallback``. Off-site/unsafe
    targets are ignored, so this can't be used as an open redirect."""
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect(fallback)


@login_required
def notification_list(request):
    # Scoped to the authenticated user only: there is no way to pass a
    # different user's id here, so this can't be manipulated via the URL.
    # select_related("ticket") avoids one extra query per row for the
    # ticket.pk/ticket_number the template reads on every notification.
    own_notifications = Notification.objects.filter(recipient=request.user)
    notifications = own_notifications.select_related("ticket")

    # Optional tab filter, validated against known values (anything else
    # is ignored and the full inbox is shown).
    active_filter = request.GET.get("filter", "")
    if active_filter == UNREAD_FILTER:
        notifications = notifications.filter(is_read=False)
    elif active_filter in Notification.NotificationType.values:
        notifications = notifications.filter(notification_type=active_filter)
    else:
        active_filter = ""

    # Per-type counts for the tabs: one grouped query.
    type_counts = dict(
        own_notifications.values_list("notification_type")
        .annotate(count=Count("id"))
        .order_by()
    )

    page_obj = Paginator(notifications, settings.PAGE_SIZE).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "notifications/notification_list.html",
        {
            "page_obj": page_obj,
            "active_filter": active_filter,
            "total_count": sum(type_counts.values()),
            "type_tabs": [
                (value, label, type_counts.get(value, 0))
                for value, label in Notification.NotificationType.choices
            ],
        },
    )


@login_required
@require_POST
def notification_mark_read(request, pk):
    # recipient=request.user makes a notification belonging to someone
    # else a 404, not just a permission error: a user can't even confirm
    # another user's notification exists by probing this URL.
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    return _redirect_back(request)


@login_required
@require_POST
def notification_mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    return _redirect_back(request)
