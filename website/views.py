from django.shortcuts import render
from .models import News, Product
from django.db.models import Count


def home(request):
    return render(request, "ПМК-71_главная_исправленная.html", {
        "news_items": News.objects.filter(is_published=True),
    })


def catalog(request):
    items = Product.objects.filter(is_published=True)
    return render(request, "ПМК-71_каталог_обновлённый.html", {
        "products": items,
        "product_count": items.count(),
        "categories": items.values("category").annotate(count=Count("pk")).order_by("category"),
    })


def news(request):
    items = News.objects.filter(is_published=True)
    featured = items.filter(is_featured=True).first()
    return render(request, "ПМК-71_страница_новостей.html", {
        "featured_news": featured,
        "news_items": items.exclude(pk=featured.pk) if featured else items,
    })


from django.http import JsonResponse
from django.db import transaction
from .notifications import notify_sales
from django.views.decorators.http import require_POST
from .forms import OrderRequestForm
from .models import OrderRequest


@require_POST
def submit_order(request):
    from .antispam import consume_limit, rate_response
    import re
    # Ignore forwarded headers: only the actual peer address is trusted.
    ip = request.META.get("REMOTE_ADDR", "unknown")
    for scope, maximum, seconds in (("ip-minute", 10, 60), ("ip-hour", 30, 3600)):
        retry = consume_limit(scope, ip, maximum, seconds)
        if retry:
            return rate_response(retry)
    if request.POST.get("website", "").strip():
        return JsonResponse({"errors": {"spam": [{"message": "Не удалось отправить форму. Обновите страницу и попробуйте снова."}]}}, status=400)
    form = OrderRequestForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    data = form.cleaned_data
    if OrderRequest.objects.filter(submission_id=data["submission_id"]).exists():
        return JsonResponse({"message": "Заявка принята. Отдел продаж свяжется с вами."})
    retry = consume_limit("phone-hour", re.sub(r"\D", "", data["phone"]), 5, 3600)
    if retry:
        return rate_response(retry)
    product = data["product"]
    order, created = OrderRequest.objects.get_or_create(
        submission_id=data["submission_id"],
        defaults={
            "product": product,
            "product_name": product.name if product else "Общий запрос",
            "customer_name": data["customer_name"],
            "phone": data["phone"],
            "comment": data["comment"],
        },
    )
    if created:
        transaction.on_commit(lambda: notify_sales(order.pk))
    return JsonResponse({"message": "Заявка принята. Отдел продаж свяжется с вами."}, status=201 if created else 200)
