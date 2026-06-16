from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

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


@admin.register(User)
class CustomUserAdmin(UserAdmin):
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
    )

    search_fields = (
        'email',
        'username',
        'company_name',
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
                    'password1',
                    'password2',
                    'user_type',
                    'is_staff',
                    'is_active',
                ),
            },
        ),
    )

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'url',
        'user',
        'is_active',
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

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
    )

    search_fields = (
        'name',
    )

    filter_horizontal = (
        'shops',
    )

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'category',
    )

    list_filter = (
        'category',
    )

    search_fields = (
        'name',
    )

class ProductParameterInline(admin.TabularInline):
    model = ProductParameter
    extra = 1

@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'model',
        'product',
        'shop',
        'quantity',
        'price',
        'price_rrc',
    )

    list_filter = (
        'shop',
        'product__category',
    )

    search_fields = (
        'model',
        'product__name',
        'shop__name',
    )

    inlines = [
        ProductParameterInline,
    ]

@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
    )

    search_fields = (
        'name',
    )

@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
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
        'parameter__name',
        'value',
    )

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'dt',
        'status',
    )

    list_filter = (
        'status',
        'dt',
    )

    search_fields = (
        'user__email',
        'user__username',
    )

    inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'product_info',
        'get_shop',
        'quantity',
    )

    list_filter = (
        'product_info__shop',
    )

    search_fields = (
        'order__user__email',
        'order__user__username',
        'product_info__model',
    )

    @admin.display(description='Магазин')
    def get_shop(self, obj):
        return obj.product_info.shop

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'city',
        'street',
        'house',
        'phone',
    )

    search_fields = (
        'user__email',
        'user__username',
        'city',
        'street',
        'house',
        'phone',
    )