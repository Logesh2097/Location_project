from django.shortcuts import render

from .geolocation import GeolocationError, client_ip, locate


def index(request):
    """Show the approximate location of the visitor's IP address."""
    context = {"data": None, "error": ""}
    try:
        context["data"] = locate(client_ip(request))
    except GeolocationError as exc:
        context["error"] = str(exc)
    return render(request, "index.html", context)
