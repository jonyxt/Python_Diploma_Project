# backend/tests/conftest.py

import pytest
from rest_framework.test import APIClient

from orders.models import User, Shop, Category, Product, ProductInfo


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="client@example.com",
        password="testpass123",
        first_name="Client",
        last_name="User",
        company="Test Company",
        position="Buyer",
        type="buyer",
    )


@pytest.fixture
def supplier(db):
    return User.objects.create_user(
        email="supplier@example.com",
        password="testpass123",
        first_name="Supplier",
        last_name="User",
        company="Supplier Company",
        position="Manager",
        type="shop",
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def supplier_client(api_client, supplier):
    api_client.force_authenticate(user=supplier)
    return api_client


@pytest.fixture
def shop(db, supplier):
    return Shop.objects.create(
        name="Test Shop",
        user=supplier,
        state=True,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(
        name="Smartphones",
    )


@pytest.fixture
def product(db, category):
    product = Product.objects.create(
        name="iPhone 15",
        category=category,
    )
    return product


@pytest.fixture
def product_info(db, shop, product):
    return ProductInfo.objects.create(
        product=product,
        shop=shop,
        external_id=1001,
        model="A3090",
        price=100000,
        price_rrc=120000,
        quantity=10,
    )