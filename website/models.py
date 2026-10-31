from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models, transaction


class News(models.Model):
    class Category(models.TextChoices):
        OBJECTS = "objects", "Наши объекты"
        TEAM = "team", "Люди и профессия"
        COMPANY = "company", "Предприятие"

    title = models.CharField("Заголовок", max_length=250)
    summary = models.TextField("Краткое описание")
    body = models.TextField("Дополнительный текст", blank=True)
    image = models.FileField(
        "Фотография", upload_to="news/%Y/%m/", blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp", "gif"])],
    )
    source_url = models.URLField("Ссылка на источник", max_length=1000)
    category = models.CharField("Категория", max_length=20, choices=Category.choices, default=Category.COMPANY)
    published_at = models.DateField("Дата публикации", blank=True, null=True)
    is_featured = models.BooleanField("Главная новость", default=False)
    is_published = models.BooleanField("Опубликовано", default=True)
    position = models.PositiveIntegerField("Порядок (меньше — выше)", default=0)
    created_at = models.DateTimeField("Добавлено", auto_now_add=True)

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
        ordering = ["-is_featured", "position", "-created_at", "-pk"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_featured:
                type(self).objects.exclude(pk=self.pk).filter(is_featured=True).update(is_featured=False)
            super().save(*args, **kwargs)


class Product(models.Model):
    name = models.CharField("Название", max_length=250)
    category = models.CharField("Категория", max_length=100)
    description = models.TextField("Описание", blank=True)
    image = models.FileField("Фотография", upload_to="products/%Y/%m/", blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp", "gif"])])
    unit = models.CharField("Единица измерения", max_length=30, default="шт.")
    price = models.DecimalField("Цена, BYN", max_digits=12, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(0)])
    is_published = models.BooleanField("Опубликовано", default=True)
    position = models.PositiveIntegerField("Порядок (меньше — выше)", default=0)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Продукция"
        ordering = ["position", "name", "pk"]

    def __str__(self):
        return self.name


class OrderRequest(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        PROCESSING = "processing", "В работе"
        COMPLETED = "completed", "Завершена"
        CANCELLED = "cancelled", "Отменена"

    product = models.ForeignKey(Product, verbose_name="Товар", null=True, blank=True,
                                on_delete=models.SET_NULL)
    product_name = models.CharField("Продукция на момент заявки", max_length=250, blank=True)
    customer_name = models.CharField("Имя", max_length=100)
    phone = models.CharField("Телефон", max_length=40)
    comment = models.TextField("Комментарий клиента", blank=True, max_length=3000)
    status = models.CharField("Статус", max_length=20, choices=Status.choices, default=Status.NEW)
    sales_notes = models.TextField("Заметки отдела продаж", blank=True)
    created_at = models.DateTimeField("Получена", auto_now_add=True)
    submission_id = models.UUIDField(unique=True, editable=False)
    notification_sent_at = models.DateTimeField("Уведомление отправлено", null=True, blank=True, editable=False)
    notification_error = models.CharField("Ошибка уведомления", max_length=250, blank=True, editable=False)

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки на продукцию"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заявка №{self.pk} — {self.customer_name}"


class SubmissionLimit(models.Model):
    key = models.CharField(max_length=100, unique=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
