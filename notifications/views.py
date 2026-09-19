from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    # Scoped to the authenticated user only: there is no way to pass a
    # different user's id here, so this can't be manipulated via the URL.
    notifications = Notification.objects.filter(recipient=request.user)
    return render(
        request, "notifications/notification_list.html", {"notifications": notifications}
    )


@login_required
@require_POST
def notification_mark_read(request, pk):
    # recipient=request.user makes a notification belonging to someone
    # else a 404, not just a permission error: a user can't even confirm
    # another user's notification exists by probing this URL.
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    return redirect("notifications:list")


@login_required
@require_POST
def notification_mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    return redirect("notifications:list")
