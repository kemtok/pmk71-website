from datetime import timedelta
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac
from .models import SubmissionLimit


def consume_limit(scope, identity, maximum, seconds):
    now = timezone.now()
    key = scope + ":" + salted_hmac("order-rate-limit", identity).hexdigest()
    # Shared database counters survive server restarts and are shared by workers.
    SubmissionLimit.objects.filter(expires_at__lt=now - timedelta(days=1)).delete()
    row, _ = SubmissionLimit.objects.get_or_create(
        key=key, defaults={"expires_at": now + timedelta(seconds=seconds)})
    SubmissionLimit.objects.filter(pk=row.pk, expires_at__lte=now).update(
        count=0, expires_at=now + timedelta(seconds=seconds))
    allowed = SubmissionLimit.objects.filter(pk=row.pk, count__lt=maximum).update(count=F("count") + 1)
    if allowed:
        return 0
    row.refresh_from_db()
    return max(1, int((row.expires_at - now).total_seconds()) + 1)


def rate_response(seconds):
    from django.http import JsonResponse
    response = JsonResponse({"errors": {"rate": [{"message":
        f"Слишком много отправок. Попробуйте через {seconds} сек."}]}}, status=429)
    response["Retry-After"] = str(seconds)
    return response
