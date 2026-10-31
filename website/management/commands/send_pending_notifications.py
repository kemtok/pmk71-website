from django.core.management.base import BaseCommand
from website.models import OrderRequest
from website.notifications import notify_sales


class Command(BaseCommand):
    help = "Retry unsent sales notifications. Run one instance at a time."

    def handle(self, *args, **options):
        sent = 0
        for pk in OrderRequest.objects.filter(notification_sent_at__isnull=True).values_list("pk", flat=True):
            sent += int(notify_sales(pk))
        self.stdout.write(f"Sent: {sent}")
