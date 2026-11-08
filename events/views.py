from django.shortcuts import render

from accounts.permissions import organizer_required


def home(request):
    return render(request, "events/home.html")


@organizer_required
def organizer_dashboard(request):
    return render(request, "events/organizer_dashboard.html")