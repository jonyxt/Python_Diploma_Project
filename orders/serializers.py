from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from rest_framework import serializers

from .models import (
    User,
    Shop,
    ProductInfo,
    ProductParameter,
    Order,
    OrderItem,
    Contact,
    Category
)


class RegisterSerializer(serializers.ModelSerializer):
    """
    Создает нового неактивного пользователя.
    """

    password = serializers.CharField(write_only=True, min_length=8)
    company = serializers.CharField(
        source='company_name',
        required=False,
        allow_blank=True
    )

    class Meta:
        model = User
        fields = [
            'id',
            'last_name',
            'first_name',
            'email',
            'password',
            'company',
            'position',
        ]
        extra_kwargs = {
            'position': {
                'required': False,
                'allow_blank': True,
            }
        }

    def create(self, validated_data):
        """
        Создает пользователя с неактивным статусом до подтверждения email.
        """
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.username = validated_data['email']
        user.is_active = False
        user.set_password(password)
        user.save()

        return user


class RegisterConfirmSerializer(serializers.Serializer):
    """
    Проверяет email и токен подтверждения регистрации.
    """
    email = serializers.EmailField()
    token = serializers.CharField()

    def validate(self, attrs):
        email = attrs['email']
        token = attrs['token']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Пользователь с таким email не найден')

        if user.is_active:
            attrs['user'] = user
            return attrs

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError('Токен подтверждения недействителен или устарел')

        attrs['user'] = user
        return attrs


class LoginSerializer(serializers.Serializer):
    """
    Проверяет email и пароль пользователя.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if user:
                data['user'] = user
            else:
                raise serializers.ValidationError("Неверный email или пароль. "
                                                  "Возможно, email ещё не подтверждён")
        else:
            raise serializers.ValidationError("Необходимо указать email и password")

        return data


class PasswordResetSerializer(serializers.Serializer):
    """
    Проверяет email для запроса сброса пароля.
    """

    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Пользователь с таким email не найден')

        attrs['user'] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Проверяет токен и новый пароль для сброса пароля.
    """

    email = serializers.EmailField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        email = attrs['email']
        token = attrs['token']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Пользователь с таким email не найден')

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError('Токен недействителен или устарел')

        attrs['user'] = user
        return attrs


