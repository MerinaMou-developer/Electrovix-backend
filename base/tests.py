from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from base.factories import BrandFactory, CategoryFactory, ProductFactory
from base.utils.catalog_cache import invalidate_catalog_cache


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

    def test_products_list_uses_catalog_cache(self):
        cache.clear()
        invalidate_catalog_cache()
        CategoryFactory()
        BrandFactory()
        ProductFactory()

        first = self.client.get(reverse("products"))
        second = self.client.get(reverse("products"))

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.get("X-Cache"), "MISS")
        self.assertEqual(second.get("X-Cache"), "HIT")
