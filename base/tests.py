from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class PublicApiSmokeTests(APITestCase):
    def test_products_list_endpoint_returns_success(self):
        response = self.client.get(reverse("products"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("products", response.data)
        self.assertIn("page", response.data)
        self.assertIn("pages", response.data)
        self.assertIn("total", response.data)

    def test_categories_endpoint_returns_success(self):
        response = self.client.get(reverse("category"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_brand_endpoint_returns_success(self):
        response = self.client.get(reverse("brand"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hybrid_search_requires_query(self):
        response = self.client.get(reverse("hybrid-search"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_profile_endpoint_requires_authentication(self):
        response = self.client.get(reverse("users-profile"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
