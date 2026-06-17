# backend/tests/test_api_orders.py

import pytest
from django.urls import reverse

from orders.models import Order, OrderItem, Contact


@pytest.mark.django_db
def test_confirm_order(auth_client, user, product_info, mocker):
    contact = Contact.objects.create(
        user=user,
        city="Moscow",
        street="Test Street",
        house="1",
        structure="",
        building="",
        apartment="10",
        phone="+79999999999",
    )

    order = Order.objects.create(
        user=user,
        status="basket",
    )

    OrderItem.objects.create(
        order=order,
        product_info=product_info,
        quantity=1,
    )

    mocked_task = mocker.patch("orders.tasks.send_email.delay")

    url = reverse("order-confirm")
    payload = {
        "basket_id": order.id,
        "contact_id": contact.id,
    }

    response = auth_client.post(url, payload, format="json")

    assert response.status_code in (200, 201)

    order.refresh_from_db()

    assert order.status != "basket"
    assert order.contact == contact

    assert mocked_task.call_count == 2

    called_recipient_lists = [
        call.kwargs["recipient_list"]
        for call in mocked_task.call_args_list
    ]

    assert [user.email] in called_recipient_lists
    assert ["admin@example.com"] in called_recipient_lists