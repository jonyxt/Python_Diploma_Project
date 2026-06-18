from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from orders.services import read_yaml_file
from orders.tasks import do_import

from .models import (
    User,
    Shop,
    Category,
    Product,
    ProductInfo,
    Parameter,
    ProductParameter,
    Order,
    OrderItem,
    Contact,
)


admin.site.site_header = 'Администрирование склада'
admin.site.site_title = 'Склад'
admin.site.index_title = 'Панель управления закупками'


class AdminImportForm(forms.Form):
    """
    Форма загрузки YAML-прайса поставщика через админку.
    """

    supplier = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='shop'),
        label='Поставщик'
    )
    file = forms.FileField(
        label='YAML-файл'
    )


class LowStockFilter(admin.SimpleListFilter):
    """
    Фильтр товарных позиций по остатку на складе.
    """

    title = 'Остаток на складе'
    parameter_name = 'stock'

    def lookups(self, request, model_admin):
        """
        Возвращает варианты фильтра по количеству товара.
        """
        return (
            ('empty', 'Нет в наличии'),
            ('low', 'Мало: 1-5'),
            ('normal', 'Достаточно: больше 5')
        )

    def queryset(self, request, queryset):
        """
        Фильтрует товарные позиции по выбранному уровню остатка.
        """
        if self.value() == 'empty':
            return queryset.filter(quantity=0)

        if self.value() == 'low':
            return queryset.filter(quantity__gt=0, quantity__lte=5)

        if self.value() == 'normal':
            return queryset.filter(quantity__gt=5)

        return queryset


