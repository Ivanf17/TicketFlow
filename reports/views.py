from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import (
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    OuterRef,
    Subquery,
)
from django.shortcuts import render

from administration.models import Area
from tickets.models import Ticket, TicketHistory
from users.models import User

from .permissions import can_access_dashboard, get_dashboard_tickets_queryset
from .services import format_average_resolution, parse_date_param

RECENT_TICKETS_LIMIT = 10


@login_required
def dashboard(request):
    if not can_access_dashboard(request.user):
        raise PermissionDenied("You do not have access to the dashboard.")

    # --- Base queryset: the single source of truth for "what can this
    # user see", everything below is derived from it (or a further
    # filter of it), so every metric on the page reflects the same set.
    queryset = get_dashboard_tickets_queryset(request.user)

    # --- Area filter: selectable only for admin/management. For an
    # area_manager the area is fixed to their own and the querystring is
    # never even read, so a manipulated ?area=... can't do anything.
    areas_for_filter = None
    selected_area = None
    if request.user.role in (User.Role.ADMIN, User.Role.MANAGEMENT):
        areas_for_filter = Area.objects.order_by("name")
        area_param = request.GET.get("area")
        if area_param:
            try:
                selected_area = areas_for_filter.get(pk=int(area_param))
            except (ValueError, Area.DoesNotExist):
                selected_area = None
        if selected_area is not None:
            queryset = queryset.filter(category__area=selected_area)
    elif request.user.role == User.Role.AREA_MANAGER:
        selected_area = request.user.area

    # --- Date filters (server-validated; a bad format is dropped, not
    # trusted, and never crashes the page).
    start_date, start_date_error = parse_date_param(request.GET.get("start_date"))
    end_date, end_date_error = parse_date_param(request.GET.get("end_date"))

    date_range_error = None
    if start_date and end_date and start_date > end_date:
        # An inverted range would silently produce an empty (and
        # misleading) result set; surface it and drop both filters
        # instead of pretending "no tickets" is the real answer.
        date_range_error = (
            "La fecha inicial no puede ser posterior a la fecha final. "
            "Se ignoraron los filtros de fecha."
        )
        start_date = None
        end_date = None

    if start_date:
        queryset = queryset.filter(created_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__date__lte=end_date)

    # --- Status counts: one query, grouped in the database.
    status_counts = dict(
        queryset.values_list("status").annotate(count=Count("id")).order_by()
    )
    pending = status_counts.get(Ticket.Status.PENDING, 0)
    in_process = status_counts.get(Ticket.Status.IN_PROCESS, 0)
    resolved = status_counts.get(Ticket.Status.RESOLVED, 0)
    total = pending + in_process + resolved

    # --- Tickets by area: one query, grouped in the database. Ticket has
    # no area FK of its own; the area comes from category__area, exactly
    # as established in Block 3/4 (Ticket.area is a Python property, not
    # a column, so it can't be used inside .values()/.annotate()).
    by_area = list(
        queryset.values("category__area__id", "category__area__name")
        .annotate(count=Count("id"))
        .order_by("category__area__name")
    )

    # --- Average resolution time. RESOLVED is terminal in the state
    # machine (Block 5): a ticket can reach it at most once, via exactly
    # one IN_PROCESS -> RESOLVED TicketHistory entry, so this subquery
    # picks that single row (defensively ordered/limited to one, in case
    # older data ever violated that invariant) rather than trusting
    # Ticket.updated_at, which just reflects the *last* save for any
    # reason.
    resolution_at = (
        TicketHistory.objects.filter(
            ticket=OuterRef("pk"),
            status=Ticket.Status.RESOLVED,
            previous_status=Ticket.Status.IN_PROCESS,
        )
        .order_by("created_at")
        .values("created_at")[:1]
    )
    resolved_with_duration = (
        queryset.filter(status=Ticket.Status.RESOLVED)
        .annotate(resolved_at=Subquery(resolution_at))
        .annotate(
            resolution_duration=ExpressionWrapper(
                F("resolved_at") - F("created_at"), output_field=DurationField()
            )
        )
    )
    average_duration = resolved_with_duration.aggregate(avg=Avg("resolution_duration"))[
        "avg"
    ]
    average_resolution_label = format_average_resolution(average_duration)

    # --- Recent tickets: select_related to avoid N+1 while rendering
    # category/area/created_by/assigned_to for each row. Tie-broken by
    # id (in addition to created_at) so the order is fully deterministic
    # even when two tickets share the same timestamp.
    #
    # Management's dashboard scope is management-level reporting (global
    # metrics, counts, average resolution time), not individual ticket
    # content, and tickets.permissions.get_visible_tickets deliberately
    # denies management access to ticket detail. Rather than linking to
    # a detail page that would 404, the "recent tickets" widget is
    # skipped for management entirely: the query is never built (using
    # .none(), which never hits the database), not just hidden after
    # the fact.
    show_recent_tickets = request.user.role != User.Role.MANAGEMENT
    if show_recent_tickets:
        recent_tickets = queryset.select_related(
            "category", "category__area", "created_by", "assigned_to"
        ).order_by("-created_at", "-id")[:RECENT_TICKETS_LIMIT]
    else:
        recent_tickets = Ticket.objects.none()

    context = {
        "total": total,
        "pending": pending,
        "in_process": in_process,
        "resolved": resolved,
        "average_resolution_label": average_resolution_label,
        "by_area": by_area,
        "show_recent_tickets": show_recent_tickets,
        "recent_tickets": recent_tickets,
        "areas_for_filter": areas_for_filter,
        "selected_area": selected_area,
        "start_date_value": request.GET.get("start_date", ""),
        "end_date_value": request.GET.get("end_date", ""),
        "start_date_error": start_date_error,
        "end_date_error": end_date_error,
        "date_range_error": date_range_error,
        "status_labels": [
            Ticket.Status.PENDING.label,
            Ticket.Status.IN_PROCESS.label,
            Ticket.Status.RESOLVED.label,
        ],
        "status_values": [pending, in_process, resolved],
        "area_labels": [row["category__area__name"] for row in by_area],
        "area_values": [row["count"] for row in by_area],
    }
    return render(request, "reports/dashboard.html", context)
