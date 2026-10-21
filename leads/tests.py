from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import SiteSettings
from leads import telegram
from leads.models import Lead

VALID = {"name": "Айсен", "phone": "+7 914 123-45-67", "message": "Лендинг для кофейни", "consent": "on", "page": "/"}


class LeadFormTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.url = reverse("leads:create")

    def test_valid_lead_is_saved_with_consent_time_and_versions(self) -> None:
        site = SiteSettings.load()
        site.policy_version, site.consent_version = "2.1", "1.3"
        site.save()
        response = self.client.post(self.url, VALID)
        self.assertRedirects(response, reverse("leads:thanks"))
        lead = Lead.objects.get()
        self.assertTrue(lead.consent)
        self.assertIsNotNone(lead.consent_at)
        self.assertEqual((lead.policy_version, lead.consent_version), ("2.1", "1.3"))
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertEqual(lead.page, "/")

    def test_without_consent_lead_is_rejected_on_server(self) -> None:
        data = {k: v for k, v in VALID.items() if k != "consent"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Без согласия", status_code=400)
        self.assertFalse(Lead.objects.exists())

    def test_consent_checkbox_is_not_checked_by_default(self) -> None:
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, 'name="consent"')
        self.assertNotContains(response, 'name="consent" checked')

    def test_bad_phone_is_rejected(self) -> None:
        for phone in ("123", "+7 (914) abc", "1" * 20):
            response = self.client.post(self.url, {**VALID, "phone": phone})
            self.assertEqual(response.status_code, 400, phone)
        self.assertFalse(Lead.objects.exists())

    def test_honeypot_pretends_success_but_saves_nothing(self) -> None:
        response = self.client.post(self.url, {**VALID, "website": "http://spam"})
        self.assertRedirects(response, reverse("leads:thanks"))
        self.assertFalse(Lead.objects.exists())

    def test_foreign_page_value_is_dropped(self) -> None:
        self.client.post(self.url, {**VALID, "page": "https://evil.example"})
        self.assertEqual(Lead.objects.get().page, "")

    @override_settings(LEAD_RATE_LIMIT=2)
    def test_rate_limit_blocks_flood(self) -> None:
        for _ in range(2):
            self.client.post(self.url, VALID)
        response = self.client.post(self.url, VALID)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(Lead.objects.count(), 2)

    @override_settings(BEHIND_PROXY=True, LEAD_RATE_LIMIT=1)
    def test_rate_limit_uses_forwarded_ip_behind_proxy(self) -> None:
        self.client.post(self.url, VALID, HTTP_X_FORWARDED_FOR="10.0.0.1")
        other = self.client.post(self.url, VALID, HTTP_X_FORWARDED_FOR="10.0.0.2")
        self.assertEqual(other.status_code, 302)
        same = self.client.post(self.url, VALID, HTTP_X_FORWARDED_FOR="10.0.0.1")
        self.assertEqual(same.status_code, 429)

    def test_thanks_page_shows_number_and_is_noindex(self) -> None:
        self.client.post(self.url, VALID)
        response = self.client.get(reverse("leads:thanks"))
        self.assertContains(response, f"Номер заявки — {Lead.objects.get().pk}")
        self.assertEqual(response["X-Robots-Tag"], "noindex")

    def test_form_page_get(self) -> None:
        self.assertContains(self.client.get(self.url), "Заявка на сайт")


class TelegramTests(TestCase):
    def test_message_has_number_and_admin_link_but_no_personal_data(self) -> None:
        lead = Lead.objects.create(name="Айсен", phone="+79141234567", message="секретный текст", consent=True)
        text = telegram.build_message(lead.pk)
        self.assertIn(f"Новая заявка №{lead.pk}", text)
        self.assertIn(f"/admin/leads/lead/{lead.pk}/change/", text)
        for private in ("Айсен", "79141234567", "секретный"):
            self.assertNotIn(private, text)

    @override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="")
    def test_without_token_sending_is_skipped(self) -> None:
        with mock.patch("leads.telegram.urlopen") as urlopen:
            self.assertFalse(telegram.send_telegram("x"))
            urlopen.assert_not_called()

    @override_settings(TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_CHAT_ID="42")
    def test_sends_to_bot_api(self) -> None:
        response = mock.MagicMock(status=200)
        response.__enter__.return_value = response
        with mock.patch("leads.telegram.urlopen", return_value=response) as urlopen:
            self.assertTrue(telegram.send_telegram("Новая заявка №1"))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.telegram.org/bot123:abc/sendMessage")
        self.assertIn(b"chat_id=42", request.data)

    @override_settings(TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_CHAT_ID="42")
    def test_network_error_does_not_break_anything(self) -> None:
        with mock.patch("leads.telegram.urlopen", side_effect=OSError("down")):
            with self.assertLogs("leads", level="WARNING"):
                self.assertFalse(telegram.send_telegram("x"))

    @override_settings(TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_CHAT_ID="42")
    def test_lead_submission_notifies_after_commit(self) -> None:
        cache.clear()
        with mock.patch("leads.telegram.start_background") as start:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(reverse("leads:create"), VALID)
        lead = Lead.objects.get()
        start.assert_called_once_with(telegram.build_message(lead.pk))

    @override_settings(TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_CHAT_ID="42")
    def test_background_thread_calls_sender(self) -> None:
        with mock.patch("leads.telegram.threading.Thread") as thread:
            telegram.start_background("x")
        thread.assert_called_once_with(target=telegram.send_telegram, args=("x",), daemon=True)


class LeadAdminTests(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth.models import User
        self.admin = User.objects.create_superuser("boss", "", "strong-pass-123")
        self.lead = Lead.objects.create(name="Айсен", phone="+79141234567", consent=True)

    def test_admin_requires_login(self) -> None:
        response = self.client.get(reverse("admin:leads_lead_changelist"))
        self.assertEqual(response.status_code, 302)

    def test_admin_lists_leads_and_cannot_add(self) -> None:
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:leads_lead_changelist"))
        self.assertContains(response, "Айсен")
        self.assertContains(response, "Новая")
        self.assertEqual(self.client.get(reverse("admin:leads_lead_add")).status_code, 403)

    def test_admin_change_page_opens(self) -> None:
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:leads_lead_change", args=[self.lead.pk]))
        self.assertContains(response, "Согласие на обработку персональных данных")
