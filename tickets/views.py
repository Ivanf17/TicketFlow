from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TicketCreateForm
from .models import Ticket
from .permissions import get_visible_tickets


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
    return render(request, "tickets/ticket_detail.html", {"ticket": ticket})
