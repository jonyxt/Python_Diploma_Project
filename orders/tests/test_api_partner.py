import pytest
from django.urls import reverse

from orders.models import Contact, Order, OrderItem


@pytest.mark.django_db
def test_partner_state_get_and_update(supplier_client, shop):
    get_response = supplier_client.get(reverse("partner-state"))

    assert get_response.status_code == 200
    assert get_response.data["state"] == "on"

    update_response = supplier_client.post(
        reverse("partner-state"),
        {"state": "off"},
    )

    assert update_response.status_code == 200

    shop.refresh_from_db()

    assert shop.is_active is False


@pytest.mark.django_db
def test_partner_orders(supplier_client, user, shop, product_info):
    contact = Contact.objects.create(
        user=user,
        city="Moscow",
        street="Test Street",
        house="1",
        phone="+79999999999",
    )

    order = Order.objects.create(
        user=user,
        contact=contact,
        status="new",
    )

    OrderItem.objects.create(
        order=order,
        product_info=product_info,
        quantity=1,
    )

    response = supplier_client.get(reverse("partner-orders"))

    assert response.status_code == 200
    assert response.data[0]["number"] == order.id


@pytest.mark.django_db
def test_partner_update_starts_import_task(supplier_client, mocker):
    response_mock = mocker.MagicMock()
    response_mock.__enter__.return_value.read.return_value = b"shop: Test Shop"
    response_mock.__exit__.return_value = None

    mocked_urlopen = mocker.patch(
        "orders.views.urlopen",
        return_value=response_mock,
    )
    mocked_task = mocker.patch("orders.views.do_import.delay")
    mocked_task.return_value.id = "task-id"

    response = supplier_client.post(
        reverse("partner-update"),
        {"url": "https://example.com/shop.yaml"},
    )

    assert response.status_code == 202

    mocked_urlopen.assert_called_once_with(
        "https://example.com/shop.yaml",
        timeout=10,
    )

    mocked_task.assert_called_once()
    assert mocked_task.call_args.kwargs["yaml_text"] == "shop: Test Shop"
    assert mocked_task.call_args.kwargs["user_id"]