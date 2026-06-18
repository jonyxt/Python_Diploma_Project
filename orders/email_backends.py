from django.core.mail.backends.base import BaseEmailBackend


class ReadableConsoleEmailBackend(BaseEmailBackend):
    """
    Печатает email-сообщения в консоль в читаемом виде.

    Используется для локальной разработки вместо стандартного
    console backend, который может выводить MIME/base64.
    """

    def send_messages(self, email_messages):
        """
        Выводит письма в stdout и возвращает количество сообщений.
        """
        count = 0

        for message in email_messages:
            print("-" * 80)
            print(f"Subject: {message.subject}")
            print(f"From: {message.from_email}")
            print(f"To: {', '.join(message.to)}")
            print()
            print(message.body)
            print("-" * 80)

            count += 1

        return count