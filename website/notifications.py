from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from .models import OrderRequest


def notify_sales(order_id):
    order = OrderRequest.objects.get(pk=order_id)
    if order.notification_sent_at:
        return True
    if not settings.SALES_NOTIFICATION_EMAILS or not settings.EMAIL_HOST:
        OrderRequest.objects.filter(pk=order_id).update(notification_error="Не настроены получатели или SMTP.")
        return False
    link = settings.SITE_URL + reverse("admin:website_orderrequest_change", args=[order.pk])
    try:
        count = send_mail(
            f"ПМК-71: новая заявка №{order.pk}",
            f"Поступила новая заявка на продукцию: {order.product_name}.\n"
            f"Откройте заявку в админке: {link}\nДля просмотра контактов требуется вход.",
            settings.DEFAULT_FROM_EMAIL, settings.SALES_NOTIFICATION_EMAILS,
        )
        if count != 1:
            raise RuntimeError("No email sent")
    except Exception:
        OrderRequest.objects.filter(pk=order_id).update(
            notification_error="Не удалось отправить письмо. Проверьте настройки SMTP и повторите отправку.")
        return False
    OrderRequest.objects.filter(pk=order_id).update(notification_sent_at=timezone.now(), notification_error="")
    return True
