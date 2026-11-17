from rest_framework import status
from rest_framework.test import APITestCase


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
