"""IP geolocation through the ip-api.com JSON API.

Everything that talks to the network lives here so the view stays small and
the lookup can be tested without a real API call.
"""

from __future__ import annotations

import ipaddress
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# The free tier of ip-api.com is served over plain http only.
API_URL = "http://ip-api.com/json/"


class GeolocationError(Exception):
    """A lookup failed. The message is safe to show to the user."""


def client_ip(request) -> str:
    """Return the visitor's public IP address, or "" if it cannot be known.

    A private or loopback address (local development, or a proxy in front of
    the app) says nothing about where the visitor is, so it is reported as "".
    """
    candidate = request.META.get("REMOTE_ADDR", "")
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            candidate = forwarded.split(",")[0].strip()
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return ""
    return str(address) if address.is_global else ""


def locate(ip: str = "") -> dict:
    """Return ip-api.com's location record for ``ip``.

    With an empty ``ip`` the service locates the address the request comes
    from, which is this server's own public address.
    """
    try:
        response = requests.get(API_URL + ip, timeout=settings.GEOLOCATION_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.error("Geolocation request failed: %s", type(exc).__name__)
        raise GeolocationError(
            "The location service could not be reached. Try again later."
        ) from exc

    if not isinstance(data, dict) or data.get("status") != "success":
        reason = data.get("message", "unknown") if isinstance(data, dict) else "unknown"
        logger.warning("Geolocation lookup was refused: %s", reason)
        raise GeolocationError("The location for this address could not be determined.")
    return data
