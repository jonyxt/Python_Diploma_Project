from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.db.models import Q

from orders.services import import_products_from_yaml
from .models import ProductInfo, Order, OrderItem, Contact
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    ProductInfoSerializer,
    BasketItemSerializer,
    BasketAddSerializer,
    BasketDeleteSerializer,
    ContactSerializer,
    OrderConfirmSerializer,
    OrderSerializer,
)


class PartnerImportView(APIView):
    """
    View для импорта товаров из YAML файла.
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.user_type != 'shop':
            return Response(
                {'error': 'Только поставщик может импортировать товары'},
                status=status.HTTP_403_FORBIDDEN
            )

        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            return Response({'error': 'Файл не предоставлен'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not uploaded_file.name.endswith(('.yaml', '.yml')):
            return Response({'error': 'Неверный формат файла. Ожидается .yaml или .yml'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            result = import_products_from_yaml(file_obj=uploaded_file, user=request.user)
        except ValueError as error:
            return Response(
                {'error': str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                'status': 'success',
                'message': 'Товары успешно импортированы',
                'shop': result['shop'],
                'imported_count': result['imported_count']
            },
            status=status.HTTP_201_CREATED
        )

class RegisterView(APIView):
    """
    Регистрация пользователя.

    POST:
    {
        "last_name": "Иванов",
        "first_name": "Иван",
        "email": "user@mail.com",
        "password": "password123"
    }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    'message': 'Пользователь успешно зарегистрирован',
                    'user_id': user.id,
                    'token': token.key
                },
                status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    """"
      Вход пользователя.

      POST:
      {
          "email": "user@mail.com",
          "password": "password123"
      }
    """

    permission_classes = [AllowAny]

    def post(self, request):
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
                status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProductListView(APIView):
    """
    Список товаров с фильтрацией и поиском.

    GET /api/products/
    GET /api/products/?search=iphone
    GET /api/products/?shop=1
    """

    permission_classes = [AllowAny]

    def get(self, request):
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

        if search:
            products = products.filter(
                Q(product__name__icontains=search)
                | Q(shop__name__icontains=search)
            )

        if shop:
            products = products.filter(shop_id=shop)

        serializer = ProductInfoSerializer(products, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

class BasketView(APIView):
    """
    Корзина:
    GET    — просмотр корзины
    POST   — добавление товара
    DELETE — удаление товаров из корзины
    """

    permission_classes = [IsAuthenticated]

    def get_basket(self, user):
        basket, _ = Order.objects.get_or_create(
            user=user,
            status='basket',
        )
        return basket

    def get(self, request):
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
        serializer = BasketAddSerializer(data=request.data)

        if serializer.is_valid():
            basket = self.get_basket(request.user)
            product_info = serializer.validated_data['product_info']
            quantity = serializer.validated_data['quantity']

            item, created = OrderItem.objects.get_or_create(
                order=basket,
                product_info=product_info,
                defaults={
                    'quantity': quantity
                }
            )

            if not created:
                new_quantity = item.quantity + quantity
                if new_quantity > product_info.quantity:
                    return Response(
                        {
                            'error': 'Итоговое количество больше доступного остатка'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                item.quantity = new_quantity
                item.save()

            return Response(
                {
                    'message': 'Товар добавлен в корзину'
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        serializer = BasketDeleteSerializer(data=request.data)

        if serializer.is_valid():
            basket = self.get_basket(request.user)
            delete_count, _ = OrderItem.objects.filter(
                order=basket,
                id__in=serializer.validated_data['items'],
            ).delete()

            return Response(
                {
                    'message': 'Товары удалены из корзины',
                    'deleted': delete_count,
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ContactView(APIView):
    """
    Контакты:
    GET    — список контактов
    POST   — добавление контакта
    DELETE — удаление контакта
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
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

    def delete(self, request):
        contact_id = request.data.get('id')
        if not contact_id:
            return Response(
                {
                    'error': 'Не передан id контакта'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        deleted_count, _ = Contact.objects.filter(
            id=contact_id,
            user=request.user
        ).delete()

        if deleted_count == 0:
            return Response(
                {
                    'error': 'Контакт не найден'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                'message': 'Контакт удален'
            },
            status=status.HTTP_200_OK
        )

class OrderConfirmView(APIView):
    """
    Подтверждение заказа.

    POST:
    {
        "basket_id": 1,
        "contact_id": 2
    }
    """

    permission_classes = [IsAuthenticated]

    def  post(self, request):
        serializer = OrderConfirmSerializer(
            data=request.data,
            context={
                'request': request
            }
        )

        if serializer.is_valid():
            basket = serializer.validated_data['basket']
            contact = serializer.validated_data['contact']
            basket.contact = contact
            basket.status = 'new'
            basket.save()

            return Response(
                {
                    'message': 'Заказ подтвержден',
                    'order_id': basket.id,
                    'status': basket.status
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrderListView(APIView):
    """
    История заказов пользователя.

    GET /api/orders/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).exclude(
            status='basket'
        ).prefetch_related(
            'items',
            'items__product_info',
            'items__product_info__product',
            'items__product_info__shop'
        ).order_by('-created_at')

        serializer = OrderSerializer(orders, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
