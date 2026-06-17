# backend/tests/test_import.py

import pytest
from pathlib import Path

from orders.models import Shop, ProductInfo, Category, Product
from orders.services import import_products_from_yaml


@pytest.mark.django_db
def test_import_products_from_yaml_creates_products(tmp_path, supplier):
    yaml_content = """
shop: Test Import Shop
categories:
  - id: 1
    name: Смартфоны
goods:
  - id: 1001
    category: 1
    name: iPhone 15
    model: A3090
    price: 100000
    price_rrc: 120000
    quantity: 5
    parameters:
      Диагональ: 6.1
      Цвет: Черный
"""

    file_path = tmp_path / "shop.yaml"
    file_path.write_text(yaml_content, encoding="utf-8")

    result = import_products_from_yaml(file_path, user=supplier)

    assert Shop.objects.filter(name="Test Import Shop").exists()
    assert Category.objects.filter(name="Смартфоны").exists()
    assert Product.objects.filter(name="iPhone 15").exists()
    assert ProductInfo.objects.filter(external_id=1001, quantity=5).exists()