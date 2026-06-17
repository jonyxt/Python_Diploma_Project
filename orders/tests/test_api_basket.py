# backend/tests/test_api_basket.py

import pytest
from django.urls import reverse

from orders.models import Order, OrderItem


@pytest.mark.django_db
def test_add_product_to_basket(auth_client, user, product_info):
    url = reverse("basket")

    payload = {
        "product_info": product_info.id,
        "quantity": 2,
    }

    response = auth_client.post(url, payload, format="json")

    assert response.status_code in (200, 201)
    assert Order.objects.filter(user=user, status="basket").exists()
    assert OrderItem.objects.filter(
        product_info=product_info,
        quantity=2,
    ).exists()