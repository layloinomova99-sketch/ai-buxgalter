"""Telegram bot adapter — Creator-only training channel.

Shares the same DB + AI agent as the web app. Starts only if TELEGRAM_BOT_TOKEN is set.
"""
import os
import asyncio
import logging
from typing import Optional
from bson import ObjectId

from core.db import get_db, iso_now
from core.security import verify_password

log = logging.getLogger("telegram")

MAX_FILE_BYTES = 20 * 1024 * 1024
NOT_CREATOR = "⛔ Bu bot faqat Creator uchun. Web paneldan foydalaning."
NOT_LINKED = "Avval hisobingizni bog'lang:\n/login email parol"

HELP_TEXT = (
    "🤖 *AI BUXGALTER — Creator boti*\n\n"
    "Bu bot orqali AI'ni o'rgatasiz:\n"
    "📎 *Fayl yuboring* (.py .txt .pdf .docx .xlsx .json, rasm) — AI o'qib, bilim bazasiga qoidalar sifatida saqlaydi. "
    "Fayl bilan birga izoh (caption) yozsangiz, AI uni hisobga oladi.\n"
    "✍️ *Oddiy matn yozing* — AI bilan suhbat. Qoida o'rgatmoqchi bo'lsangiz shunchaki tushuntiring, "
    "masalan: «Yandex cheklarini 1C'da Sotuv hujjati sifatida yoz».\n\n"
    "*Buyruqlar:*\n"
    "/login email parol — hisobni bog'lash\n"
    "/kompaniya — aktiv kompaniyani tanlash\n"
    "/qoidalar — oxirgi qoidalar\n"
    "/bilim — yuklangan fayllar\n"
    "/tasdiqlar — kutilayotgan tasdiqlar\n"
    "🎤 Ovozli xabar — matnga o'giriladi va AI'ga yuboriladi\n"
    "📊 Soliq 'Чеклар рўйхати' .xlsx — cheklar sifatida import qilinadi (aktiv kompaniya kerak)\n"
    "/yangi — yangi suhbat boshlash\n"
    "/chiqish — hisobni uzish\n"
    "/yordam — bu xabar"
)


async def _link_for(tg_id: int) -> Optional[dict]:
    db = get_db()
    link = await db.telegram_links.find_one({"telegram_id": tg_id})
    if not link:
        return None
    user = await db.users.find_one({"_id": ObjectId(link["user_id"])})
    if not user or user.get("role") != "creator" or not user.get("active", True):
        return None
    link["user"] = user
    return link


def _md_escape(s: str) -> str:
    return s


