"""Tests for the location lookup. No test makes a real network call."""

from unittest import mock

import requests
from django.test import RequestFactory, SimpleTestCase, override_settings

from .geolocation import GeolocationError, client_ip, locate

SAMPLE_RESPONSE = {
    "status": "success",
    "query": "8.8.8.8",
    "country": "United States",
    "countryCode": "US",
    "city": "Ashburn",
    "zip": "20149",
    "lat": 39.03,
    "lon": -77.5,
    "timezone": "America/New_York",
}


def fake_response(payload, status_code=200):
    response = mock.Mock(status_code=status_code)
    response.json.return_value = payload
    response.raise_for_status.side_effect = (
        requests.HTTPError(f"HTTP {status_code}") if status_code >= 400 else None
    )
    return response


class ClientIpTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_a_public_address_is_used(self):
        request = self.factory.get("/", REMOTE_ADDR="8.8.8.8")

        self.assertEqual(client_ip(request), "8.8.8.8")

    def test_a_loopback_or_private_address_is_not_used(self):
        for address in ("127.0.0.1", "192.168.1.20", "10.0.0.5", "::1"):
            with self.subTest(address=address):
                request = self.factory.get("/", REMOTE_ADDR=address)

                self.assertEqual(client_ip(request), "")

    def test_the_forwarded_header_is_ignored_by_default(self):
        request = self.factory.get("/", REMOTE_ADDR="8.8.8.8", HTTP_X_FORWARDED_FOR="1.1.1.1")

        self.assertEqual(client_ip(request), "8.8.8.8")

    @override_settings(TRUST_X_FORWARDED_FOR=True)
    def test_the_forwarded_header_is_used_when_trusted(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.1.1.1, 10.0.0.1"
        )

        self.assertEqual(client_ip(request), "1.1.1.1")

    @override_settings(TRUST_X_FORWARDED_FOR=True)
    def test_a_forged_forwarded_value_is_never_passed_on(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="../batch?x=1"
        )

        self.assertEqual(client_ip(request), "")


class LocateTests(SimpleTestCase):
    @mock.patch("location_app.geolocation.requests.get")
    def test_a_lookup_returns_the_location_record(self, get):
        get.return_value = fake_response(SAMPLE_RESPONSE)

        data = locate("8.8.8.8")

        self.assertEqual(data["city"], "Ashburn")
        self.assertTrue(get.call_args.args[0].endswith("/json/8.8.8.8"))
        self.assertIn("timeout", get.call_args.kwargs)

    @mock.patch("location_app.geolocation.requests.get")
    def test_a_refused_lookup_is_reported(self, get):
        get.return_value = fake_response({"status": "fail", "message": "private range"})

        with self.assertRaisesMessage(GeolocationError, "could not be determined"):
            locate("8.8.8.8")

    @mock.patch("location_app.geolocation.requests.get")
    def test_a_network_failure_is_reported(self, get):
        get.side_effect = requests.ConnectionError("unreachable")

        with self.assertRaisesMessage(GeolocationError, "could not be reached"):
            locate("8.8.8.8")

    @mock.patch("location_app.geolocation.requests.get")
    def test_a_rate_limit_response_is_reported(self, get):
        get.return_value = fake_response({}, status_code=429)

        with self.assertRaisesMessage(GeolocationError, "could not be reached"):
            locate("8.8.8.8")


class IndexViewTests(SimpleTestCase):
    @mock.patch("location_app.geolocation.requests.get")
    def test_a_public_visitor_sees_the_location_of_their_address(self, get):
        get.return_value = fake_response(SAMPLE_RESPONSE)

        response = self.client.get("/", REMOTE_ADDR="8.8.8.8")

        self.assertContains(response, "Your Location - 8.8.8.8")
        self.assertContains(response, "City: Ashburn")
        self.assertTrue(get.call_args.args[0].endswith("/json/8.8.8.8"))

    @mock.patch("location_app.geolocation.requests.get")
    def test_a_local_visitor_falls_back_to_the_servers_own_address(self, get):
        get.return_value = fake_response(SAMPLE_RESPONSE)

        self.client.get("/", REMOTE_ADDR="127.0.0.1")

        self.assertTrue(get.call_args.args[0].endswith("/json/"))

    @mock.patch("location_app.geolocation.requests.get")
    def test_a_failed_lookup_shows_a_message_instead_of_crashing(self, get):
        get.side_effect = requests.Timeout("slow")

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "could not be reached")
