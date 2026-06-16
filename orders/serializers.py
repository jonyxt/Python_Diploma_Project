from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import (
User,
Shop,
Product,
ProductInfo,
Parameter,
ProductParameter,
Order,
OrderItem,
Contact
)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'id',
            'last_name',
            'first_name',
            'email',
            'password'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.username = validated_data['email']
        user.set_password(password)
        user.save()

        return user

class LoginSerializer(serializers.Serializer):
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
                raise serializers.ValidationError("Unable to log in with provided credentials.")
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")

        return data

class ProductParameterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='parameter.name')

    class Meta:
        model = ProductParameter
        fields = ['name', 'value']

class ProductInfoSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='product.name')
    supplier = serializers.CharField(source='shop.name')
    characteristics = ProductParameterSerializer(source='parameters', many=True, read_only=True)

    class Meta:
        model = ProductInfo
        fields = [
            'id',
            'name',
            'supplier',
            'characteristics',
            'price',
            'quantity'
        ]

class BasketItemSerializer(serializers.ModelSerializer):
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
        return obj.product_info.price * obj.quantity

class BasketAddSerializer(serializers.Serializer):
    product_info = serializers.PrimaryKeyRelatedField(
        queryset=ProductInfo.objects.all()
    )
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        product_info = attrs['product_info']
        quantity = attrs['quantity']

        if quantity > product_info.quantity:
            raise serializers.ValidationError("Запрошенное количество больше доступного остатка")

        return attrs

class BasketDeleteSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "id",
            "phone",
            "city",
            "street",
            "house",
            "structure",
            "building",
            "apartment",
        ]
        read_only_fields = ["id"]

class OrderConfirmSerializer(serializers.Serializer):
    basket_id = serializers.IntegerField()
    contact_id = serializers.IntegerField()

    def validate(self, attrs):
        user = self.context['request'].user
        basket_id = attrs['basket_id']
        contact_id = attrs['contact_id']

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
        attrs['contact'] = contact

        return attrs

class OrderItemSerializer(serializers.ModelSerializer):
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
    number = serializers.IntegerField(source='id')
    date = serializers.DateTimeField(source='created_at', format='%Y-%m-%d %H:%M')
    sum = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'number',
            'date',
            'sum',
            'status',
            'items'
        ]

    def get_sum(self, obj):
        return sum(
            item.product_info.price * item.quantity
            for item in obj.items.all()
        )