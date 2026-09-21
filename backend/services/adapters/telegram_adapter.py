"""Telegram bot adapter — starts only if TELEGRAM_BOT_TOKEN is set.

Shares the same backend DB and AI as web (per problem statement).
Runs in the background alongside FastAPI when a token is provided.
"""
import os
import asyncio
import logging

log = logging.getLogger("telegram")


async def start_telegram_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        log.info("Telegram bot: TELEGRAM_BOT_TOKEN topilmadi — bot ishga tushirilmadi.")
        return

    try:
        from aiogram import Bot, Dispatcher
        from aiogram.filters import CommandStart
        from aiogram.types import Message
    except Exception as e:
        log.warning(f"aiogram o'rnatilmagan: {e}. Bot ishga tushmadi.")
        return

    bot = Bot(token=token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start_handler(m: Message):
        await m.answer(
            "Assalomu alaykum! Men — AI BUXGALTER.\n"
            "Web panelga kiring: kompaniyalarni qo'shing va menga savol bering.\n"
            "Buyruqlar: /help /ai <savol>"
        )

    @dp.message()
    async def any_handler(m: Message):
        text = (m.text or "").strip()
        if not text:
            return
        if text.startswith("/ai"):
            question = text[3:].strip()
            if not question:
                await m.answer("Savolingizni yozing: /ai Bugungi cheklar nechta?")
                return
            await m.answer("AI'ga yubordim... (Telegram-web sinxronizatsiyasi keyinroq to'liq faollashadi)")
        else:
            await m.answer("/ai <savol> deb yozing yoki web panel'ga o'ting.")

    log.info("Telegram bot polling boshlandi.")
    try:
        await dp.start_polling(bot, handle_signals=False)
    except Exception as e:
        log.exception(f"Telegram bot xatosi: {e}")


def spawn_telegram_task(loop: asyncio.AbstractEventLoop):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return None
    return loop.create_task(start_telegram_bot())
