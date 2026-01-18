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
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return ""
    if digits.startswith("8") and len(digits) == 11:
        return f"+7{digits[1:]}"
    if digits.startswith("7") and len(digits) == 11:
        return f"+7{digits[1:]}"
    if len(digits) == 10:
        return f"+7{digits}"
    if raw.startswith("+"):
        return f"+{digits}"
    return digits


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


def cache_login_nonce(chat_id: int, nonce: str) -> None:
    key = f"tg:chat:{chat_id}:nonce"
    cache.set(key, nonce, timeout=60 * 60)


def get_cached_nonce(chat_id: int) -> str | None:
    key = f"tg:chat:{chat_id}:nonce"
    return cache.get(key)


def cache_pending_login(tenant_id: int, nonce: str, phone: str) -> None:
    key = f"tg:nonce:{tenant_id}:{nonce}"
    cache.set(key, phone, timeout=settings.OTP_TTL_SECONDS)


def get_pending_login_phone(tenant_id: int, nonce: str) -> str | None:
    key = f"tg:nonce:{tenant_id}:{nonce}"
    return cache.get(key)


def clear_pending_login(tenant_id: int, nonce: str) -> None:
    key = f"tg:nonce:{tenant_id}:{nonce}"
    cache.delete(key)


def get_telegram_bot_username() -> str:
    raw = (settings.TELEGRAM_BOT_USERNAME or "").strip()
    if raw.startswith("@"):
        raw = raw[1:]
    return raw


def telegram_configured() -> tuple[bool, str | None]:
    username = get_telegram_bot_username()
    if not username:
        return False, "USERNAME_MISSING"
    if not settings.TELEGRAM_BOT_TOKEN:
        return False, "TOKEN_MISSING"
    if settings.TELEGRAM_MODE == "webhook" and not settings.TELEGRAM_WEBHOOK_SECRET:
        return False, "WEBHOOK_SECRET_MISSING"
    return True, None


def build_telegram_start_payload(tenant_slug: str, nonce: str) -> str:
    return f"{tenant_slug}_{nonce}"


def parse_telegram_start_payload(payload: str) -> tuple[str | None, str | None]:
    raw = (payload or "").strip()
    if not raw:
        return None, None
    if "_" in raw:
        tenant_slug, nonce = raw.rsplit("_", 1)
        return tenant_slug.strip() or None, nonce.strip() or None
    if "." in raw:
        tenant_slug, nonce = raw.split(".", 1)
        return tenant_slug.strip() or None, nonce.strip() or None
    return raw, None
