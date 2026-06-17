# backend/tests/test_api_auth.py

import pytest
from django.urls import reverse

from orders.models import User


@pytest.mark.django_db
def test_user_registration(api_client):
    url = reverse("user-register")

    payload = {
        "email": "newuser@example.com",
        "password": "testpass123",
        "first_name": "New",
        "last_name": "User",
        "company": "Test Company",
        "position": "Buyer",
    }

    response = api_client.post(url, payload, format="json")

    assert response.status_code in (200, 201)
    assert User.objects.filter(email="newuser@example.com").exists()