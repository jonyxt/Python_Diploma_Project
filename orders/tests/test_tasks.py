import pytest

from orders.tasks import do_import, send_email


@pytest.mark.django_db
def test_do_import_task_calls_import_service(mocker, supplier):
    mocked_import = mocker.patch("orders.tasks.import_products_from_yaml_text")

    do_import("shop: Test Shop", user_id=supplier.id)

    mocked_import.assert_called_once_with(
        yaml_text="shop: Test Shop",
        user=supplier,
    )


@pytest.mark.django_db
def test_send_email_task_calls_django_send_mail(mocker):
    mocked_send_mail = mocker.patch("orders.tasks.django_send_mail")

    send_email(
        subject="Test subject",
        message="Test message",
        from_email="admin@example.com",
        recipient_list=["client@example.com"],
    )

    mocked_send_mail.assert_called_once_with(
        subject="Test subject",
        message="Test message",
        from_email="admin@example.com",
        recipient_list=["client@example.com"],
        fail_silently=False,
    )