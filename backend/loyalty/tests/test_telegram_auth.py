from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from loyalty.models import OneTimeCode, Tenant, User
from loyalty.telegram_auth import hash_otp


class TelegramAuthTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="org1", name="Org 1")

    @patch("loyalty.views.send_telegram_message")
    def test_webhook_contact_creates_otp(self, send_mock):
        headers = {"HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN": "secret"}
        with self.settings(
            TELEGRAM_WEBHOOK_SECRET="secret",
            TELEGRAM_CODE_RATE_LIMIT_PER_HOUR=100,
            TELEGRAM_CHAT_RATE_LIMIT_PER_HOUR=100,
        ):
            start_payload = {"message": {"chat": {"id": 10}, "text": "/start org1"}}
            self.client.post("/api/v1/integrations/telegram/webhook", start_payload, content_type="application/json", **headers)
            contact_payload = {
                "message": {
                    "chat": {"id": 10},
                    "contact": {"phone_number": "+79995554433"},
                }
            }
            self.client.post("/api/v1/integrations/telegram/webhook", contact_payload, content_type="application/json", **headers)
        self.assertTrue(OneTimeCode.objects.filter(tenant=self.tenant).exists())
        send_mock.assert_called()

    def test_verify_creates_user_and_tokens(self):
        phone = "+79995554433"
        code = "123456"
        now = timezone.now()
        OneTimeCode.objects.create(
            tenant=self.tenant,
            purpose=OneTimeCode.Purpose.TELEGRAM_PHONE_LOGIN,
            recipient=phone,
            code_hash=hash_otp(code, OneTimeCode.Purpose.TELEGRAM_PHONE_LOGIN, phone),
            expires_at=now + timedelta(minutes=5),
        )
        res = self.client.post(
            f"/api/v1/t/{self.tenant.slug}/auth/telegram/verify",
            {"phone": phone, "code": code},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("tokens", res.json())
        user = User.objects.get(tenant=self.tenant, phone=phone)
        self.assertTrue(user.phone_verified)
