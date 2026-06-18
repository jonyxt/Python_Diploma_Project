import pytest
from django.urls import reverse

from orders.models import Contact


@pytest.mark.django_db
def test_contact_crud(auth_client, user):
    url = reverse("user-contact")

    create_response = auth_client.post(
        url,
        {
            "city": "Almaty",
            "street": "Shashkin street",
            "house": "40",
            "phone": "+49564563242",
        },
    )

    assert create_response.status_code == 201
    contact_id = create_response.data["contact"]["id"]

    list_response = auth_client.get(url)

    assert list_response.status_code == 200
    assert list_response.data[0]["id"] == contact_id

    update_response = auth_client.put(
        url,
        {
            "id": contact_id,
            "phone": "+45465421654",
        },
    )

    assert update_response.status_code == 200
    assert Contact.objects.get(id=contact_id).phone == "+45465421654"

    delete_response = auth_client.delete(
        url,
        {"items": str(contact_id)},
    )

    assert delete_response.status_code == 200
    assert not Contact.objects.filter(id=contact_id, user=user).exists()