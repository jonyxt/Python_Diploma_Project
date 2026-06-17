# backend/tests/test_api_products.py

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_products_list_available_for_anonymous_user(api_client, product_info):
    url = reverse("products")

    response = api_client.get(url)

    assert response.status_code == 200
    assert "iPhone 15" in str(response.data)