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
from django.views.decorators.http import require_POST
from .forms import OrderRequestForm
from .models import OrderRequest


@require_POST
def submit_order(request):
    form = OrderRequestForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    data = form.cleaned_data
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
    return JsonResponse({"message": "Заявка принята. Отдел продаж свяжется с вами."}, status=201 if created else 200)
