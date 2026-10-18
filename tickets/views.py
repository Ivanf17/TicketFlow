from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from assignment.permissions import can_manage_ticket_assignment
from assignment.services import AssignmentError, assign_ticket, auto_assign_ticket
from notifications.services import notify_ticket_comment_added

from .forms import TicketAssignForm, TicketCommentForm, TicketCreateForm, TicketStatusChangeForm
from .models import Ticket, TicketComment
from .permissions import can_manage_ticket_status, get_visible_tickets
from .services import StatusTransitionError, change_ticket_status, get_next_status

# List-only pseudo-status ("Mis tickets" for area managers): every ticket
# not yet resolved. Not a stored state, just a filter over Ticket.Status.
OPEN_STATUS_FILTER = "OPEN"
OPEN_STATUSES = (Ticket.Status.PENDING, Ticket.Status.IN_PROCESS)


@login_required
def ticket_create(request):
    if request.user.role != request.user.Role.EMPLOYEE:
        raise PermissionDenied("Only employees can create tickets.")
    if request.method == "POST":
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            ticket = Ticket.objects.create_ticket(
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                category=form.cleaned_data["category"],
                created_by=request.user,
            )
            auto_assign_ticket(ticket)
            return redirect("tickets:detail", pk=ticket.pk)
    else:
        form = TicketCreateForm()
    return render(request, "tickets/ticket_form.html", {"form": form})


@login_required
def ticket_list(request):
    # select_related avoids one extra query per row for each of these
    # FKs (category, category.area, created_by, assigned_to), all of
    # which the template reads per ticket. Purely a load-time
    # optimization: get_visible_tickets' filtering/visibility is
    # untouched, this only changes how the same rows are fetched.
    visible = get_visible_tickets(request.user)

    # Summary counts for the metric cards, computed over everything the
    # user can see (before the filters below), in one grouped query.
    status_counts = dict(
        visible.values_list("status").annotate(count=Count("id")).order_by()
    )
    unassigned_pending_count = visible.filter(
        assigned_to__isnull=True, status=Ticket.Status.PENDING
    ).count()

    # Optional list filters. They only ever narrow get_visible_tickets'
    # result, so they can't widen what a role is allowed to see; unknown
    # values are ignored instead of trusted.
    tickets = visible
    status_filter = request.GET.get("status", "")
    if status_filter in Ticket.Status.values:
        tickets = tickets.filter(status=status_filter)
    elif status_filter == OPEN_STATUS_FILTER:
        tickets = tickets.filter(status__in=OPEN_STATUSES)
    else:
        status_filter = ""
    assignment_filter = request.GET.get("assignment", "")
    if assignment_filter == "unassigned":
        tickets = tickets.filter(assigned_to__isnull=True)
    elif assignment_filter == "assigned":
        tickets = tickets.filter(assigned_to__isnull=False)
    else:
        assignment_filter = ""
    search = request.GET.get("q", "").strip()
    if search:
        tickets = tickets.filter(
            Q(ticket_number__icontains=search) | Q(title__icontains=search)
        )

    tickets = tickets.select_related(
        "category", "category__area", "created_by", "assigned_to"
    )
    page_obj = Paginator(tickets, settings.PAGE_SIZE).get_page(request.GET.get("page"))
    pending = status_counts.get(Ticket.Status.PENDING, 0)
    in_process = status_counts.get(Ticket.Status.IN_PROCESS, 0)
    resolved = status_counts.get(Ticket.Status.RESOLVED, 0)
    return render(
        request,
        "tickets/ticket_list.html",
        {
            "page_obj": page_obj,
            "count_total": pending + in_process + resolved,
            "count_pending": pending,
            "count_in_process": in_process,
            "count_resolved": resolved,
            "count_unassigned_pending": unassigned_pending_count,
            # "Mis tickets" card: same statuses the OPEN filter applies.
            "count_open": pending + in_process,
            "open_status_filter": OPEN_STATUS_FILTER,
            "status_filter": status_filter,
            "assignment_filter": assignment_filter,
            "search": search,
            "status_choices": Ticket.Status.choices,
            "filters_active": bool(status_filter or assignment_filter or search),
        },
    )


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(get_visible_tickets(request.user), pk=pk)
    can_assign = can_manage_ticket_assignment(request.user, ticket)
    can_manage_status = can_manage_ticket_status(request.user, ticket)
    next_status = get_next_status(ticket.status)

    # Presentation of the linear PENDING -> IN_PROCESS -> RESOLVED flow:
    # each step is matched with the TicketHistory entry that reached it
    # (if any). Read-only; transitions are still only possible through
    # ticket_change_status / change_ticket_status.
    history = list(ticket.history.select_related("changed_by"))
    reached = {}
    for entry in history:
        reached.setdefault(entry.status, entry)
    statuses = list(Ticket.Status)
    current_index = statuses.index(ticket.status)
    status_steps = [
        {
            "number": index + 1,
            "label": status.label,
            "entry": reached.get(status),
            "state": (
                "done"
                if index < current_index
                else "current" if index == current_index else "upcoming"
            ),
            "is_final": index == len(statuses) - 1,
        }
        for index, status in enumerate(statuses)
    ]
    return render(
        request,
        "tickets/ticket_detail.html",
        {
            "ticket": ticket,
            "history": history,
            "status_steps": status_steps,
            "current_step": current_index + 1,
            "total_steps": len(statuses),
            "can_assign": can_assign,
            "can_change_status": can_manage_status and next_status is not None,
            "next_status": next_status,
            "no_status_actions": can_manage_status and next_status is None,
            "comment_form": TicketCommentForm(),
        },
    )