class UserDetailsSerializer(serializers.ModelSerializer):
    """
    Сериализует и обновляет профиль текущего пользователя.
    """

    company = serializers.CharField(
        source='company_name',
        required=False,
        allow_blank=True
    )
    password = serializers.CharField(
        write_only=True,
        required=False,
        min_length=8
    )

    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'password',
            'company',
            'position',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
            'email': {'required': False},
            'position': {'required': False, 'allow_blank': True},
        }

    def update(self, instance, validated_data):
        """
        Обновляет профиль и корректно хеширует новый пароль.
        """
        password = validated_data.pop('password', None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if password:
            instance.set_password(password)

        if instance.email:
            instance.username = instance.email

        instance.save()
        return instance


class ProductParameterSerializer(serializers.ModelSerializer):
    """
    Сериализует характеристику товара.
    """

    name = serializers.CharField(source='parameter.name')

    class Meta:
        model = ProductParameter
        fields = ['name', 'value']


class ShopSerializer(serializers.ModelSerializer):
    """
    Сериализует магазин поставщика.
    """

    class Meta:
        model = Shop
        fields = [
            'id',
            'name',
            'url',
            'is_active',
        ]


class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализует категорию товаров.
    """

    class Meta:
        model = Category
        fields = [
            'id',
            'name',
        ]


class ProductInfoSerializer(serializers.ModelSerializer):
    """
    Сериализует товарную позицию конкретного магазина.
    """

    name = serializers.CharField(source='product.name')
    supplier = serializers.CharField(source='shop.name')
    description = serializers.CharField(source='model')
    characteristics = ProductParameterSerializer(source='parameters', many=True, read_only=True)

    class Meta:
        model = ProductInfo
        fields = [
            'id',
            'name',
            'description',
            'supplier',
            'characteristics',
            'price',
            'quantity'
        ]


class BasketItemSerializer(serializers.ModelSerializer):
    """
    Сериализует позицию корзины.
    """

    product_name = serializers.CharField(source='product_info.product.name', read_only=True)
    shop = serializers.CharField(source='product_info.shop.name', read_only=True)
    price = serializers.DecimalField(
        source='product_info.price',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    total_sum = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            "product_info",
            "product_name",
            "shop",
            "price",
            "quantity",
            "total_sum",
        ]

    def get_total_sum(self, obj):
        """
        Возвращает сумму позиции корзины.
        """
        return obj.product_info.price * obj.quantity


class BasketAddSerializer(serializers.Serializer):
    """
    Проверяет данные для добавления товара в корзину.
    """

    product_info = serializers.PrimaryKeyRelatedField(
        queryset=ProductInfo.objects.select_related('shop', 'product').all()
    )
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        product_info = attrs['product_info']
        quantity = attrs['quantity']

        if not product_info.shop.is_active:
            raise serializers.ValidationError(
                'Магазин не принимает заказы'
            )

        if product_info.quantity <= 0:
            raise serializers.ValidationError(
                'Товары отсутствуют на складе'
            )

        if quantity > product_info.quantity:
            raise serializers.ValidationError("Запрошенное количество больше доступного остатка")

        return attrs


class ContactSerializer(serializers.ModelSerializer):
    """
    Сериализует контактные данные пользователя.
    """

    class Meta:
        model = Contact
        fields = [
            "id",
            "phone",
            'last_name',
            'first_name',
            'middle_name',
            "city",
            "street",
            "house",
            "structure",
            "building",
            "apartment",
        ]
        read_only_fields = ["id"]

    def validate_phone(self, value):
        """
        Нормализует и проверяет номер телефона.
        """
        cleaned_value = value.strip()
        if len(cleaned_value) < 7:
            raise serializers.ValidationError(
                'Телефон слишком короткий'
            )
        return cleaned_value

    def validate(self, attrs):
        """
        Проверяет обязательные поля при создании контакта.
        """
        required_fields = ['phone', 'city', 'street', 'house']

        for field in required_fields:
            if self.partial and field not in attrs:
                continue

            value = attrs.get(field)

            if not value or not str(value).strip():
                raise serializers.ValidationError(
                    f"Поле '{field}' не может быть пустым"
                )

        return attrs


class OrderCreateSerializer(serializers.Serializer):
    """
    Проверяет данные для оформления корзины в заказ.
    """

    id = serializers.IntegerField()
    contact = serializers.IntegerField()

    def validate(self, attrs):
        user = self.context['request'].user
        basket_id = attrs['id']
        contact_id = attrs['contact']

        try:
            basket = Order.objects.get(
                id=basket_id,
                user=user,
                status='basket'
            )
        except Order.DoesNotExist:
            raise serializers.ValidationError("Корзина не найдена")

        if not basket.items.exists():
            raise serializers.ValidationError("Корзина пуста")

        try:
            contact = Contact.objects.get(
                id=contact_id,
                user=user
            )
        except Contact.DoesNotExist:
            raise serializers.ValidationError("Контакт не найден")

        attrs['basket'] = basket
        attrs['contact_obj'] = contact

        return attrs


class OrderStatusSerializer(serializers.Serializer):
    """
    Проверяет новый статус заказа.
    """

    status = serializers.ChoiceField(
        choices=[
            Order.Status.CONFIRMED,
            Order.Status.ASSEMBLED,
            Order.Status.SENT,
            Order.Status.COMPLETED,
            Order.Status.CANCELED,
        ]
    )


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Сериализует позицию оформленного заказа.
    """

    product_name = serializers.CharField(source='product_info.product.name')
    shop = serializers.CharField(source='product_info.shop.name')
    price = serializers.DecimalField(
        source='product_info.price',
        max_digits=12,
        decimal_places=2
    )
    total_sum = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            "product_name",
            "shop",
            "price",
            "quantity",
            "total_sum",
        ]

    def get_total_sum(self, obj):
        return obj.product_info.price * obj.quantity


class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализует оформленный заказ.
    """

    number = serializers.IntegerField(source='id')
    date = serializers.DateTimeField(source='created_at', format='%Y-%m-%d %H:%M')
    sum = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'number',
            'date',
            'sum',
            'status',
            'contact',
            'items'
        ]

    def get_sum(self, obj):
        return sum(
            item.product_info.price * item.quantity
            for item in obj.items.all()
        )