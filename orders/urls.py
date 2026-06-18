from django.urls import path

from orders.views import (
    RegisterView,
    LoginView,
    ProductListView,
    BasketView,
    ContactView,
    PartnerImportView,
    ConfirmRegisterView,
    ShopListView,
    CategoryListView,
    OrderView,
    UserDetailsView,
    PartnerStateView,
    PartnerOrdersView,
    PasswordResetView,
    PasswordResetConfirmView
)

urlpatterns = [
    path("user/details", UserDetailsView.as_view(), name="user-details"),
    path("user/register", RegisterView.as_view(), name="user-register"),
    path("user/register/confirm", ConfirmRegisterView.as_view(),
         name="user-register-confirm"),
    path("user/login", LoginView.as_view(), name="user-login"),
    path("user/contact", ContactView.as_view(), name="user-contact"),
    path("user/password_reset", PasswordResetView.as_view(),
         name="user-password-reset"),
    path("user/password_reset/confirm", PasswordResetConfirmView.as_view(),
         name="user-password-reset-confirm"),
    path("products", ProductListView.as_view(), name="products"),
    path("basket", BasketView.as_view(), name="basket"),
    path("shops", ShopListView.as_view(), name="shops"),
    path("categories", CategoryListView.as_view(), name="categories"),
    path("order", OrderView.as_view(), name="order"),
    path('partner/update', PartnerImportView.as_view(), name='partner-update'),
    path("partner/orders", PartnerOrdersView.as_view(), name="partner-orders"),
    path("partner/state", PartnerStateView.as_view(), name="partner-state"),
]
