import json
import re
from urllib.error import URLError
from urllib.request import urlopen

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator

from orders.tasks import send_email, do_import
from .models import ProductInfo, Order, OrderItem, Contact, Shop, Category
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    ProductInfoSerializer,
    BasketItemSerializer,
    BasketAddSerializer,
    ContactSerializer,
    OrderSerializer,
    ShopSerializer,
    CategorySerializer,
    OrderCreateSerializer,
    UserDetailsSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    RegisterConfirmSerializer
)


class PartnerImportView(APIView):
    """
    Обновляет прайс поставщика по ссылке на YAML-файл.
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Загружает YAML по URL и запускает фоновый импорт товаров.
        """
        if request.user.user_type != 'shop':
            return Response(
                {
                    'error': (
                        'Только поставщик может обновлять прайс'
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        url = request.data.get('url')

        if not url:
            return Response(
                {'error': 'Не передан url'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not url.endswith(('.yaml', '.yml')):
            return Response(
                {
                    'error': (
                        'Неверный формат URL. '
                        'Ожидается .yaml или .yml'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with urlopen(url, timeout=10) as response:
                yaml_text = response.read().decode('utf-8')
        except (URLError, TimeoutError, UnicodeDecodeError) as error:
            return Response(
                {
                    'error': (
                        f'Не удалось загрузить YAML-файл: {error}'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        task = do_import.delay(
            yaml_text=yaml_text,
            user_id=request.user.id
        )

        return Response(
            {
                'status': 'accepted',
                'message': 'Импорт товаров запущен',
                'task_id': task.id
            },
            status=status.HTTP_202_ACCEPTED
        )


class PartnerStateView(APIView):
    """
    Показывает и меняет статус приема заказов поставщиком.
    """

    permission_classes = [IsAuthenticated]

    def get_shop(self, user):
        """
        Возвращает магазин текущего пользователя-поставщика.
        """
        if user.user_type != 'shop':
            return None

        try:
            return user.shop
        except Shop.DoesNotExist:
            return None

    def get(self, request):
        """
        Возвращает текущий статус приема заказов.
        """
        shop = self.get_shop(request.user)

        if shop is None:
            return Response(
                {'error': 'Магазин поставщика не найден'},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response(
            {
                'state': 'on' if shop.is_active else 'off',
                'is_active': shop.is_active,
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        """
        Переключает статус приема заказов: on или off.
        """
        shop = self.get_shop(request.user)

        if shop is None:
            return Response(
                {'error': 'Магазин поставщика не найден'},
                status=status.HTTP_403_FORBIDDEN
            )

        state = request.data.get('state')

        if state not in ('on', 'off'):
            return Response(
                {'error': 'state должен быть on или off'},
                status=status.HTTP_400_BAD_REQUEST
            )

        shop.is_active = state == 'on'
        shop.save(update_fields=['is_active'])

        return Response(
            {
                'message': 'Статус поставщика обновлен',
                'state': state,
            },
            status=status.HTTP_200_OK
        )


class PartnerOrdersView(APIView):
    """
    Возвращает заказы с товарами текущего поставщика.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Показывает все оформленные заказы, где есть товары магазина поставщика.
        """
        if request.user.user_type != 'shop':
            return Response(
                {'error': 'Только поставщик может просматривать заказы магазина'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            shop = request.user.shop
        except Shop.DoesNotExist:
            return Response(
                {'error': 'Магазин поставщика не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        orders = Order.objects.filter(
            items__product_info__shop=shop
        ).exclude(
            status='basket'
        ).select_related(
            'user',
            'contact'
        ).prefetch_related(
            'items',
            'items__product_info',
            'items__product_info__product',
            'items__product_info__shop'
        ).distinct().order_by('-created_at')

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RegisterView(APIView):
    """
    Показывает все оформленные заказы, где есть товары магазина поставщика.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """
        Создает неактивного пользователя и отправляет email с токеном.
        """
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token = default_token_generator.make_token(user)
            send_email.delay(
                subject='Подтверждение регистрации',
                message=(
                    f'Здравствуйте!\n\n'
                    f'Для подтверждения регистрации используйте токен:\n'
                    f'{token}\n\n'
                    f'Email: {user.email}\n\n'
                    f'Если вы не регистрировались, просто проигнорируйте это письмо.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email]
            )
            return Response(
                {
                    'message': 'Пользователь зарегистрирован. '
                               'Проверьте email для подтверждения регистрации.',
                    'user_id': user.id
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConfirmRegisterView(APIView):
    """
    Подтверждает регистрацию по email и токену.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """
        Активирует пользователя, если токен подтверждения корректен.
        """
        serializer = RegisterConfirmSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']

        if user.is_active:
            return Response(
                {'message': 'Пользователь уже подтвержден'},
                status=status.HTTP_200_OK
            )

        user.is_active = True
        user.save(update_fields=['is_active'])

        return Response(
            {'message': 'Email успешно подтвержден. Теперь можно войти'},
            status=status.HTTP_200_OK
        )


class LoginView(APIView):
    """
    Выдает auth token по email и паролю.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """
        Авторизует пользователя и возвращает DRF token.
        """
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    'message': 'Успешный вход',
                    'user_id': user.id,
                    'token': token.key
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    """
    Отправляет токен для сброса пароля.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """
        Генерирует токен сброса пароля и отправляет его на email.
        """
        serializer = PasswordResetSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        token = default_token_generator.make_token(user)

        send_email.delay(
            subject='Сброс пароля',
            message=(
                f'Для сброса пароля используйте токен:\n'
                f'{token}\n'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email]
        )

        return Response(
            {'message': 'Токен для сброса пароля отправлен на email'},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    """
    Меняет пароль по email и токену сброса.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """
        Устанавливает новый пароль, если токен сброса корректен.
        """
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        password = serializer.validated_data['password']

        user.set_password(password)
        user.save(update_fields=['password'])

        return Response(
            {'message': 'Пароль успешно изменен'},
            status=status.HTTP_200_OK
        )


class UserDetailsView(APIView):
    """
    Показывает и обновляет данные текущего пользователя.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Возвращает профиль текущего пользователя.
        """
        serializer = UserDetailsSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Частично обновляет профиль текущего пользователя.
        """
        serializer = UserDetailsSerializer(
            request.user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'Данные пользователя обновлены',
                    'user': serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductListView(APIView):
    """
    Возвращает список доступных товаров.

    Поддерживает фильтрацию по магазину и категории:
    - shop_id
    - category_id
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """
        Показывает товары активных магазинов с положительным остатком.
        """
        products = ProductInfo.objects.select_related(
            'product',
            'shop'
        ).prefetch_related(
            'parameters__parameter'
        ).filter(
            shop__is_active=True,
            quantity__gt=0
        )

        search = request.query_params.get('search')
        shop = request.query_params.get('shop')
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if search:
            products = products.filter(
                Q(product__name__icontains=search)
                | Q(shop__name__icontains=search)
            )

        if shop:
            products = products.filter(shop_id=shop)

        if shop_id:
            products = products.filter(shop_id=shop_id)

        if category_id:
            products = products.filter(product__category_id=category_id)

        serializer = ProductInfoSerializer(products, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class ShopListView(APIView):
    """
    Возвращает список активных магазинов.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        shops = Shop.objects.filter(is_active=True).order_by('name')
        serializer = ShopSerializer(shops, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoryListView(APIView):
    """
    Возвращает список категорий товаров.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """
        Показывает все категории.
        """
        categories = Category.objects.all().order_by('name')
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BasketView(APIView):
    """
    Управляет корзиной текущего пользователя.
    """

    permission_classes = [IsAuthenticated]

    def get_basket(self, user):
        """
        Возвращает существующую корзину или создает новую.
        """
        basket, _ = Order.objects.get_or_create(
            user=user,
            status='basket',
        )
        return basket

    def parse_items(self, request):
        """
        Разбирает JSON-список товаров из поля items.

        Поддерживает примеры из Postman с лишними запятыми перед
        закрывающими скобками.
        """
        items = request.data.get('items')

        if items is None:
            return None

        if isinstance(items, str):
            try:
                return json.loads(items)
            except json.JSONDecodeError:
                cleaned_items = re.sub(r',\s*([}\]])', r'\1', items)

                try:
                    return json.loads(cleaned_items)
                except json.JSONDecodeError:
                    return None

        return items

    def parse_item_ids(self, request):
        """
        Разбирает строку id товаров из поля items.
        """
        items = request.data.get('items')

        if not items:
            return []

        if isinstance(items, str):
            return [
                int(item_id)
                for item_id in items.split(',')
                if item_id.strip().isdigit()
            ]

        return items

    def get(self, request):
        """
        Возвращает содержимое корзины.
        """
        basket = self.get_basket(request.user)

        items = basket.items.select_related(
            'product_info',
            'product_info__product',
            'product_info__shop'
        )

        serializer = BasketItemSerializer(items, many=True)

        basket_sum = sum(
            item.product_info.price * item.quantity
            for item in items
        )

        return Response(
            {
                'basket_id': basket.id,
                'items': serializer.data,
                'sum': basket_sum
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        """
        Добавляет товары в корзину.
        """
        basket = self.get_basket(request.user)
        items = self.parse_items(request)

        if not isinstance(items, list):
            return Response(
                {'error': 'items должен быть списком товаров'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_items = []

        for item_data in items:
            serializer = BasketAddSerializer(data=item_data)

            if not serializer.is_valid():
                return Response(serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST)

            product_info = serializer.validated_data['product_info']
            quantity = serializer.validated_data['quantity']

            item, created = OrderItem.objects.get_or_create(
                order=basket,
                product_info=product_info,
                defaults={'quantity': quantity}
            )

            if not created:
                new_quantity = item.quantity + quantity

                if new_quantity > product_info.quantity:
                    return Response(
                        {
                            'error': 'Итоговое количество больше доступного остатка'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                item.quantity = new_quantity
                item.save(update_fields=['quantity'])

            created_items.append(item.id)

        return Response(
            {
                'message': 'Товары добавлены в корзину',
                'basket_id': basket.id,
                'items': created_items,
            },
            status=status.HTTP_201_CREATED
        )

    def put(self, request):
        """
        Обновляет количество товаров в корзине.
        """
        basket = self.get_basket(request.user)
        items = self.parse_items(request)

        if not isinstance(items, list):
            return Response(
                {'error': 'items должен быть списком товаров'},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated_items = []

        for item_data in items:
            item_id = item_data.get('id')
            quantity = item_data.get('quantity')

            if not item_id or quantity is None:
                return Response(
                    {'error': 'Для каждого товара нужны id и quantity'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                return Response(
                    {'error': 'quantity должен быть числом'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if quantity < 1:
                return Response(
                    {'error': 'quantity должен быть больше 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                item = OrderItem.objects.select_related('product_info').get(
                    id=item_id,
                    order=basket
                )
            except OrderItem.DoesNotExist:
                return Response(
                    {'error': f'Товар корзины {item_id} не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if quantity > item.product_info.quantity:
                return Response(
                    {
                        'error': 'Запрошенное количество больше доступного остатка'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            item.quantity = quantity
            item.save(update_fields=['quantity'])
            updated_items.append(item.id)

        return Response(
            {
                'message': 'Корзина обновлена',
                'items': updated_items,
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request):
        """
        Удаляет товары из корзины.
        """
        item_ids = self.parse_item_ids(request)

        if not item_ids:
            return Response(
                {'error': 'Не переданы корректные id товаров'},
                status=status.HTTP_400_BAD_REQUEST
            )

        basket = self.get_basket(request.user)

        delete_count, _ = OrderItem.objects.filter(
            order=basket,
            id__in=item_ids,
        ).delete()

        return Response(
            {
                'message': 'Товары удалены из корзины',
                'deleted': delete_count,
            },
            status=status.HTTP_200_OK
        )


class ContactView(APIView):
    """
    Управляет контактами текущего пользователя.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Возвращает список контактов пользователя.
        """
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Создает новый контакт пользователя.
        """
        serializer = ContactSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(
                {
                    'message': 'Контакт добавлен',
                    'contact': serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """
        Частично обновляет контакт пользователя.
        """
        contact_id = request.data.get('id')

        if not contact_id:
            return Response(
                {'error': 'Не передан id контакта'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            contact = Contact.objects.get(
                id=contact_id,
                user=request.user
            )
        except Contact.DoesNotExist:
            return Response(
                {'error': 'Контакт не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ContactSerializer(
            contact,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(
                {
                    'message': 'Контакт обновлен',
                    'contact': serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """
        Удаляет контакты пользователя по списку id.
        """
        items = request.data.get('items')

        if not items:
            return Response(
                {'error': 'Не переданы items'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if isinstance(items, str):
            contact_ids = [
                int(item_id)
                for item_id in items.split(',')
                if item_id.strip().isdigit()
            ]
        else:
            contact_ids = items

        if not contact_ids:
            return Response(
                {'error': 'Не переданы корректные id контактов'},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted_count, _ = Contact.objects.filter(
            id__in=contact_ids,
            user=request.user
        ).delete()

        return Response(
            {
                'message': 'Контакты удалены',
                'deleted': deleted_count
            },
            status=status.HTTP_200_OK
        )


class OrderView(APIView):
    """
    Показывает заказы пользователя и оформляет корзину в заказ.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Возвращает оформленные заказы текущего пользователя.
        """
        orders = Order.objects.filter(
            user=request.user
        ).exclude(
            status='basket'
        ).select_related(
            'contact'
        ).prefetch_related(
            'items',
            'items__product_info',
            'items__product_info__product',
            'items__product_info__shop'
        ).order_by('-created_at')

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Оформляет корзину в заказ.
        """
        serializer = OrderCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        basket = serializer.validated_data['basket']
        contact = serializer.validated_data['contact_obj']

        basket.contact = contact
        basket.status = 'new'
        basket.save(update_fields=['contact', 'status'])

        order_items = basket.items.select_related(
            'product_info',
            'product_info__product',
            'product_info__shop'
        )

        order_sum = sum(
            item.product_info.price * item.quantity
            for item in order_items
        )

        return Response(
            {
                'message': 'Заказ подтвержден',
                'order_id': basket.id,
                'status': basket.status,
                'sum': order_sum,
            },
            status=status.HTTP_200_OK
        )
