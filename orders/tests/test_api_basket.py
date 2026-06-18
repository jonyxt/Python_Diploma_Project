import pytest
from django.urls import reverse

from orders.models import OrderItem


@pytest.mark.django_db
def test_basket_crud(auth_client, product_info):
    url = reverse("basket")

    add_response = auth_client.post(
        url,
        {
            "items": (
                '[{"product_info": %s, "quantity": 2,}]'
                % product_info.id
            )
        },
    )

    assert add_response.status_code == 201
    item_id = add_response.data["items"][0]

    get_response = auth_client.get(url)

    assert get_response.status_code == 200
    assert get_response.data["items"][0]["id"] == item_id
    assert get_response.data["items"][0]["quantity"] == 2

    update_response = auth_client.put(
        url,
        {
            "items": (
                '[{"id": %s, "quantity": 1,}]'
                % item_id
            )
        },
    )

    assert update_response.status_code == 200
    assert OrderItem.objects.get(id=item_id).quantity == 1

    delete_response = auth_client.delete(
        url,
        {"items": str(item_id)},
    )

    assert delete_response.status_code == 200
    assert not OrderItem.objects.filter(id=item_id).exists()