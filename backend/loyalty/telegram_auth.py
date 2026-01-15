import hashlib
import secrets
from datetime import timedelta

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import OneTimeCode, Tenant


def normalize_phone(phone: str) -> str:
    raw = "".join(ch for ch in phone.strip() if ch.isdigit() or ch == "+")
    if raw.startswith("+"):
        digits = "".join(ch for ch in raw if ch.isdigit())
        return f"+{digits}"
    return "".join(ch for ch in raw if ch.isdigit())


def generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp(code: str, purpose: str, recipient: str) -> str:
    raw = f"{settings.SECRET_KEY}:{purpose}:{recipient}:{code}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def issue_telegram_code(tenant: Tenant, phone: str, chat_id: int | None = None):
    purpose = OneTimeCode.Purpose.TELEGRAM_PHONE_LOGIN
    now = timezone.now()
    expires_at = now + timedelta(seconds=settings.OTP_TTL_SECONDS)
    OneTimeCode.objects.filter(
        tenant=tenant,
        purpose=purpose,
        recipient=phone,
        consumed_at__isnull=True,
    ).update(consumed_at=now)
    code = generate_code()
    record = OneTimeCode.objects.create(
        tenant=tenant,
        purpose=purpose,
        recipient=phone,
        code_hash=hash_otp(code, purpose, phone),
        chat_id=chat_id,
        expires_at=expires_at,
    )
    return record, code


def send_telegram_message(chat_id: int, text: str) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)


def get_cached_tenant_slug(chat_id: int) -> str | None:
    key = f"tg:chat:{chat_id}:tenant"
    return cache.get(key)


def cache_tenant_slug(chat_id: int, tenant_slug: str) -> None:
    key = f"tg:chat:{chat_id}:tenant"
    cache.set(key, tenant_slug, timeout=60 * 60)
