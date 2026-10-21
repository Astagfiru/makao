from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

ALLOWED_LINK_PREFIXES = ("https://", "http://", "tel:", "mailto:")


def validate_link(value: str) -> None:
    if not value.startswith(ALLOWED_LINK_PREFIXES):
        raise ValidationError("Ссылка должна начинаться с https://, http://, tel: или mailto:")


class SiteSettings(models.Model):
    """Одна запись: реквизиты оператора ПДн и версии правовых документов."""

    operator_name = models.CharField("ФИО оператора (ИП)", max_length=150, default="Кузьмин Виктор")
    inn = models.CharField("ИНН", max_length=12, blank=True, default="000000000000",
                           help_text="Плейсхолдер — замените на свой ИНН.")
    ogrnip = models.CharField("ОГРНИП", max_length=15, blank=True, default="000000000000000",
                              help_text="Плейсхолдер — замените на свой ОГРНИП.")
    pd_email = models.EmailField("Email для запросов по персональным данным", blank=True,
                                 default="privacy@example.ru")
    city = models.CharField("Город", max_length=60, default="Якутск")
    hosting = models.CharField("Где хранятся данные (хостинг)", max_length=200,
                               default="VPS у ООО «РЕГ.РУ», серверы в Российской Федерации")
    policy_version = models.CharField("Версия политики", max_length=20, default="1.0")
    policy_date = models.DateField("Дата политики", default=timezone.localdate)
    consent_version = models.CharField("Версия согласия", max_length=20, default="1.0")
    consent_date = models.DateField("Дата согласия", default=timezone.localdate)
    map_embed_url = models.URLField(
        "Яндекс.Карта (адрес виджета)", max_length=500,
        default="https://yandex.ru/map-widget/v1/?ll=129.732600%2C62.027600&z=12",
        help_text="Карта грузится только по клику посетителя (у Яндекса свои cookie).",
    )

    class Meta:
        verbose_name = "Настройки и реквизиты"
        verbose_name_plural = "Настройки и реквизиты"

    def __str__(self) -> str:
        return "Настройки сайта и правовые реквизиты"

    def save(self, *args, **kwargs) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ContactChannel(models.Model):
    class Kind(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        TELEGRAM = "telegram", "Telegram"
        PHONE = "phone", "Телефон"
        VK = "vk", "ВКонтакте"
        MAX = "max", "Max"
        EMAIL = "email", "Email"
        OTHER = "other", "Другое"

    kind = models.CharField("Тип", max_length=20, choices=Kind.choices)
    label = models.CharField("Подпись на кнопке", max_length=60)
    url = models.CharField("Ссылка", max_length=300, validators=[validate_link],
                           help_text="Например https://wa.me/79140000000, https://t.me/имя, tel:+79140000000")
    show_in_header = models.BooleanField("В шапке и первом экране", default=False)
    show_in_footer = models.BooleanField("В футере", default=True)
    show_in_cta = models.BooleanField("В блоке «Связаться»", default=True)
    is_active = models.BooleanField("Показывать", default=True)
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Канал связи"
        verbose_name_plural = "Каналы связи"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()}: {self.label}"


class Tariff(models.Model):
    name = models.CharField("Название", max_length=80)
    price_from = models.PositiveIntegerField("Цена от, ₽")
    duration = models.CharField("Срок", max_length=60, help_text="Например «5–7 дней»")
    days_min = models.PositiveSmallIntegerField("Срок от, дней", default=5,
                                                help_text="Для даты «запуск к …» на главной")
    days_max = models.PositiveSmallIntegerField("Срок до, дней", null=True, blank=True,
                                                help_text="Пусто — «не раньше чем через N дней»")
    summary = models.CharField("Кому подходит", max_length=200, blank=True)
    features = models.TextField("Что входит", help_text="Каждый пункт с новой строки")
    is_featured = models.BooleanField("Выделить", default=False)
    is_active = models.BooleanField("Показывать", default=True)
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"
        ordering = ["order", "price_from"]

    def __str__(self) -> str:
        return f"{self.name} — от {self.price_from} ₽"

    @property
    def feature_list(self) -> list[str]:
        return [line.strip() for line in self.features.splitlines() if line.strip()]

    def launch_window(self, start: date) -> tuple[date, date | None]:
        """Когда будет готов сайт, если начать в день start (календарные дни)."""
        end = start + timedelta(days=self.days_max) if self.days_max else None
        return start + timedelta(days=self.days_min), end


class PublishedReviewManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True, author_consent=True)


class Review(models.Model):
    author_name = models.CharField("Имя автора", max_length=40, help_text="Только имя, без фамилии")
    client_niche = models.CharField("Бизнес клиента", max_length=80, blank=True,
                                    help_text="Например «кофейня» — без названия, если клиент не разрешил")
    text = models.TextField("Текст отзыва", max_length=1500)
    author_consent = models.BooleanField(
        "Согласие автора на публикацию получено", default=False,
        help_text="Без отметки отзыв на сайте не показывается.",
    )
    is_published = models.BooleanField("Опубликован", default=False)
    order = models.PositiveSmallIntegerField("Порядок", default=0)
    created_at = models.DateTimeField("Добавлен", auto_now_add=True)

    objects = models.Manager()
    published = PublishedReviewManager()

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["order", "-created_at"]

    def __str__(self) -> str:
        return f"{self.author_name}: {self.text[:40]}"

    def clean(self) -> None:
        if len(self.author_name.split()) > 1:
            raise ValidationError({"author_name": "Укажите только имя, без фамилии."})
        if self.is_published and not self.author_consent:
            raise ValidationError({"is_published": "Опубликовать можно только с согласия автора."})


class FAQItem(models.Model):
    question = models.CharField("Вопрос", max_length=200)
    answer = models.TextField("Ответ")
    is_published = models.BooleanField("Показывать", default=True)
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Вопрос FAQ"
        verbose_name_plural = "Вопросы FAQ"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.question
