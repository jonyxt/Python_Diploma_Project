from django.urls import path
from orders.views import PartnerImportView

urlpatterns = [
    path('partner/import/', PartnerImportView.as_view(), name='partner-import'),
]