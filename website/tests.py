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



class SalesTests(TestCase):
    def test_staff_permissions(self):
        from django.contrib.auth.models import Group
        user = get_user_model().objects.create_user("saleslimited", password="test-pass", is_staff=True)
        user.groups.add(Group.objects.get(name="Отдел продаж"))
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("admin:website_orderrequest_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:website_product_changelist")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:auth_user_changelist")).status_code, 403)
        self.assertFalse(user.has_perm("website.delete_orderrequest"))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                       EMAIL_HOST="smtp.test", DEFAULT_FROM_EMAIL="site@example.com",
                       SALES_NOTIFICATION_EMAILS=["sales@example.com"])
    def test_notification_retry_and_deduplication(self):
        from django.core import mail
        from unittest.mock import patch
        from website.notifications import notify_sales
        from .models import OrderRequest
        import uuid
        order = OrderRequest.objects.create(customer_name="Клиент", phone="+375291234567",
                                            product_name="Бетон", submission_id=uuid.uuid4())
        with patch("website.notifications.send_mail", side_effect=RuntimeError("SMTP")):
            self.assertFalse(notify_sales(order.pk))
        self.assertTrue(OrderRequest.objects.filter(pk=order.pk).exists())
        self.assertTrue(notify_sales(order.pk))
        self.assertTrue(notify_sales(order.pk))
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn(order.phone, mail.outbox[0].body)
        order.refresh_from_db()
        self.assertIsNotNone(order.notification_sent_at)
        self.assertEqual(order.notification_error, "")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                       EMAIL_HOST="smtp.test", DEFAULT_FROM_EMAIL="site@example.com",
                       SALES_NOTIFICATION_EMAILS=["sales@example.com"])
    def test_submission_sends_only_after_commit(self):
        from django.core import mail
        import uuid
        data = {"customer_name": "Клиент", "phone": "+375291234567", "submission_id": str(uuid.uuid4())}
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(reverse("website:submit_order"), data).status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("website:submit_order"), data)
        self.assertEqual(len(mail.outbox), 1)



class FeedbackTests(TestCase):
    def test_both_forms_submit_with_csrf_and_show_errors(self):
        import re
        import uuid
        from .models import OrderRequest
        for name in ("home", "news"):
            client = Client(enforce_csrf_checks=True)
            response = client.get(reverse("website:" + name))
            self.assertEqual(response.status_code, 200)
            html = response.content.decode()
            self.assertIn('name="customer_name"', html)
            self.assertIn('name="phone"', html)
            self.assertIn('js/contact-form.js', html)
            csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)[1]
            data = {"csrfmiddlewaretoken": csrf, "customer_name": "Клиент",
                    "phone": "wrong", "comment": "Обратная связь", "submission_id": str(uuid.uuid4())}
            self.assertEqual(client.post(reverse("website:submit_order"), data).status_code, 400)
            data["phone"] = "+375291234567"
            self.assertEqual(client.post(reverse("website:submit_order"), data).status_code, 201)
            self.assertEqual(client.post(reverse("website:submit_order"), data).status_code, 200)
        self.assertEqual(OrderRequest.objects.count(), 2)
        self.assertTrue(all(x.product_name == "Общий запрос" for x in OrderRequest.objects.all()))



