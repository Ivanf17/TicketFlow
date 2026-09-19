from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from assignment.permissions import can_manage_ticket_assignment
from assignment.services import AssignmentError, assign_ticket, auto_assign_ticket

from .forms import TicketAssignForm, TicketCreateForm, TicketStatusChangeForm
from .models import Ticket
from .permissions import can_manage_ticket_status, get_visible_tickets
from .services import StatusTransitionError, change_ticket_status, get_next_status


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
    tickets = get_visible_tickets(request.user)
    return render(request, "tickets/ticket_list.html", {"tickets": tickets})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(get_visible_tickets(request.user), pk=pk)
    can_assign = can_manage_ticket_assignment(request.user, ticket)
    can_manage_status = can_manage_ticket_status(request.user, ticket)
    next_status = get_next_status(ticket.status)
    return render(
        request,
        "tickets/ticket_detail.html",
        {
            "ticket": ticket,
            "can_assign": can_assign,
            "can_change_status": can_manage_status and next_status is not None,
            "next_status": next_status,
            "no_status_actions": can_manage_status and next_status is None,
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
            messages.error(request, "That status change is not allowed.")
        else:
            messages.success(request, "Ticket status updated.")
    else:
        messages.error(request, "That status change is not allowed.")
    return redirect("tickets:detail", pk=ticket.pk)
