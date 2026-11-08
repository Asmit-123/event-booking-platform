from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator

from accounts.permissions import organizer_required

from . import selectors, services
from .forms import EventForm
from .models import Event

EVENTS_PER_PAGE = 9

def home(request):
    return render(request, "events/home.html")


@organizer_required
def organizer_dashboard(request):
    events = selectors.organizer_events(request.user)
    return render(request, "events/organizer_dashboard.html", {"events": events})


@organizer_required
def event_create(request):
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            try:
                event = services.create_event(request.user, **form.cleaned_data)
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, f"\u201c{event.title}\u201d has been created.")
                return redirect("events:organizer_dashboard")
    else:
        form = EventForm()

    context = {"form": form, "heading": "Create event", "submit_label": "Create event"}
    return render(request, "events/event_form.html", context)


@organizer_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if not event.is_editable:
        messages.error(request, "Cancelled or past events can no longer be edited.")
        return redirect("events:organizer_dashboard")

    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            try:
                updated = services.update_event(request.user, event.pk, **form.cleaned_data)
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, f"\u201c{updated.title}\u201d has been updated.")
                return redirect("events:organizer_dashboard")
    else:
        form = EventForm(instance=event)

    context = {"form": form, "heading": "Edit event", "submit_label": "Save changes"}
    return render(request, "events/event_form.html", context)

@organizer_required
def event_cancel(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if not event.is_editable:
        messages.error(request, "Only active, upcoming events can be cancelled.")
        return redirect("events:organizer_dashboard")

    if request.method == "POST":
        try:
            services.cancel_event(request.user, event.pk)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, f"\u201c{event.title}\u201d has been cancelled.")
        return redirect("events:organizer_dashboard")

    context = {"event": event, "registered": event.registrations.count()}
    return render(request, "events/event_cancel_confirm.html", context)

@organizer_required
def event_attendees(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    registrations = selectors.event_registrations(event)
    context = {"event": event, "registrations": registrations}
    return render(request, "events/event_attendees.html", context)

def event_list(request):
    paginator = Paginator(selectors.upcoming_events(), EVENTS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "events/event_list.html", {"page": page})


def event_detail(request, pk):
    event = get_object_or_404(selectors.events_with_seats(), pk=pk)
    is_registered = (
        request.user.is_authenticated
        and event.registrations.filter(attendee=request.user).exists()
    )
    context = {"event": event, "is_registered": is_registered}
    return render(request, "events/event_detail.html", context)