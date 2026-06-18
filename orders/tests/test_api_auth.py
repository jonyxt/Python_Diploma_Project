import pytest
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from rest_framework.authtoken.models import Token

from orders.models import User


@pytest.mark.django_db
def test_user_registration(api_client, mocker):
    mocked_send_email = mocker.patch("orders.views.send_email.delay")
    url = reverse("user-register")

    response = api_client.post(
        url,
        {
            "email": "newuser@example.com",
            "password": "testpass123",
            "first_name": "New",
            "last_name": "User",
            "company": "Test Company",
            "position": "Buyer",
        },
    )

    assert response.status_code == 201

    user = User.objects.get(email="newuser@example.com")
    assert user.is_active is False
    assert user.company_name == "Test Company"
    assert user.position == "Buyer"
    mocked_send_email.assert_called_once()


@pytest.mark.django_db
def test_user_register_confirm(api_client):
    user = User.objects.create_user(
        email="inactive@example.com",
        password="testpass123",
    )
    token = default_token_generator.make_token(user)

    response = api_client.post(
        reverse("user-register-confirm"),
        {
            "email": user.email,
            "token": token,
        },
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_active is True


@pytest.mark.django_db
def test_user_login(api_client, user):
    response = api_client.post(
        reverse("user-login"),
        {
            "email": user.email,
            "password": "testpass123",
        },
    )

    assert response.status_code == 200
    assert response.data["token"] == Token.objects.get(user=user).key


@pytest.mark.django_db
def test_user_details_get_and_update(auth_client, user):
    get_response = auth_client.get(reverse("user-details"))

    assert get_response.status_code == 200
    assert get_response.data["email"] == user.email

    update_response = auth_client.post(
        reverse("user-details"),
        {
            "first_name": "Updated",
            "last_name": "Client",
            "company": "Updated Company",
            "position": "Lead Buyer",
        },
    )

    assert update_response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Updated"
    assert user.company_name == "Updated Company"
    assert user.position == "Lead Buyer"


@pytest.mark.django_db
def test_password_reset_flow(api_client, user, mocker):
    mocked_send_email = mocker.patch("orders.views.send_email.delay")

    response = api_client.post(
        reverse("user-password-reset"),
        {"email": user.email},
    )

    assert response.status_code == 200
    mocked_send_email.assert_called_once()

    token = default_token_generator.make_token(user)
    confirm_response = api_client.post(
        reverse("user-password-reset-confirm"),
        {
            "email": user.email,
            "password": "newpass123",
            "token": token,
        },
    )

    assert confirm_response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("newpass123")