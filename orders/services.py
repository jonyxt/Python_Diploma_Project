import yaml
from django.db import transaction

from orders.models import (
    Shop,
    Category,
    Product,
    ProductInfo,
    Parameter,
    ProductParameter
)

@transaction.atomic
def import_products_from_yaml(file_obj, user=None):
    """
    Импорт товаров из YAML файла.
    """

    try:
        content = file_obj.read().decode('utf-8')
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        raise ValueError('Ошибка чтения YAML-файла')
    except UnicodeDecodeError:
        raise ValueError('Файл должен быть в кодировке UTF-8')

    if not data:
        raise ValueError('Файл пустой или имеет неверную структуру')

    shop_name = data.get('shop')
    categories_data = data.get('categories', [])
    if not categories_data:
        raise ValueError('В файле отсутствует список категорий')
    goods_data = data.get('goods', [])
    if not goods_data:
        raise ValueError('В файле отсутствует список товаров')

    if not shop_name:
        raise ValueError('В файле отсутствует название магазина')

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

    if user and shop.user is None:
        shop.user = user
        shop.save(update_fields=['user'])

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