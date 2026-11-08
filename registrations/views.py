from django.shortcuts import render

from accounts.permissions import attendee_required


@attendee_required
def my_registrations(request):
    return render(request, "registrations/my_registrations.html")