import pytest

from orders.models import Contact, Order, OrderItem


@pytest.mark.django_db
def test_model_string_representations(user, shop, category, product, product_info):
    contact = Contact.objects.create(
        user=user,
        phone="+79999999999",
        city="Moscow",
        street="Test Street",
        house="1",
    )

    order = Order.objects.create(
        user=user,
        contact=contact,
        status="new",
    )

    item = OrderItem.objects.create(
        order=order,
        product_info=product_info,
        quantity=2,
    )

    assert str(user) == user.email
    assert str(shop) == shop.name
    assert str(category) == category.name
    assert str(product) == product.name
    assert product_info.model in str(product_info)
    assert "Moscow" in str(contact)
    assert f"#{order.id}" in str(order)
    assert product_info.model in str(item)