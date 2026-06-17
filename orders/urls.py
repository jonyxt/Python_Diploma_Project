from django.urls import path
from orders.views import (
    RegisterView,
    LoginView,
    ProductListView,
    BasketView,
    ContactView,
    OrderConfirmView,
    OrderListView,
    PartnerImportView,
    ConfirmRegisterView
)

urlpatterns = [
    path('partner/import/', PartnerImportView.as_view(), name='partner-import'),
    path("user/register/", RegisterView.as_view(), name="user-register"),
    path("user/login/", LoginView.as_view(), name="user-login"),
    path("products/", ProductListView.as_view(), name="products"),
    path("basket/", BasketView.as_view(), name="basket"),
    path("contacts/", ContactView.as_view(), name="contacts"),
    path("order/confirm/", OrderConfirmView.as_view(), name="order-confirm"),
    path("orders/", OrderListView.as_view(), name="orders"),
    path('user/register/confirm/<uidb64>/<token>/',
         ConfirmRegisterView.as_view(),
         name='user-register-confirm')
]