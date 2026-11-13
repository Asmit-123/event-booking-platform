from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator

from accounts.permissions import organizer_required

from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from . import exports, selectors, services
from .forms import EventForm, EventSearchForm
from .models import Event

from django.urls import reverse

from . import exports, ics, selectors, services

EVENTS_PER_PAGE = 9

def home(request):
    featured = selectors.upcoming_events()[:3]
    return render(request, "events/home.html", {"featured": featured})


@organizer_required
def organizer_dashboard(request):
    events = list(selectors.organizer_events(request.user))
    context = {"events": events, "stats": selectors.summarize_organizer_events(events)}
    return render(request, "events/organizer_dashboard.html", context)


@organizer_required
def event_create(request):
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            try:
                data = form.cleaned_data.copy()\n                data.pop("use_registration_deadline", None)\n                event = services.create_event(request.user, **data)
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
                data = form.cleaned_data.copy()\n                data.pop("use_registration_deadline", None)\n                updated = services.update_event(request.user, event.pk, **data)
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
    form = EventSearchForm(request.GET)
    events = selectors.upcoming_events()
    has_filters = False

    if form.is_valid():
        data = form.cleaned_data
        events = selectors.search_events(events, data["q"])
        events = selectors.filter_by_date_range(events, data["date_from"], data["date_to"])
        if data["available_only"]:
            events = selectors.only_with_seats(events)
        has_filters = any(data.values())

    paginator = Paginator(events, EVENTS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))
    context = {"page": page, "form": form, "has_filters": has_filters}
    return render(request, "events/event_list.html", context)

def event_detail(request, pk):
    event = get_object_or_404(selectors.events_with_seats(), pk=pk)
    is_registered = (
        request.user.is_authenticated
        and event.registrations.filter(attendee=request.user).exists()
    )
    context = {"event": event, "is_registered": is_registered}
    return render(request, "events/event_detail.html", context)

@organizer_required
@require_GET
@never_cache
def event_attendees_csv(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="attendees-event-{event.pk}.csv"'
    exports.write_attendees_csv(response, selectors.event_registrations(event))
    return response

@require_GET
def event_calendar(request, pk):
    event = get_object_or_404(Event, pk=pk, status=Event.Status.ACTIVE)
    url = request.build_absolute_uri(reverse("events:event_detail", args=[event.pk]))
    response = HttpResponse(ics.build_ics(event, url), content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="event-{event.pk}.ics"'
    return response