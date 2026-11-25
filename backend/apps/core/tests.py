from unittest.mock import patch

from django.db import DatabaseError
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import override_settings


class HealthEndpointTests(APITestCase):
    def test_health_endpoint_is_public_without_exposing_service_details(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})
        self.assertNotIn("service", response.data)
        self.assertNotIn("version", response.data)

    def test_readiness_endpoint_checks_service_readiness_without_exposing_database_details(self):
        response = self.client.get("/api/ready/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ready"})
        self.assertNotIn("database", response.data)

    @patch("apps.core.views.connection.cursor", side_effect=DatabaseError("database unavailable"))
    def test_readiness_endpoint_returns_unavailable_when_database_cannot_be_reached(self, cursor):
        response = self.client.get("/api/ready/")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data, {"status": "not_ready"})

    @override_settings(
        SECURE_HSTS_SECONDS=31536000,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=False,
        SECURE_HSTS_PRELOAD=False,
    )
    def test_https_responses_include_hsts_without_subdomain_or_preload_flags(self):
        response = self.client.get("/api/health/", secure=True)
        self.assertEqual(
            response.headers.get("Strict-Transport-Security"),
            "max-age=31536000",
        )