@login_required
def ticket_assign(request, pk):
    ticket = get_object_or_404(get_visible_tickets(request.user), pk=pk)
    if not can_manage_ticket_assignment(request.user, ticket):
        raise PermissionDenied("You are not allowed to assign this ticket.")

    if request.method == "POST":
        form = TicketAssignForm(request.POST, ticket=ticket)
        if form.is_valid():
            try:
                assign_ticket(
                    ticket,
                    assigned_to=form.cleaned_data["assigned_to"],
                    changed_by=request.user,
                )
            except AssignmentError as exc:
                form.add_error("assigned_to", str(exc))
            else:
                return redirect("tickets:detail", pk=ticket.pk)
    else:
        form = TicketAssignForm(ticket=ticket, initial={"assigned_to": ticket.assigned_to_id})
    return render(
        request, "tickets/ticket_assign.html", {"ticket": ticket, "form": form}
    )


@login_required
@require_POST
def ticket_change_status(request, pk):
    ticket = get_object_or_404(get_visible_tickets(request.user), pk=pk)
    if not can_manage_ticket_status(request.user, ticket):
        raise PermissionDenied("You are not allowed to change this ticket's status.")

    form = TicketStatusChangeForm(request.POST, ticket=ticket)
    if form.is_valid():
        try:
            change_ticket_status(
                ticket,
                new_status=form.cleaned_data["status"],
                changed_by=request.user,
            )
        except StatusTransitionError:
            messages.error(request, "Ese cambio de estado no está permitido.")
        else:
            messages.success(request, "Estado del ticket actualizado.")
    else:
        messages.error(request, "Ese cambio de estado no está permitido.")
    return redirect("tickets:detail", pk=ticket.pk)


@login_required
@require_POST
def ticket_comment_create(request, pk):
    # Same visibility rule as ticket_detail: whoever can see the ticket
    # can comment on it. RESOLVED tickets are included on purpose -- a
    # comment is purely informative and never touches status/assignment.
    ticket = get_object_or_404(get_visible_tickets(request.user), pk=pk)
    form = TicketCommentForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            TicketComment.objects.create(
                ticket=ticket, author=request.user, content=form.cleaned_data["content"]
            )
            notify_ticket_comment_added(ticket, author=request.user)
        messages.success(request, "Comentario agregado.")
    else:
        messages.error(request, "El comentario no puede estar vacío.")
    return redirect("tickets:detail", pk=ticket.pk)