async def start_telegram_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        log.info("Telegram bot: TELEGRAM_BOT_TOKEN topilmadi — bot ishga tushirilmadi.")
        return

    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import Command, CommandStart
    from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.enums import ChatAction

    from services.ai_agent import run_agent_turn
    from services.knowledge import ingest_file
    from services.approvals import decide_action, list_actions
    from services.adapters.soliq_adapter import is_soliq_excel
    from services.receipts_service import import_soliq_excel

    bot = Bot(token=token)
    dp = Dispatcher()
    db = get_db()

    async def _ensure_conversation(link: dict) -> str:
        if link.get("conversation_id"):
            return link["conversation_id"]
        res = await db.ai_conversations.insert_one({
            "user_id": link["user_id"], "company_id": link.get("active_company_id"),
            "title": "Telegram suhbat", "source": "telegram",
            "created_at": iso_now(), "updated_at": iso_now(),
        })
        cid = str(res.inserted_id)
        await db.telegram_links.update_one({"_id": link["_id"]}, {"$set": {"conversation_id": cid}})
        return cid

    @dp.message(CommandStart())
    async def start_handler(m: Message):
        link = await _link_for(m.from_user.id)
        if link:
            await m.answer(f"Xush kelibsiz, {link['user'].get('full_name')}! 👋\n\n" + HELP_TEXT, parse_mode="Markdown")
        else:
            await m.answer(
                "Assalomu alaykum! Men — AI BUXGALTER Creator boti.\n\n"
                "Bu bot orqali faqat Creator AI'ni o'rgatadi (fayl yuklash, qoidalar).\n\n"
                "Hisobingizni bog'lash uchun:\n/login email parol"
            )

    @dp.message(Command("yordam", "help"))
    async def help_handler(m: Message):
        await m.answer(HELP_TEXT, parse_mode="Markdown")

    @dp.message(Command("login"))
    async def login_handler(m: Message):
        parts = (m.text or "").split(maxsplit=2)
        try:
            await m.delete()
        except Exception:
            pass
        if len(parts) < 3:
            await m.answer("Format: /login email parol")
            return
        email, password = parts[1].strip().lower(), parts[2].strip()
        user = await db.users.find_one({"email": email})
        if not user or not verify_password(password, user.get("password_hash", "")):
            await m.answer("❌ Email yoki parol noto'g'ri.")
            return
        if user.get("role") != "creator":
            await m.answer(NOT_CREATOR)
            return
        await db.telegram_links.update_one(
            {"telegram_id": m.from_user.id},
            {"$set": {"user_id": str(user["_id"]), "telegram_username": m.from_user.username,
                      "telegram_id": m.from_user.id, "updated_at": iso_now()},
             "$setOnInsert": {"created_at": iso_now(), "active_company_id": None, "conversation_id": None}},
            upsert=True,
        )
        await db.audit_logs.insert_one({"who": str(user["_id"]), "what": "Telegram hisobi bog'landi", "when": iso_now(),
                                        "company_id": None, "source": "telegram", "created_at": iso_now(), "updated_at": iso_now()})
        await m.answer(f"✅ Bog'landi: {user.get('full_name')} (Creator)\n\n" + HELP_TEXT, parse_mode="Markdown")

    @dp.message(Command("chiqish", "logout"))
    async def logout_handler(m: Message):
        await db.telegram_links.delete_one({"telegram_id": m.from_user.id})
        await m.answer("Hisob uzildi. Qayta bog'lash: /login email parol")

    @dp.message(Command("yangi"))
    async def new_conv_handler(m: Message):
        link = await _link_for(m.from_user.id)
        if not link:
            return await m.answer(NOT_LINKED)
        await db.telegram_links.update_one({"_id": link["_id"]}, {"$set": {"conversation_id": None}})
        await m.answer("🆕 Yangi suhbat boshlandi.")

    @dp.message(Command("kompaniya"))
    async def company_handler(m: Message):
        link = await _link_for(m.from_user.id)
        if not link:
            return await m.answer(NOT_LINKED)
        rows = [c async for c in db.companies.find({}).sort("name", 1).limit(30)]
        if not rows:
            return await m.answer("Hali kompaniya yo'q. Web panelda qo'shing.")
        kb = [[InlineKeyboardButton(text=f"{'✅ ' if str(c['_id']) == link.get('active_company_id') else ''}{c['name']}", callback_data=f"co:{c['_id']}")] for c in rows]
        kb.append([InlineKeyboardButton(text="🌐 Global (kompaniyasiz)", callback_data="co:none")])
        await m.answer("Aktiv kompaniyani tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    @dp.callback_query(F.data.startswith("co:"))
    async def company_cb(cq: CallbackQuery):
        link = await _link_for(cq.from_user.id)
        if not link:
            return await cq.answer(NOT_LINKED, show_alert=True)
        val = cq.data[3:]
        cid = None if val == "none" else val
        name = "Global"
        if cid:
            c = await db.companies.find_one({"_id": ObjectId(cid)})
            name = c["name"] if c else "?"
        await db.telegram_links.update_one({"_id": link["_id"]}, {"$set": {"active_company_id": cid, "conversation_id": None}})
        await cq.message.edit_text(f"Aktiv kompaniya: *{name}*", parse_mode="Markdown")
        await cq.answer()

    @dp.message(Command("qoidalar"))
    async def rules_handler(m: Message):
        link = await _link_for(m.from_user.id)
        if not link:
            return await m.answer(NOT_LINKED)
        rows = [r async for r in db.ai_rules.find({"status": "active"}).sort("_id", -1).limit(10)]
        if not rows:
            return await m.answer("Hali qoidalar yo'q. Fayl yuboring yoki tushuntiring.")
        total = await db.ai_rules.count_documents({"status": "active"})
        lines = [f"📜 Jami {total} qoida. Oxirgi {len(rows)} ta:\n"]
        for r in rows:
            lines.append(f"• [{r.get('category')}] {r.get('instruction', '')[:180]}")
        await m.answer("\n".join(lines))

    @dp.message(Command("bilim"))
    async def kb_handler(m: Message):
        link = await _link_for(m.from_user.id)
        if not link:
            return await m.answer(NOT_LINKED)
        rows = [d async for d in db.knowledge_docs.find({}).sort("_id", -1).limit(10)]
        if not rows:
            return await m.answer("Bilim bazasi bo'sh. Fayl yuboring.")
        lines = ["📚 Yuklangan fayllar:\n"]
        for d in rows:
            st = {"ready": "✅", "failed": "❌"}.get(d.get("status"), "⏳")
            lines.append(f"{st} {d.get('filename')} — {len(d.get('rule_ids') or [])} qoida")
        await m.answer("\n".join(lines))

    def _action_kb(action_id: str):
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"act:ok:{action_id}"),
            InlineKeyboardButton(text="❌ Bekor", callback_data=f"act:no:{action_id}"),
        ]])

    async def _send_pending(chat_id: int, action_ids: list):
        for aid in action_ids:
            a = await db.pending_actions.find_one({"_id": ObjectId(aid)})
            if not a or a.get("status") != "pending":
                continue
            await bot.send_message(chat_id, f"⚠️ *Tasdiq kerak*\n{a.get('description')}\n\nTuri: {a.get('action_type')}",
                                   parse_mode="Markdown", reply_markup=_action_kb(aid))

    @dp.message(Command("tasdiqlar"))
    async def pending_handler(m: Message):
        link = await _link_for(m.from_user.id)
        if not link:
            return await m.answer(NOT_LINKED)
        rows = await list_actions(status="pending", limit=10)
        if not rows:
            return await m.answer("Kutilayotgan tasdiqlar yo'q ✅")
        for a in rows:
            await m.answer(f"⚠️ {a['label']}\n{a['description']}", reply_markup=_action_kb(a["id"]))

    @dp.callback_query(F.data.startswith("act:"))
    async def action_cb(cq: CallbackQuery):
        link = await _link_for(cq.from_user.id)
        if not link:
            return await cq.answer(NOT_CREATOR, show_alert=True)
        _, verdict, aid = cq.data.split(":", 2)
        approve = verdict == "ok"
        try:
            await cq.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        if approve:
            await cq.message.answer("⏳ Bajarilmoqda...")
        try:
            res = await decide_action(aid, link["user_id"], approve, source="telegram")
        except Exception as e:
            return await cq.message.answer(f"❌ Xato: {e}")
        if res["status"] == "rejected":
            txt = f"❌ Bekor qilindi: {res['description']}"
        elif res["status"] == "done":
            r = res.get("result") or {}
            detail = ""
            if r.get("ref_key"): detail = f"\n1C Ref: `{r['ref_key']}`"
            if "imported" in r: detail = f"\nYozildi: {r['imported']} ta, xato: {len(r.get('failed') or [])}"
            if "synced" in r: detail = f"\nSinxronlandi: {r['synced']} ta mahsulot"
            if r.get("already"): detail += "\n(1C da allaqachon mavjud edi)"
            if r.get("warnings"): detail += "\n⚠️ " + "; ".join(r["warnings"][:3])
            txt = f"✅ Bajarildi: {res['description']}{detail}"
        else:
            txt = f"❌ Bajarilmadi: {res['description']}\n{res.get('error') or (res.get('result') or {}).get('failed') or ''}"
        try:
            await cq.message.answer(txt, parse_mode="Markdown")
        except Exception:
            await cq.message.answer(txt)
        await cq.answer()

    @dp.message(F.voice | F.audio)
    async def voice_handler(m: Message):
        link = await _link_for(m.from_user.id)
        if not link:
            existing = await db.telegram_links.find_one({"telegram_id": m.from_user.id})
            return await m.answer(NOT_CREATOR if existing else NOT_LINKED)
        v = m.voice or m.audio
        if (v.file_size or 0) > 24 * 1024 * 1024:
            return await m.answer("Audio 24 MB dan katta.")
        status = await m.answer("🎤 Ovoz matnga o'girilmoqda...")
        try:
            tg_file = await bot.get_file(v.file_id)
            buf = await bot.download_file(tg_file.file_path)
            from services.speech import transcribe
            text = await transcribe(buf.read(), "voice.ogg" if m.voice else (v.file_name or "audio.mp3"))
        except Exception as e:
            log.exception("voice failed")
            return await status.edit_text(f"❌ Ovozni o'girib bo'lmadi: {e}")
        if not text.strip():
            return await status.edit_text("❌ Ovozdan matn ajratilmadi.")
        await status.edit_text(f"📝 Siz: _{text}_", parse_mode="Markdown")
        await _ai_reply(m, link, text)

    async def _ai_reply(m: Message, link: dict, text: str):
        await bot.send_chat_action(m.chat.id, ChatAction.TYPING)
        conv_id = await _ensure_conversation(link)
        try:
            result = await run_agent_turn(user_id=link["user_id"], conversation_id=conv_id,
                                          company_id=link.get("active_company_id"), user_text=text, source="telegram")
        except Exception as e:
            log.exception("AI turn failed")
            return await m.answer(f"❌ AI xatosi: {e}")
        reply = result.get("content") or "(bo'sh javob)"
        saved = [t for t in result.get("tool_trace", []) if t.get("tool") == "save_creator_rule" and t.get("result", {}).get("saved")]
        if saved:
            reply += f"\n\n📜 {len(saved)} ta qoida saqlandi."
        for i in range(0, len(reply), 4000):
            await m.answer(reply[i:i + 4000])
        if result.get("pending_action_ids"):
            await _send_pending(m.chat.id, result["pending_action_ids"])

    async def _handle_file(m: Message, file_id: str, filename: str, size: int):
        link = await _link_for(m.from_user.id)
        if not link:
            return await m.answer(NOT_LINKED if not await db.telegram_links.find_one({"telegram_id": m.from_user.id}) else NOT_CREATOR)
        if size and size > MAX_FILE_BYTES:
            return await m.answer("Fayl 20 MB dan katta. Kichikroq fayl yuboring.")
        status = await m.answer(f"📥 {filename} qabul qilindi. AI tahlil qilmoqda...")
        await bot.send_chat_action(m.chat.id, ChatAction.TYPING)
        try:
            tg_file = await bot.get_file(file_id)
            buf = await bot.download_file(tg_file.file_path)
            data = buf.read()
        except Exception as e:
            return await status.edit_text(f"❌ Faylni yuklab olishda xato: {e}")
        if filename.lower().endswith((".xlsx", ".xlsm")) and is_soliq_excel(data):
            cid = link.get("active_company_id")
            if not cid:
                return await status.edit_text("📊 Bu Soliq cheklar fayli. Avval /kompaniya bilan aktiv kompaniyani tanlang.")
            try:
                r = await import_soliq_excel(cid, link["user_id"], data, source="telegram")
            except Exception as e:
                return await status.edit_text(f"❌ Cheklar import qilinmadi: {e}")
            txt = (f"📊 *Soliq cheklar import qilindi*\n"
                   f"Yangi: {r['created']} · Takror: {r['duplicates']} · O'tkazildi: {r['skipped']}\n"
                   f"✅ To'liq moslashgan: {r['matched']}\n⚠️ Ko'rib chiqish kerak: {r['needs_review']}\n\n"
                   "1C ga yozish uchun: «matched cheklarni 1C ga yoz» deb yozing yoki web paneldan yuboring.")
            return await status.edit_text(txt, parse_mode="Markdown")
        result = await ingest_file(link["user_id"], filename, data, source="telegram",
                                   company_id=link.get("active_company_id"), note=m.caption)
        if result.get("status") != "ready":
            return await status.edit_text(f"❌ Tahlil qilinmadi: {result.get('error', 'noma`lum xato')}")
        facts = "\n".join(f"• {f}" for f in (result.get("key_facts") or [])[:6])
        text = (
            f"✅ *{result.get('title') or filename}*\n\n{result.get('summary', '')}\n\n"
            + (f"*Asosiy faktlar:*\n{facts}\n\n" if facts else "")
            + f"📜 {result.get('rules_count', 0)} ta qoida bilim bazasiga qo'shildi.\n"
            "Tuzatish kerak bo'lsa, shunchaki yozing."
        )
        try:
            await status.edit_text(text, parse_mode="Markdown")
        except Exception:
            await status.edit_text(text)

    @dp.message(F.document)
    async def document_handler(m: Message):
        d = m.document
        await _handle_file(m, d.file_id, d.file_name or "fayl", d.file_size or 0)

    @dp.message(F.photo)
    async def photo_handler(m: Message):
        p = m.photo[-1]
        await _handle_file(m, p.file_id, f"rasm_{p.file_unique_id}.jpg", p.file_size or 0)

    @dp.message(F.text)
    async def text_handler(m: Message):
        text = (m.text or "").strip()
        if not text or text.startswith("/"):
            if text.startswith("/"):
                await m.answer("Noma'lum buyruq. /yordam")
            return
        link = await _link_for(m.from_user.id)
        if not link:
            existing = await db.telegram_links.find_one({"telegram_id": m.from_user.id})
            return await m.answer(NOT_CREATOR if existing else NOT_LINKED)
        await _ai_reply(m, link, text)

    log.info("Telegram bot polling boshlandi.")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, handle_signals=False)
    except Exception as e:
        log.exception(f"Telegram bot xatosi: {e}")


def spawn_telegram_task(loop: asyncio.AbstractEventLoop):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return None
    return loop.create_task(start_telegram_bot())
