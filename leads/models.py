from django.db import models


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В работе"
        CLOSED = "closed", "Закрыта"

    name = models.CharField("Имя", max_length=100)
    phone = models.CharField("Телефон", max_length=30)
    message = models.TextField("Что нужно", max_length=2000, blank=True)
    page = models.CharField("Страница формы", max_length=200, blank=True)
    consent = models.BooleanField("Согласие на обработку ПДн", default=False)
    consent_at = models.DateTimeField("Дата и время согласия", null=True, blank=True)
    policy_version = models.CharField("Версия политики", max_length=20, blank=True)
    consent_version = models.CharField("Версия согласия", max_length=20, blank=True)
    status = models.CharField("Статус", max_length=20, choices=Status.choices, default=Status.NEW)
    note = models.TextField("Заметка (видна только в админке)", blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Изменена", auto_now=True)

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Заявка №{self.pk}"
