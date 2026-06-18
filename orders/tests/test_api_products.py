import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_products_list_available_for_anonymous_user(api_client, product_info):
    response = api_client.get(
        reverse("products"),
        {
            "shop_id": product_info.shop_id,
            "category_id": product_info.product.category_id,
        },
    )

    assert response.status_code == 200
    assert response.data[0]["name"] == "iPhone 15"


@pytest.mark.django_db
def test_shops_and_categories_available_for_anonymous_user(
    api_client,
    shop,
    category,
):
    shops_response = api_client.get(reverse("shops"))
    categories_response = api_client.get(reverse("categories"))

    assert shops_response.status_code == 200
    assert shops_response.data[0]["id"] == shop.id

    assert categories_response.status_code == 200
    assert categories_response.data[0]["id"] == category.id


@pytest.mark.django_db
def test_product_detail_available_for_anonymous_user(api_client, product_info):
    response = api_client.get(
        reverse(
            "product-detail",
            kwargs={"product_info_id": product_info.id}
        )
    )

    assert response.status_code == 200
    assert response.data["id"] == product_info.id
    assert response.data["name"] == "iPhone 15"
    assert response.data["supplier"] == product_info.shop.name