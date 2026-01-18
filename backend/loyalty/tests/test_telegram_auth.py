from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from loyalty.models import OneTimeCode, Tenant, User
from loyalty.telegram_auth import (
    build_telegram_start_payload,
    cache_pending_login,
    hash_otp,
    normalize_phone,
    parse_telegram_start_payload,
    telegram_configured,
)


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

    def test_telegram_configured_missing_username(self):
        with self.settings(TELEGRAM_BOT_USERNAME="", TELEGRAM_BOT_TOKEN="token", TELEGRAM_MODE="polling"):
            configured, reason = telegram_configured()
        self.assertFalse(configured)
        self.assertEqual(reason, "USERNAME_MISSING")

    def test_telegram_configured_ok(self):
        with self.settings(TELEGRAM_BOT_USERNAME="@app_messenger_bot", TELEGRAM_BOT_TOKEN="token", TELEGRAM_MODE="polling"):
            configured, reason = telegram_configured()
        self.assertTrue(configured)
        self.assertIsNone(reason)

    def test_telegram_config_endpoint(self):
        with self.settings(TELEGRAM_BOT_USERNAME="app_messenger_bot", TELEGRAM_BOT_TOKEN="token", TELEGRAM_MODE="polling"):
            res = self.client.get(f"/api/v1/t/{self.tenant.slug}/auth/telegram/config")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["configured"])
        self.assertEqual(data["bot_username"], "app_messenger_bot")

    def test_normalize_phone_ru(self):
        self.assertEqual(normalize_phone("89017800504"), "+79017800504")
        self.assertEqual(normalize_phone("+79017800504"), "+79017800504")
        self.assertEqual(normalize_phone("79017800504"), "+79017800504")
        self.assertEqual(normalize_phone("9017800504"), "+79017800504")

    def test_verify_code_wrong_tenant(self):
        other = Tenant.objects.create(slug="org2", name="Org 2")
        phone = "+79017800504"
        code = "123456"
        now = timezone.now()
        OneTimeCode.objects.create(
            tenant=other,
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
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["detail"], "CODE_INVALID")

    def test_parse_start_payload(self):
        payload = build_telegram_start_payload("org1", "nonce123")
        tenant_slug, nonce = parse_telegram_start_payload(payload)
        self.assertEqual(tenant_slug, "org1")
        self.assertEqual(nonce, "nonce123")
        tenant_slug_dot, nonce_dot = parse_telegram_start_payload("org1.nonce456")
        self.assertEqual(tenant_slug_dot, "org1")
        self.assertEqual(nonce_dot, "nonce456")

    def test_verify_with_nonce(self):
        phone = "+79017800504"
        code = "123456"
        now = timezone.now()
        cache_pending_login(self.tenant.id, "nonce123", phone)
        OneTimeCode.objects.create(
            tenant=self.tenant,
            purpose=OneTimeCode.Purpose.TELEGRAM_PHONE_LOGIN,
            recipient=phone,
            code_hash=hash_otp(code, OneTimeCode.Purpose.TELEGRAM_PHONE_LOGIN, phone),
            expires_at=now + timedelta(minutes=5),
        )
        res = self.client.post(
            f"/api/v1/t/{self.tenant.slug}/auth/telegram/verify",
            {"phone": phone, "code": code, "nonce": "nonce123"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
