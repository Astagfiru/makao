import re

from django import forms

PHONE_ALLOWED = re.compile(r"[\d\s()+\-]+")
PHONE_DIGITS_MIN, PHONE_DIGITS_MAX = 10, 15
CONSENT_ERROR = "Без согласия на обработку персональных данных мы не можем принять заявку."


class LeadForm(forms.Form):
    name = forms.CharField(
        label="Ваше имя", min_length=2, max_length=100,
        widget=forms.TextInput(attrs={"autocomplete": "given-name", "placeholder": "Как к вам обращаться"}),
    )
    phone = forms.CharField(
        label="Телефон", max_length=30,
        widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel", "inputmode": "tel",
                                      "placeholder": "+7 914 000-00-00"}),
    )
    message = forms.CharField(
        label="Что нужно", max_length=2000, required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Например: лендинг для кофейни с меню и записью"}),
    )
    # Чекбокс не отмечен по умолчанию; без него форма не проходит проверку на сервере.
    consent = forms.BooleanField(required=True, error_messages={"required": CONSENT_ERROR})
    # Поле-ловушка для ботов: скрыто от людей, заполняют его только роботы.
    website = forms.CharField(required=False, max_length=200)
    page = forms.CharField(required=False, max_length=200, widget=forms.HiddenInput)

    def clean_name(self) -> str:
        return " ".join(self.cleaned_data["name"].split())

    def clean_phone(self) -> str:
        phone = self.cleaned_data["phone"].strip()
        if not PHONE_ALLOWED.fullmatch(phone):
            raise forms.ValidationError("В номере могут быть только цифры, пробелы, скобки, «+» и «-».")
        digits = re.sub(r"\D", "", phone)
        if not PHONE_DIGITS_MIN <= len(digits) <= PHONE_DIGITS_MAX:
            raise forms.ValidationError("Проверьте номер телефона: в нём должно быть 10–15 цифр.")
        return phone

    def clean_page(self) -> str:
        page = self.cleaned_data.get("page", "")
        return page if page.startswith("/") else ""

    @property
    def is_bot(self) -> bool:
        return bool(self.cleaned_data.get("website"))
