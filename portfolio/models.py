from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse

from portfolio.images import to_webp, validate_image_size


class Niche(models.Model):
    name = models.CharField("Ниша", max_length=60)
    slug = models.SlugField("Адрес (латиницей)", unique=True)
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Ниша"
        verbose_name_plural = "Ниши"
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name


class DemoSite(models.Model):
    """Демо-концепт сайта реального бизнеса. Содержимое — блоки в JSON (у каждой ниши свои)."""

    class Theme(models.TextChoices):
        DENTAL = "dental", "Стоматология: «Бриллиант»"
        DRYCLEAN = "dryclean", "Химчистка: «Снег»"
        BARBER = "barber", "Барбершоп: «Латунь»"
        SALON = "salon", "Салон: «Градиент»"
        AUTOBODY = "autobody", "Кузовной ремонт: «Индустрия»"
        FLOWERS = "flowers", "Цветы: «Пастель»"
        CAFE = "cafe", "Кофейня: «Крафт»"
        ATELIER = "atelier", "Ателье: «Бархат»"
        PHONEREPAIR = "phonerepair", "Ремонт телефонов: «Схема»"

    business_name = models.CharField("Название бизнеса", max_length=100)
    slug = models.SlugField("Адрес примера (латиницей)", unique=True)
    theme = models.CharField("Оформление", max_length=20, choices=Theme.choices)
    blocks = models.JSONField("Блоки страницы", default=dict, blank=True,
                              help_text="Содержимое примера: первый экран, услуги, цены, часы работы и т.д.")
    sources = models.JSONField("Источники данных", default=list, blank=True,
                               help_text="Список {url, what, checked_at} — откуда взяты факты.")
    source_url = models.URLField("Карточка бизнеса в 2ГИС", blank=True)
    checked_at = models.DateField("Дата проверки данных", null=True, blank=True)
    is_published = models.BooleanField("Опубликован", default=True)

    class Meta:
        verbose_name = "Пример сайта"
        verbose_name_plural = "Примеры сайтов"
        ordering = ["business_name"]

    def __str__(self) -> str:
        return self.business_name

    def get_absolute_url(self) -> str:
        return reverse("portfolio:demo", args=[self.slug])


class PublishedCaseManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


class Case(models.Model):
    title = models.CharField("Название", max_length=120)
    slug = models.SlugField("Адрес (латиницей)", unique=True)
    niche = models.ForeignKey(Niche, verbose_name="Ниша", on_delete=models.PROTECT, related_name="cases")
    demo = models.ForeignKey(DemoSite, verbose_name="Пример сайта", on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="cases")
    summary = models.CharField("Коротко (для карточки)", max_length=200)
    preview = models.ImageField(
        "Превью", upload_to="cases/", blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validate_image_size],
        help_text="JPG, PNG или WebP до 5 МБ — сохранится в WebP автоматически.",
    )
    task = models.TextField("Задача")
    solution = models.TextField("Решение")
    done = models.TextField("Что сделано", help_text="Каждый пункт с новой строки")
    is_demo_project = models.BooleanField("Пример работы (не заказ)", default=True,
                                          help_text="Снимите отметку, когда бизнес станет реальным клиентом.")
    is_published = models.BooleanField("Опубликовано", default=True)
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    objects = models.Manager()
    published = PublishedCaseManager()

    class Meta:
        verbose_name = "Кейс"
        verbose_name_plural = "Кейсы"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("portfolio:case", args=[self.slug])

    @property
    def done_list(self) -> list[str]:
        return [line.strip() for line in self.done.splitlines() if line.strip()]

    def save(self, *args, **kwargs) -> None:
        if self.preview and not self.preview._committed:  # новый файл: всегда в webp, без EXIF, ≤ 1600 px
            self.preview = to_webp(self.preview.file)
        super().save(*args, **kwargs)
