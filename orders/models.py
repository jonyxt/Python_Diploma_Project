from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)

class UserManager(BaseUserManager):
    """
    Менеджер для модели User.
    Реализует методы для создания обычных пользователей и суперпользователей.
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Создаёт и сохраняет пользователя с указанными данными.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """
        Создаёт обычного пользователя.
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Создаёт суперпользователя.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    """
    Пользователь сервиса.

    Может быть покупателем или поставщиком.
    """
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    email = models.EmailField(
        unique=True,
        verbose_name='Email'
    )

    company_name = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Название компании'
    )

    position = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Должность'
    )

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='buyer',
        verbose_name='Тип пользователя'
    )

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        help_text=_(
            '150 символов или меньше. Только буквы, цифры и @/./+/-/_.'
        ),
        validators=[username_validator],
        error_messages={
            'unique': _("Пользователь с таким username уже существует."),
        },
    )

    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Определяет, активен ли пользователь. '
            'Вместо удаления пользователя лучше снять этот флаг.'
        )
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('email',)

    def __str__(self):
        return self.email


class Shop(models.Model):
    """
    Магазин поставщика.
    """

    name = models.CharField(
        max_length=255,
        verbose_name='Название магазина'
    )

    url = models.URLField(
        blank=True,
        null=True,
        verbose_name='URL магазина'
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shop',
        verbose_name='Пользователь'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Принимает заказы'
    )

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'

    def __str__(self):
        return self.name


class Category(models.Model):
    """
    Категория товаров.
    """

    name = models.CharField(
        max_length=255,
        verbose_name='Название категории'
    )

    shops = models.ManyToManyField(
        Shop,
        related_name='categories',
        verbose_name='Магазины'
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Общий товар.

    Например: Молоко, Хлеб, Сыр.
    Конкретные цены и остатки хранятся в ProductInfo.
    """

    name = models.CharField(
        max_length=255,
        verbose_name='Название товара'
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Категория'
    )

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    """
    Информация о товаре в конкретном магазине.
    """
    external_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Внешний ID товара в магазине'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='info',
        verbose_name='Товар'
    )

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='products_info',
        verbose_name='Магазин'
    )

    model = models.CharField(
        max_length=255,
        verbose_name='Название товара в магазине'
    )

    quantity = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество на складе'
    )

    price = models.PositiveIntegerField(
        verbose_name='Цена'
    )

    price_rrc = models.PositiveIntegerField(
        verbose_name='Рекомендуемая розничная цена'
    )

    class Meta:
        verbose_name = 'Информация о товаре'
        verbose_name_plural = 'Информация о товарах'
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'shop', 'external_id'],
                name='unique_product_shop_external_id'
            )
        ]

    def __str__(self):
        return f"{self.model}: {self.shop.name}"


class Parameter(models.Model):
    """
    Параметр товара.

    Например: цвет, размер, вес.
    """

    name = models.CharField(
        max_length=255,
        verbose_name='Название параметра'
    )

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = 'Параметры'

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    """
    Значение параметра для конкретного товара в конкретном магазине.
    """

    product_info = models.ForeignKey(
        ProductInfo,
        on_delete=models.CASCADE,
        related_name='parameters',
        verbose_name='Информация о товаре'
    )

    parameter = models.ForeignKey(
        Parameter,
        on_delete=models.CASCADE,
        related_name='product_parameters',
        verbose_name='Параметр'
    )

    value = models.CharField(
        max_length=255,
        verbose_name='Значение параметра'
    )

    class Meta:
        verbose_name = 'Значение параметра товара'
        verbose_name_plural = 'Значения параметров товаров'
        constraints = [
            models.UniqueConstraint(
                fields=['product_info', 'parameter'],
                name='unique_product_info_parameter'
            )
        ]

    def __str__(self):
        return f"{self.parameter.name}: {self.value} ({self.product_info.model})"


class Contact(models.Model):
    """
    Контактные данные пользователя.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contacts',
        verbose_name='Пользователь'
    )

    phone = models.CharField(
        max_length=20,
        verbose_name='Телефон'
    )

    city = models.CharField(
        max_length=255,
        verbose_name='Город'
    )

    street = models.CharField(
        max_length=255,
        verbose_name='Улица'
    )

    house = models.CharField(
        max_length=255,
        verbose_name='Дом'
    )

    structure = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Корпус'
    )

    building = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Строение'
    )

    apartment = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Квартира'
    )

    class Meta:
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'

    def __str__(self):
        return f'{self.city} {self.street} {self.house}'

class Order(models.Model):
    """
    Заказ покупателя.
    """

    class Status(models.TextChoices):
        BASKET = 'basket', 'Корзина'
        NEW = 'new', 'Новый'
        CONFIRMED = 'confirmed', 'Подтверждён'
        ASSEMBLED = 'assembled', 'Собран'
        SENT = 'sent', 'Отправлен'
        COMPLETED = 'completed', 'Завершён'
        CANCELED = 'canceled', 'Отменён'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Пользователь'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата и время заказа'
    )

    contact = models.ForeignKey(
        Contact,
        verbose_name='Контакт',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.BASKET,
        verbose_name='Статус'
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.id} от {self.created_at.strftime('%Y-%m-%d %H:%M:%S')} ({self.get_status_display()})"


class OrderItem(models.Model):
    """
    Конкретный товар в заказе.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ'
    )

    product_info = models.ForeignKey(
        ProductInfo,
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name='Информация о товаре'
    )

    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='Количество'
    )

    class Meta:
        verbose_name = 'Товар в заказе'
        verbose_name_plural = 'Товары в заказах'
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product_info'],
                name='unique_order_product_info'
            )
        ]

    def __str__(self):
        return f"{self.product_info.model} x {self.quantity} (Заказ #{self.order.id})"