from django.contrib import admin
from .models import News


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_featured", "is_published", "published_at", "position")
    list_filter = ("category", "is_featured", "is_published")
    search_fields = ("title", "summary", "body")
    readonly_fields = ("created_at",)
    fields = ("title", "summary", "body", "image", "source_url", "category",
              "published_at", "is_featured", "is_published", "position", "created_at")


from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "unit", "is_published", "position")
    list_filter = ("category", "is_published")
    search_fields = ("name", "description")
    fields = ("name", "category", "description", "image", "unit", "price", "is_published", "position")


from .models import OrderRequest


@admin.register(OrderRequest)
class OrderRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "customer_name", "phone", "product_name", "status", "notification_sent_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer_name", "phone", "product_name", "comment", "sales_notes")
    readonly_fields = ("product", "product_name", "customer_name", "phone", "comment", "created_at", "notification_sent_at", "notification_error")
    fields = ("status", "sales_notes", "created_at", "product", "product_name", "customer_name", "phone", "comment", "notification_sent_at", "notification_error")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False
