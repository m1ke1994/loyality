from django.conf import settings
from django.core.management.base import BaseCommand

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from loyalty.telegram_auth import cache_tenant_slug, get_cached_tenant_slug, issue_telegram_code, normalize_phone
from loyalty.views import rate_limited
from loyalty.models import Tenant


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
            if message.text:
                parts = message.text.split(maxsplit=1)
                if len(parts) > 1:
                    cache_tenant_slug(message.chat.id, parts[1].strip())
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Share phone number", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
            await message.answer("Send your phone number to get a login code.", reply_markup=kb)

        @dp.message(F.contact)
        async def on_contact(message):
            contact = message.contact
            phone = normalize_phone(contact.phone_number)
            if not phone:
                await message.answer("Invalid phone number.")
                return
            tenant_slug = get_cached_tenant_slug(message.chat.id)
            if not tenant_slug:
                await message.answer("Open the bot from your tenant link and try again.")
                return
            tenant = Tenant.objects.filter(slug=tenant_slug).first()
            if not tenant:
                await message.answer("Tenant not found. Please check the link.")
                return
            rate_key_phone = f"rl:telegram:code:{tenant.id}:{phone}"
            rate_key_chat = f"rl:telegram:chat:{tenant.id}:{message.chat.id}"
            if rate_limited(rate_key_phone, settings.TELEGRAM_CODE_RATE_LIMIT_PER_HOUR) or rate_limited(
                rate_key_chat, settings.TELEGRAM_CHAT_RATE_LIMIT_PER_HOUR
            ):
                await message.answer("Too many requests. Please try later.")
                return
            _, code = issue_telegram_code(tenant, phone, chat_id=message.chat.id)
            await message.answer(f"Your login code: {code}")

        dp.run_polling(bot)
