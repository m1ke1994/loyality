import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from loyalty.telegram_auth import (
    cache_login_nonce,
    cache_tenant_slug,
    get_cached_nonce,
    get_cached_tenant_slug,
    hash_otp,
    normalize_phone,
    parse_telegram_start_payload,
)
from loyalty.views import rate_limited
from loyalty.models import OneTimeCode, Tenant

logger = logging.getLogger(__name__)


def get_tenant_by_slug(slug: str):
    return Tenant.objects.filter(slug=slug).first()


def generate_login_code(phone: str, tenant_id: int, ttl_seconds: int):
    purpose = OneTimeCode.Purpose.TELEGRAM_PHONE_LOGIN
    now = timezone.now()
    expires_at = now + timedelta(seconds=ttl_seconds)
    OneTimeCode.objects.filter(
        tenant_id=tenant_id,
        purpose=purpose,
        recipient=phone,
        consumed_at__isnull=True,
    ).update(consumed_at=now)
    code = f"{secrets.randbelow(1000000):06d}"
    record = OneTimeCode.objects.create(
        tenant_id=tenant_id,
        purpose=purpose,
        recipient=phone,
        code_hash=hash_otp(code, purpose, phone),
        expires_at=expires_at,
    )
    return record, code


def create_or_update_telegram_auth(phone: str, telegram_user_id: int | None, chat_id: int, tenant_id: int):
    with transaction.atomic():
        record, code = generate_login_code(phone, tenant_id, settings.OTP_TTL_SECONDS)
        record.chat_id = chat_id
        record.save(update_fields=["chat_id"])
    return code


class Command(BaseCommand):
    help = "Run Telegram bot in polling mode"

    def handle(self, *args, **options):
        if settings.TELEGRAM_MODE != "polling":
            self.stdout.write("Telegram bot is disabled (TELEGRAM_MODE != polling).")
            return
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stdout.write("TELEGRAM_BOT_TOKEN is not configured.")
            return

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        dp = Dispatcher()

        @dp.message(CommandStart())
        async def on_start(message):
            logger.info("telegram.start chat_id=%s text=%s", message.chat.id, message.text)
            if message.text:
                parts = message.text.split(maxsplit=1)
                if len(parts) > 1:
                    tenant_slug, nonce = parse_telegram_start_payload(parts[1].strip())
                    if tenant_slug:
                        await sync_to_async(cache_tenant_slug, thread_sensitive=True)(message.chat.id, tenant_slug)
                    if nonce:
                        await sync_to_async(cache_login_nonce, thread_sensitive=True)(message.chat.id, nonce)
                    logger.info(
                        "telegram.start cached tenant_slug=%s nonce=%s chat_id=%s",
                        tenant_slug,
                        nonce,
                        message.chat.id,
                    )
                    if not tenant_slug:
                        await message.answer("Open the bot from your organization link and try again.")
                        return
                else:
                    await message.answer("Open the bot from your organization link and try again.")
                    return
            else:
                await message.answer("Open the bot from your organization link and try again.")
                return
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Share phone number", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
            await message.answer("Send your phone number to get a login code.", reply_markup=kb)

        @dp.message(F.contact)
        async def on_contact(message):
            logger.info(
                "telegram.contact chat_id=%s user_id=%s",
                message.chat.id,
                message.from_user.id if message.from_user else None,
            )
            contact = message.contact
            phone_raw = contact.phone_number
            phone = normalize_phone(phone_raw)
            logger.info("telegram.contact phone raw=%s normalized=%s", phone_raw, phone)
            if not phone:
                await message.answer("Invalid phone number.")
                return
            tenant_slug = await sync_to_async(get_cached_tenant_slug, thread_sensitive=True)(message.chat.id)
            if not tenant_slug:
                logger.warning("telegram.contact missing_tenant_slug chat_id=%s", message.chat.id)
                await message.answer("Open the bot from your organization link and try again.")
                return
            nonce = await sync_to_async(get_cached_nonce, thread_sensitive=True)(message.chat.id)
            if not nonce:
                logger.warning("telegram.contact missing_nonce chat_id=%s tenant_slug=%s", message.chat.id, tenant_slug)
                await message.answer("Open the bot from your organization link and try again.")
                return
            tenant = await sync_to_async(get_tenant_by_slug, thread_sensitive=True)(tenant_slug)
            if not tenant:
                logger.warning("telegram.contact tenant_not_found slug=%s", tenant_slug)
                await message.answer("Tenant not found. Please check the link.")
                return
            rate_key_phone = f"rl:telegram:code:{tenant.id}:{phone}"
            rate_key_chat = f"rl:telegram:chat:{tenant.id}:{message.chat.id}"
            if not settings.TELEGRAM_DISABLE_RATE_LIMIT:
                limited_phone = await sync_to_async(rate_limited, thread_sensitive=True)(
                    rate_key_phone, settings.TELEGRAM_CODE_RATE_LIMIT_PER_HOUR
                )
                limited_chat = await sync_to_async(rate_limited, thread_sensitive=True)(
                    rate_key_chat, settings.TELEGRAM_CHAT_RATE_LIMIT_PER_HOUR
                )
                if limited_phone or limited_chat:
                    logger.info(
                        "telegram.contact rate_limited tenant_id=%s phone=%s chat_id=%s",
                        tenant.id,
                        phone,
                        message.chat.id,
                    )
                    await message.answer("Too many requests. Please try later.")
                    return
            try:
                code = await sync_to_async(create_or_update_telegram_auth, thread_sensitive=True)(
                    phone,
                    message.from_user.id if message.from_user else None,
                    message.chat.id,
                    tenant.id,
                )
            except Exception:
                logger.exception(
                    "telegram.contact failed_to_issue_code tenant_id=%s phone=%s chat_id=%s",
                    tenant.id,
                    phone,
                    message.chat.id,
                )
                await message.answer("Ошибка, попробуйте позже.")
                return
            logger.info(
                "telegram.contact code_issued tenant_id=%s phone=%s nonce=%s",
                tenant.id,
                phone,
                nonce,
            )
            await message.answer(f"Your login code: {code}")

        dp.run_polling(bot)