class AntiSpamTests(TestCase):
    def payload(self, phone="+375291234567"):
        import uuid
        return {"customer_name": "Клиент", "phone": phone, "submission_id": str(uuid.uuid4())}

    def test_honeypot_does_not_save_or_notify(self):
        from .models import OrderRequest
        from unittest.mock import patch
        data = self.payload()
        data["website"] = "spam"
        with patch("website.views.notify_sales") as notify:
            response = self.client.post(reverse("website:submit_order"), data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(OrderRequest.objects.exists())
        notify.assert_not_called()

    def test_invalid_attempts_are_limited_and_forwarded_ip_is_ignored(self):
        url = reverse("website:submit_order")
        for i in range(10):
            self.assertEqual(self.client.post(url, {}, HTTP_X_FORWARDED_FOR=f"192.0.2.{i}").status_code, 400)
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response["Retry-After"]), 0)

    def test_phone_limit_across_different_addresses_and_retries(self):
        from .models import OrderRequest
        url = reverse("website:submit_order")
        first = self.payload()
        self.assertEqual(self.client.post(url, first).status_code, 201)
        for i in range(4):
            self.assertEqual(self.client.post(url, self.payload(), REMOTE_ADDR=f"192.0.2.{i}").status_code, 201)
        self.assertEqual(self.client.post(url, first).status_code, 200)
        data = self.payload("+375 (29) 123-45-67")
        self.assertEqual(self.client.post(url, data, REMOTE_ADDR="192.0.2.100").status_code, 429)
        self.assertEqual(OrderRequest.objects.count(), 5)

    def test_limit_expires_and_does_not_store_raw_identity(self):
        from datetime import timedelta
        from unittest.mock import patch
        from django.utils import timezone
        from website.antispam import consume_limit
        from .models import SubmissionLimit
        now = timezone.now()
        with patch("website.antispam.timezone.now", return_value=now):
            self.assertEqual(consume_limit("test", "192.0.2.1", 1, 60), 0)
            self.assertGreater(consume_limit("test", "192.0.2.1", 1, 60), 0)
        self.assertNotIn("192.0.2.1", SubmissionLimit.objects.get().key)
        with patch("website.antispam.timezone.now", return_value=now + timedelta(seconds=61)):
            self.assertEqual(consume_limit("test", "192.0.2.1", 1, 60), 0)



class BackupTests(TestCase):
    def test_backup_restore_checksums_and_no_overwrite(self):
        import sqlite3
        import zipfile
        from pathlib import Path
        from website.backups import create_backup, restore_archive
        with TemporaryDirectory(dir=".") as temp:
            root = Path(temp).resolve()
            db = root / "source.sqlite3"
            with sqlite3.connect(db) as connection:
                for table in ("website_news", "website_product"):
                    connection.execute(f"CREATE TABLE {table} (image TEXT)")
                for table in ("website_orderrequest", "auth_user"):
                    connection.execute(f"CREATE TABLE {table} (id INTEGER)")
                connection.execute("INSERT INTO website_news VALUES ('photo.jpg')")
                connection.execute("INSERT INTO website_orderrequest VALUES (1)")
            connection.close()
            media = root / "media"
            media.mkdir()
            (media / "photo.jpg").write_bytes(b"photo")
            databases = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(db)}}
            from types import SimpleNamespace
            from unittest.mock import patch
            with patch("website.backups.settings", SimpleNamespace(DATABASES=databases, MEDIA_ROOT=media)):
                archive, counts = create_backup(root / "backups")
            self.assertEqual(counts["website_orderrequest"], 1)
            destination = root / "restored"
            self.assertEqual(restore_archive(archive, destination), counts)
            self.assertEqual((destination / "media/photo.jpg").read_bytes(), b"photo")
            with self.assertRaises(ValueError):
                restore_archive(archive, destination)
            broken = root / "broken.zip"
            with zipfile.ZipFile(archive) as source, zipfile.ZipFile(broken, "w") as target:
                for name in source.namelist():
                    target.writestr(name, b"changed" if name == "media/photo.jpg" else source.read(name))
            with self.assertRaises(ValueError):
                restore_archive(broken, root / "broken-restore")
            unsafe = root / "unsafe.zip"
            with zipfile.ZipFile(unsafe, "w") as z:
                z.writestr("manifest.json", "{}")
                z.writestr("db.sqlite3", b"")
                z.writestr("../escaped.txt", b"x")
            with self.assertRaises(ValueError):
                restore_archive(unsafe, root / "unsafe-restore")
            self.assertFalse((root / "escaped.txt").exists())
