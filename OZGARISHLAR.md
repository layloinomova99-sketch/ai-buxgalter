# Tuzatishlar (2026-09-23)

## Backend
- `GET /api/companies/{id}/receipts` endi `items_total` / `items_matched` qaytaradi — Cheklar sahifasidagi "Moslik" ustuni to'ladi.
- AI Yordamchi har so'rovda joriy Toshkent sana/vaqtini oladi — "bugun" to'g'ri hisoblanadi (veb + Telegram).
- 1C ga yozishda ulanish xatosi (masalan HTTP 401) ham chekni "xato" holatiga o'tkazadi va sababini saqlaydi.
- `GET /api/audit` har bir yozuvga `who_name` (ism/email) qo'shadi.
- Yangi: `POST /api/auth/change-password` (kamida 10 belgi).
- Xavfsizlik: Creator paroli repodagi fayllardan olib tashlandi (PRD.md, test_reports, testlar). Testlar endi `CREATOR_PASSWORD` env'dan o'qiydi.

## Frontend
- AI javoblari Markdown sifatida chiqadi (jadval, qalin, ro'yxat) + "AI o'ylamoqda..." indikatori.
- Audit: Toshkent vaqti, ism, o'zbekcha amal nomlari, o'qiladigan ma'lumot.
- Qoidalar: tahrirlash tugmasi + o'xshash/zid qoidalar ogohlantirishi.
- Foydalanuvchilar: qidiruv, rol filtri, test akkauntlarni yashirish; Creator o'zini o'chira olmaydi.
- Chek tafsiloti: o'zbekcha holat, moslik soni, 1C xato matni.
- 1C dialogi darhol "Yuklanmoqda" bilan ochiladi, oldingi kompaniya ma'lumoti ko'rinmaydi.
- Yuqori panelda parolni o'zgartirish tugmasi (🔑).
- `React.StrictMode` olib tashlandi — API so'rovlari endi ikki marta ketmaydi.

## Serverga ko'chirish uchun (2-bosqich)
- AI endi `emergentintegrations` o'rniga to'g'ridan-to'g'ri **Anthropic API** (`ANTHROPIC_API_KEY`) orqali ishlaydi — Emergent kreditiga bog'liq emas. Yangi fayl: `backend/services/llm.py`.
- AI endi suhbatni eslab qoladi (oldingi 20 ta xabar beriladi) — avval har savol alohida edi.
- Telegram ovozli xabarlar: `OPENAI_API_KEY` (ixtiyoriy).
- `backend/requirements.txt` ixchamlashtirildi (135 → 21 paket), Emergent'ning shaxsiy paketlari olib tashlandi; frontend'dan `@emergentbase/*` olib tashlandi, `yarn.lock` qo'shildi.
- FastAPI endi React build'ni ham beradi — bitta server/bitta domen. `Dockerfile`, `.env.example`, `DEPLOY.md` qo'shildi.
