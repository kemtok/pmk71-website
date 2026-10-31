from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import News


class NewsTests(TestCase):
    def test_imported_news_and_featured_story(self):
        self.assertEqual(News.objects.count(), 6)
        self.assertIn("53353-", News.objects.get(is_featured=True).source_url)
        for name in ("home", "news"):
            response = self.client.get(reverse("website:" + name))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "MuseiKB.jpg")

    def test_publication_changes_both_pages(self):
        item = News.objects.create(
            title="Новая публикация", summary="Описание",
            source_url="https://example.org/news",
        )
        for name in ("home", "news"):
            self.assertContains(self.client.get(reverse("website:" + name)), item.title)
        item.is_published = False
        item.save()
        for name in ("home", "news"):
            self.assertNotContains(self.client.get(reverse("website:" + name)), item.title)

    def test_featured_story_can_be_changed(self):
        item = News.objects.exclude(is_featured=True).first()
        item.is_featured = True
        item.save()
        self.assertEqual(News.objects.filter(is_featured=True).count(), 1)
        response = self.client.get(reverse("website:news"))
        self.assertEqual(response.context["featured_news"], item)
        self.assertNotIn(item, response.context["news_items"])

    def test_admin_can_upload_and_delete_news(self):
        user = get_user_model().objects.create_superuser("editor", password="test-only-password")
        self.client.force_login(user)
        with TemporaryDirectory(dir=".") as media_dir, override_settings(MEDIA_ROOT=media_dir):
            response = self.client.post(reverse("admin:website_news_add"), {
                "title": "Из админки", "summary": "Описание", "body": "",
                "source_url": "https://example.org/article", "category": "company",
                "is_published": "on", "position": 0,
                "image": SimpleUploadedFile("photo.gif", b"GIF89a", content_type="image/gif"),
                "_save": "Save",
            })
            self.assertEqual(response.status_code, 302)
            item = News.objects.get(title="Из админки")
            self.assertTrue(item.image.storage.exists(item.image.name))
            self.assertContains(self.client.get(reverse("website:news")), item.image.url)
            response = self.client.post(reverse("admin:website_news_delete", args=[item.pk]), {"post": "yes"})
            self.assertEqual(response.status_code, 302)
            self.assertFalse(News.objects.filter(pk=item.pk).exists())



class ProductTests(TestCase):
    def test_catalog_import_and_visibility(self):
        from .models import Product
        self.assertEqual(Product.objects.count(), 9)
        response = self.client.get(reverse("website:catalog"))
        self.assertEqual(response.status_code, 200)
        for item in Product.objects.all():
            self.assertContains(response, item.name)
            self.assertTrue(item.image.storage.exists(item.image.name))
        item = Product.objects.create(name="Тестовый товар", category="Новая категория", price=0)
        self.assertContains(self.client.get(reverse("website:catalog")), "Тестовый товар")
        self.assertContains(self.client.get(reverse("website:catalog")), "Новая категория")
        item.is_published = False
        item.save()
        self.assertNotContains(self.client.get(reverse("website:catalog")), "Тестовый товар")

    def test_admin_product_upload(self):
        from .models import Product
        user = get_user_model().objects.create_superuser("producteditor", password="test-only-password")
        self.client.force_login(user)
        with TemporaryDirectory(dir=".") as media_dir, override_settings(MEDIA_ROOT=media_dir):
            response = self.client.post(reverse("admin:website_product_add"), {
                "name": "Из админки", "category": "Бетон", "description": "Описание",
                "unit": "м³", "price": "12.50", "is_published": "on", "position": 0,
                "image": SimpleUploadedFile("photo.gif", b"GIF89a", content_type="image/gif"),
                "_save": "Save",
            })
            self.assertEqual(response.status_code, 302)
            item = Product.objects.get(name="Из админки")
            self.assertTrue(item.image.storage.exists(item.image.name))
            self.assertContains(self.client.get(reverse("website:catalog")), item.image.url)



class OrderTests(TestCase):
    def payload(self):
        import uuid
        from .models import Product
        return {"customer_name": "Покупатель", "phone": "+375 (29) 123-45-67",
                "comment": "Нужно 10 штук", "product": Product.objects.first().pk,
                "submission_id": str(uuid.uuid4())}

    def test_order_is_saved_once_and_keeps_product_name(self):
        from .models import OrderRequest, Product
        data = self.payload()
        url = reverse("website:submit_order")
        self.assertEqual(self.client.post(url, data).status_code, 201)
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(OrderRequest.objects.count(), 1)
        order = OrderRequest.objects.get()
        self.assertEqual(order.phone, data["phone"])
        self.assertEqual(order.status, "new")
        name = order.product_name
        Product.objects.filter(pk=data["product"]).delete()
        order.refresh_from_db()
        self.assertIsNone(order.product)
        self.assertEqual(order.product_name, name)

    def test_validation_csrf_and_hidden_products(self):
        from .models import Product, OrderRequest
        url = reverse("website:submit_order")
        data = self.payload()
        data["phone"] = "abc"
        self.assertEqual(self.client.post(url, data).status_code, 400)
        data = self.payload()
        Product.objects.filter(pk=data["product"]).update(is_published=False)
        self.assertEqual(self.client.post(url, data).status_code, 400)
        self.assertFalse(OrderRequest.objects.exists())
        self.assertEqual(Client(enforce_csrf_checks=True).post(url, self.payload()).status_code, 403)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_admin_can_process_orders(self):
        from .models import OrderRequest
        self.client.post(reverse("website:submit_order"), self.payload())
        order = OrderRequest.objects.get()
        user = get_user_model().objects.create_superuser("sales", password="test-only-password")
        self.client.force_login(user)
        response = self.client.post(reverse("admin:website_orderrequest_change", args=[order.pk]),
                                    {"status": "processing", "sales_notes": "Связались с клиентом", "_save": "Save"})
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, "processing")
        self.assertEqual(order.sales_notes, "Связались с клиентом")
