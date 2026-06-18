import pytest
from django.urls import reverse

from orders.models import Contact, Order, OrderItem


@pytest.mark.django_db
def test_order_create_and_list(auth_client, user, product_info, mocker):
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

    mocked_send_email = mocker.patch("orders.views.send_email.delay")

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

    assert mocked_send_email.call_count == 2

    recipient_lists = [
        call.kwargs["recipient_list"]
        for call in mocked_send_email.call_args_list
    ]

    assert [user.email] in recipient_lists
    assert ["admin@example.com"] in recipient_lists

    list_response = auth_client.get(reverse("order"))

    assert list_response.status_code == 200
    assert list_response.data[0]["number"] == basket.id

    detail_response = auth_client.get(
        reverse(
            "order-detail",
            kwargs={"order_id": basket.id}
        )
    )

    assert detail_response.status_code == 200
    assert detail_response.data["number"] == basket.id
    assert detail_response.data["status"] == "new"