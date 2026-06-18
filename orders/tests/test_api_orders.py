import pytest
from django.urls import reverse

from orders.models import Contact, Order, OrderItem


@pytest.mark.django_db
def test_order_create_and_list(auth_client, user, product_info):
    contact = Contact.objects.create(
        user=user,
        city="Moscow",
        street="Test Street",
        house="1",
        apartment="10",
        phone="+79999999999",
    )

    basket = Order.objects.create(
        user=user,
        status="basket",
    )

    OrderItem.objects.create(
        order=basket,
        product_info=product_info,
        quantity=1,
    )

    create_response = auth_client.post(
        reverse("order"),
        {
            "id": basket.id,
            "contact": contact.id,
        },
    )

    assert create_response.status_code == 200

    basket.refresh_from_db()

    assert basket.status == "new"
    assert basket.contact == contact

    list_response = auth_client.get(reverse("order"))

    assert list_response.status_code == 200
    assert list_response.data[0]["number"] == basket.id