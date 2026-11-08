from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from accounts.permissions import organizer_required

from . import selectors, services
from .forms import EventForm


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