class ContactInline(admin.TabularInline):
    """
    Встроенное отображение контактов пользователя.
    """

    model = Contact
    extra = 0
    fields = (
        'last_name',
        'first_name',
        'middle_name',
        'city',
        'street',
        'house',
        'phone',
    )
    show_change_link = True


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Настройки отображения пользовательской модели в админке.
    """

    model = User
    list_display = (
        'id',
        'email',
        'username',
        'user_type',
        'company_name',
        'is_staff',
        'is_active',
    )

    list_filter = (
        'user_type',
        'is_staff',
        'is_active',
        'is_superuser'
    )

    search_fields = (
        'email',
        'username',
        'company_name',
        'first_name',
        'last_name'
    )

    ordering = (
        'email',
    )

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'email',
                    'password',
                )
            }
        ),
        (
            'Личная информация',
            {
                'fields': (
                    'username',
                    'first_name',
                    'last_name',
                    'company_name',
                    'position',
                    'user_type',
                )
            }
        ),
        (
            'Права доступа',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            }
        ),
        (
            'Важные даты',
            {
                'fields': (
                    'last_login',
                    'date_joined',
                )
            }
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': (
                    'wide',
                ),
                'fields': (
                    'email',
                    'username',
                    'password1',
                    'password2',
                    'user_type',
                    'is_staff',
                    'is_active',
                ),
            },
        ),
    )

    inlines = [
        ContactInline
    ]


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """
    Управление магазинами поставщиков.
    """

    list_display = (
        'id',
        'name',
        'url',
        'user',
        'is_active',
        'products_count'
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'name',
        'url',
        'user__email',
        'user__username',
    )

    autocomplete_fields = (
        'user',
    )

    actions = (
        'activate_shops',
        'deactivate_shops'
    )

    @admin.display(description='Товарных позиций')
    def products_count(self, obj):
        """
        Возвращает количество товарных позиций магазина.
        """
        return obj.products_info.count()

    @admin.action(description='Включить приём заказов')
    def activate_shops(self, request, queryset):
        """
        Включает прием заказов для выбранных магазинов.
        """
        queryset.update(is_active=True)

    @admin.action(description='Отключить приём заказов')
    def deactivate_shops(self, request, queryset):
        """
        Отключает прием заказов для выбранных магазинов.
        """
        queryset.update(is_active=False)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Управление категориями товаров.
    """

    list_display = (
        'id',
        'name',
        'products_count'
    )

    search_fields = (
        'name',
    )

    filter_horizontal = (
        'shops',
    )

    @admin.display(description='Товаров')
    def products_count(self, obj):
        """
        Возвращает количество товаров в категории.
        """
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Управление общими карточками товаров.
    """

    list_display = (
        'id',
        'name',
        'category',
        'offers_count'
    )

    list_filter = (
        'category',
    )

    search_fields = (
        'name',
        'category__name'
    )

    autocomplete_fields = (
        'category',
    )

    @admin.display(description='Предложений поставщиков')
    def offers_count(self, obj):
        """
        Возвращает количество предложений поставщиков по товару.
        """
        return obj.info.count()


class ProductParameterInline(admin.TabularInline):
    """
    Встроенное редактирование характеристик товарной позиции.
    """

    model = ProductParameter
    extra = 0
    autocomplete_fields = (
        'parameter',
    )
    fields = (
        'parameter',
        'value'
    )


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """
    Управление товарными позициями магазинов.
    """

    list_display = (
        'id',
        'model',
        'product',
        'get_category',
        'shop',
        'quantity',
        'stock_status',
        'price',
        'price_rrc',
    )

    list_editable = (
        'quantity',
        'price',
        'price_rrc',
    )

    list_filter = (
        LowStockFilter,
        'shop',
        'product__category',
        'shop__is_active'
    )

    search_fields = (
        'model',
        'product__name',
        'shop__name',
        'external_id'
    )

    autocomplete_fields = (
        'product',
        'shop',
    )

    list_select_related = (
        'product',
        'product__category',
        'shop'
    )

    inlines = [
        ProductParameterInline,
    ]

    fieldsets = (
        (
            'Основная информация',
            {
                'fields': (
                    'external_id',
                    'product',
                    'shop',
                    'model'
                )
            }
        ),
        (
            'Склад и цены',
            {
                'fields': (
                    'quantity',
                    'price',
                    'price_rrc'
                )
            }
        )
    )

    change_list_template = 'admin/orders/productinfo/change_list.html'

    def get_urls(self):
        """
        Добавляет custom URL для импорта YAML через админку.
        """
        urls = super().get_urls()

        custom_urls = [
            path(
                'import-yaml/',
                self.admin_site.admin_view(self.import_yaml_view),
                name='orders_productinfo_import_yaml'
            ),
        ]

        return custom_urls + urls

    def import_yaml_view(self, request):
        """
        Обрабатывает загрузку YAML-файла поставщика через админку.
        """
        if request.method == 'POST':
            form = AdminImportForm(request.POST, request.FILES)

            if form.is_valid():
                supplier = form.cleaned_data['supplier']
                uploaded_file = form.cleaned_data['file']

                if not uploaded_file.name.endswith(('.yaml', '.yml')):
                    messages.error(
                        request,
                        'Неверный формат файла. Ожидается .yaml или .yml'
                    )
                    return HttpResponseRedirect(request.path)

                try:
                    yaml_text = read_yaml_file(uploaded_file)
                except ValueError as error:
                    messages.error(request, str(error))
                    return HttpResponseRedirect(request.path)

                task = do_import.delay(
                    yaml_text=yaml_text,
                    user_id=supplier.id
                )

                messages.success(
                    request,
                    f'Импорт запущен в Celery. Task ID: {task.id}'
                )

                return HttpResponseRedirect(
                    reverse('admin:orders_productinfo_changelist')
                )
        else:
            form = AdminImportForm()

        context = {
            **self.admin_site.each_context(request),
            'title': 'Импорт товаров из YAML',
            'form': form,
            'opts': self.model._meta,
        }

        return render(
            request,
            'admin/orders/productinfo/import_yaml.html',
            context
        )

    @admin.display(description='Категория')
    def get_category(self, obj):
        """
        Возвращает категорию товара.
        """
        return obj.product.category

    @admin.display(description='Статус склада')
    def stock_status(self, obj):
        """
        Возвращает HTML-индикатор остатка на складе.
        """
        if obj.quantity == 0:
            return format_html('<b style="color: red;">Нет в наличии</b>')

        if obj.quantity <= 5:
            return format_html('<b style="color: orange;">Мало</b>')

        return format_html('<span style="color: green;">В наличии</span>')


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """
    Управление справочником характеристик товаров.
    """

    list_display = (
        'id',
        'name',
    )

    search_fields = (
        'name',
    )


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """
    Управление значениями характеристик товарных позиций.
    """

    list_display = (
        'id',
        'product_info',
        'parameter',
        'value',
    )

    list_filter = (
        'parameter',
    )

    search_fields = (
        'product_info__model',
        'product_info__product__name',
        'parameter__name',
        'value',
    )

    autocomplete_fields = (
        'product_info',
        'parameter',
    )

    list_select_related = (
        'product_info',
        'parameter'
    )


class OrderItemInline(admin.TabularInline):
    """
    Встроенное отображение товаров внутри заказа.
    """

    model = OrderItem
    extra = 0
    autocomplete_fields = (
        'product_info',
    )
    fields = (
        'product_info',
        'get_shop',
        'quantity',
        'item_sum'
    )
    readonly_fields = (
        'get_shop',
        'item_sum'
    )

    @admin.display(description='Магазин')
    def get_shop(self, obj):
        """
        Возвращает магазин товарной позиции.
        """
        if obj.product_info_id:
            return obj.product_info.shop
        return '-'

    @admin.display(description='Сумма позиции')
    def item_sum(self, obj):
        """
        Возвращает стоимость позиции заказа.
        """
        if obj.product_info_id:
            return obj.product_info.price * obj.quantity
        return 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Управление заказами пользователей.
    """

    list_display = (
        'id',
        'user',
        'created_at',
        'status',
        'contact',
        'items_count',
        'order_sum'
    )

    list_filter = (
        'status',
        'created_at',
    )

    search_fields = (
        'id',
        'user__email',
        'user__username',
        'contact__phone',
        'contact__city',
        'contact__street',
    )

    readonly_fields = (
        'created_at',
        'items_count',
        'order_sum',
    )

    autocomplete_fields = (
        'user',
        'contact',
    )

    inlines = [
        OrderItemInline
    ]

    actions = (
        'mark_confirmed',
        'mark_assembled',
        'mark_sent',
        'mark_completed',
        'mark_canceled',
    )

    fieldsets = (
        (
            'Заказ',
            {
                'fields':
                    (
                        'user',
                        'created_at',
                        'status',
                        'contact'
                    )
            }
        ),
        (
            'Итоги',
            {
                'fields': (
                    'items_count',
                    'order_sum'
                )
            }
        )
    )

    @admin.display(description='Позиций')
    def items_count(self, obj):
        """
        Возвращает количество позиций в заказе.
        """
        return obj.items.count()

    @admin.display(description='Сумма заказа')
    def order_sum(self, obj):
        """
        Возвращает итоговую сумму заказа.
        """
        return sum(
            item.product_info.price * item.quantity
            for item in obj.items.select_related('product_info')
        )

    @admin.action(description='Перевести в статус: Подтверждён')
    def mark_confirmed(self, request, queryset):
        """
        Переводит выбранные заказы в статус confirmed.
        """
        queryset.update(status=Order.Status.CONFIRMED)

    @admin.action(description='Перевести в статус: Собран')
    def mark_assembled(self, request, queryset):
        """
        Переводит выбранные заказы в статус assembled.
        """
        queryset.update(status=Order.Status.ASSEMBLED)

    @admin.action(description='Перевести в статус: Отправлен')
    def mark_sent(self, request, queryset):
        """
        Переводит выбранные заказы в статус sent.
        """
        queryset.update(status=Order.Status.SENT)

    @admin.action(description='Перевести в статус: Завершён')
    def mark_completed(self, request, queryset):
        """
        Переводит выбранные заказы в статус completed.
        """
        queryset.update(status=Order.Status.COMPLETED)

    @admin.action(description='Перевести в статус: Отменён')
    def mark_canceled(self, request, queryset):
        """
        Переводит выбранные заказы в статус canceled.
        """
        queryset.update(status=Order.Status.CANCELED)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Управление отдельными позициями заказов.
    """

    list_display = (
        'id',
        'order',
        'product_info',
        'get_shop',
        'quantity',
        'item_sum'
    )

    list_filter = (
        'product_info__shop',
        'product_info__product__category'
    )

    search_fields = (
        'order__user__email',
        'order__user__username',
        'product_info__model',
        'product_info__product__name',
        'product_info__shop__name',
    )

    autocomplete_fields = (
        'order',
        'product_info',
    )

    list_select_related = (
        'order',
        'product_info',
        'product_info__shop',
        'product_info__product',
    )

    @admin.display(description='Магазин')
    def get_shop(self, obj):
        """
        Возвращает магазин товарной позиции.
        """
        return obj.product_info.shop

    @admin.display(description='Сумма позиций')
    def item_sum(self, obj):
        """
        Возвращает стоимость позиции заказа.
        """
        return obj.product_info.price * obj.quantity


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Управление контактными данными пользователей.
    """

    list_display = (
        'id',
        'user',
        'last_name',
        'first_name',
        'middle_name',
        'city',
        'street',
        'house',
        'phone',
    )

    list_filter = (
        'city',
    )

    search_fields = (
        'user__email',
        'user__username',
        'last_name',
        'first_name',
        'middle_name',
        'city',
        'street',
        'house',
        'phone',
    )

    autocomplete_fields = (
        'user',
    )