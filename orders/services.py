import yaml

from django.db import transaction
from pathlib import Path

from orders.models import (
    Shop,
    Category,
    Product,
    ProductInfo,
    Parameter,
    ProductParameter
)

def read_yaml_file(file_obj):
    """
    Читает YAML-файл и возвращает его содержимое строкой.

    Поддерживает путь к файлу, pathlib.Path и Django UploadedFile.
    """
    try:
        if isinstance(file_obj, (str, Path)):
            return Path(file_obj).read_text(encoding="utf-8")

        content = file_obj.read()

        if isinstance(content, bytes):
            return content.decode("utf-8")

        return content

    except Exception as exc:
        raise ValueError(f"Не удалось прочитать YAML-файл: {exc}")


@transaction.atomic
def import_products_from_yaml_text(yaml_text, user=None):
    """
    Импортирует товары поставщика из YAML-текста.

    Создает или обновляет магазин, категории, товары, товарные
    позиции и характеристики.
    """

    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        raise ValueError('Ошибка чтения YAML-файла')

    if not data:
        raise ValueError('Файл пустой или имеет неверную структуру')

    shop_name = data.get('shop')
    categories_data = data.get('categories', [])
    goods_data = data.get('goods', [])

    if not categories_data:
        raise ValueError('В файле отсутствует список категорий')

    if not goods_data:
        raise ValueError('В файле отсутствует список товаров')

    if not shop_name:
        raise ValueError('В файле отсутствует название магазина')

    if user is None:
        raise ValueError('Для импорта необходимо указать поставщика')

    shop, _ = Shop.objects.get_or_create(
        user=user,
        defaults={
            'name': shop_name,
            'is_active': True
        }
    )

    if shop.name != shop_name:
        shop.name = shop_name
        shop.save(update_fields=['name'])

    category_map = {}

    for category_data in categories_data:
        external_category_id = category_data.get('id')
        category_name = category_data.get('name')

        if external_category_id is None or not category_name:
            continue

        category, _ = Category.objects.get_or_create(name=category_name)
        category.shops.add(shop)

        category_map[external_category_id] = category

    imported_count = 0

    for item in goods_data:
        external_id = item.get('id')
        category_id = item.get('category')
        product_name = item.get('name')
        model = item.get('model', '')
        price = item.get('price', 0)
        price_rrc = item.get('price_rrc', 0)
        quantity = item.get('quantity', 0)
        parameters = item.get('parameters') or {}

        if external_id is None or category_id is None or not product_name:
            continue

        category = category_map.get(category_id)

        if category is None:
            continue

        product, _ = Product.objects.get_or_create(
            name=product_name,
            category=category
        )

        product_info, _ = ProductInfo.objects.update_or_create(
            shop=shop,
            external_id=external_id,
            defaults={
                'product': product,
                'model': model,
                'quantity': quantity,
                'price': price,
                'price_rrc': price_rrc,
            }
        )

        ProductParameter.objects.filter(product_info=product_info).delete()

        for parameters_name, parameters_value in parameters.items():
            parameter, _ = Parameter.objects.get_or_create(name=parameters_name)
            ProductParameter.objects.create(
                product_info=product_info,
                parameter=parameter,
                value=str(parameters_value)
            )

        imported_count += 1

    return {
        'shop': shop.name,
        'imported_count': imported_count
    }

def import_products_from_yaml(file_obj, user=None):
    """
    Читает YAML-файл и импортирует товары поставщика.
    """
    yaml_text = read_yaml_file(file_obj)
    return import_products_from_yaml_text(yaml_text=yaml_text, user=user)