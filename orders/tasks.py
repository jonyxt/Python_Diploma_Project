from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail as django_send_mail

from orders.services import import_products_from_yaml_text


@shared_task(name='orders.send_email')
def send_email(subject, message, from_email, recipient_list):
    """
    Celery-задача для отправки email.
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
    User = get_user_model()
    user = User.objects.get(id=user_id)
    result = import_products_from_yaml_text(
        yaml_text=yaml_text,
        user=user
    )
    return result