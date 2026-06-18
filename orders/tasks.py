from celery import shared_task
from django.core.mail import send_mail as django_send_mail

from orders.models import User
from orders.services import import_products_from_yaml_text


@shared_task(name='orders.send_email')
def send_email(subject, message, from_email, recipient_list):
    """
    Celery-задача для отправки email через настроенный Django email backend.
    """
    return django_send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        fail_silently=False
    )

@shared_task(name='orders.do_import')
def do_import(yaml_text, user_id):
    """
    Celery-задача для импорта товаров из YAML.
    """
    user = User.objects.get(id=user_id)
    return import_products_from_yaml_text(yaml_text=yaml_text, user=user)