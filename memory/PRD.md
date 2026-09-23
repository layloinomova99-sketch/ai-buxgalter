# AI BUXGALTER PLATFORMASI — PRD

## Original problem statement (short)
O'zbekiston uchun professional AI-driven Buxgalter platformasi:
- Web + Telegram bot (bitta backend, bitta AI, bitta DB)
- Claude Sonnet 4.6 asosidagi AI Assistant (tool calling, no-hallucination)
- O'zbekiston Soliq tizimi + 1C + ERI/EIMZO + Didox integratsiya (modular adapterlar)
- Ko'p kompaniya (limit 10) + rollar (creator/administrator/observer)
- Creator AI'ni conversational tarzda o'rgatadi (AI Knowledge base)
- Company-level qat'iy izolyatsiya

## Personas
- **Creator (Owner, `layloinomova99@gmail.com`)**: tizim yaratuvchisi. Foydalanuvchilarga access beradi, AI'ni qoidalar orqali o'rgatadi, audit ko'radi.
- **Administrator**: ro'yxatdan o'tgan foydalanuvchi. O'z kompaniyalarini boshqaradi, AI bilan gaplashadi.
- **Observer**: faqat o'qish huquqi.

## Architecture
- Backend: FastAPI + MongoDB (Motor async), modular structure — `core/`, `models/`, `api/`, `services/`, `services/adapters/`.
- Frontend: React + Tailwind + Shadcn UI, Cabinet Grotesk + IBM Plex Sans, emerald primary, light/dark theme.
- AI: `emergentintegrations` LlmChat routed via EMERGENT_LLM_KEY → Anthropic Claude Sonnet 4.6, with 10 tools defined in `services/ai_tools.py`.
- Telegram: aiogram polling task spawned only when `TELEGRAM_BOT_TOKEN` is set.

## What's implemented (2026-09-21)
### Backend
- JWT auth (`/api/auth/register`, `/login`, `/me`) + bcrypt password hashing
- Roles (creator/administrator/observer) + role-based route guards
- Companies CRUD with per-user 10 limit and strict company-level isolation
- Receipts + duplicate detection (external_id, fiscal_id)
- Products (1C catalog mirror)
- Product mappings (Soliq ↔ 1C)
- AI rules (10 categories, priority, scope: company/global) — Creator-only mutations
- AI conversations + messages persistence
- AI agent with 10 tools: get_current_context, list_companies, get_company_receipts, search_product, find_product_mapping, create_product_mapping, list_ai_rules, save_creator_rule, request_approval, get_sync_status
- Creator user management (`/api/creator/users`): access grant/revoke, activate/deactivate, role change
- Audit logs (`/api/audit`)
- Adapter placeholders: Soliq, 1C, EIMZO, Telegram, Didox — no fabricated APIs

### Frontend
- Login + Register (Uzbek UI)
- App shell with sidebar (Dashboard, Kompaniyalar, Cheklar, Mahsulotlar, Mappinglar, Qoidalar, AI Yordamchi, Audit) + Creator section (Foydalanuvchilar)
- Multi-company switcher in top bar
- Empty state onboarding — "Kompaniya qo'shish" (per user request: no seeded companies)
- Dashboard metric cards + company status badges
- Companies page (add/delete)
- Receipts, Products, Mappings, Rules pages with dialogs
- AI Chat with tool-call reveal accordion
- Audit log viewer
- Creator Users panel with switches
- Light/Dark mode toggle

## Test credentials
- Creator: `layloinomova99@gmail.com` / `Creator@2026!Secure`
- New users self-register (no seeded users).

## What's implemented (2026-09-21, phase 2 — Telegram Creator boti + Bilim bazasi)
- Telegram bot @AI_Buxgalter_yordamchisi_bot (aiogram polling ichida backend). FAQAT Creator: `/login email parol` orqali bog'lanadi (`telegram_links` kolleksiyasi), boshqa rollar "Faqat Creator uchun".
- Buyruqlar: /start /yordam /login /chiqish /kompaniya (inline tanlash) /qoidalar /bilim /yangi
- Fayl yuklash (.py .txt .pdf .docx .xlsx .json rasm, 20MB): `services/knowledge.py::ingest_file` → Claude tahlil → `knowledge_docs` + `ai_rules` (source="document"). Fayl saqlanmaydi (tempfile), matn `text_excerpt` sifatida Mongo'da.
- Oddiy matn → `run_agent_turn(source="telegram")`; Creator uchun AI qoidani `save_creator_rule` bilan avtomatik saqlaydi.
- Yangi AI tool: `search_knowledge` (bilim bazasidan qidirish). `save_creator_rule` endi tool ichida rol tekshiradi.
- API: GET/DELETE /api/knowledge, GET /api/knowledge/{id}, POST /api/knowledge/upload (multipart), GET /api/telegram/status — creator-only.
- Frontend: Creator nav → "Bilim bazasi" (/creator/bilim): Telegram holati, web yuklash, hujjatlar ro'yxati, detal dialog (faktlar + qoidalar), o'chirish.
- Test: iteration_3.json — 100% pass.

## What's implemented (2026-09-23, phase 3 — 1C + Soliq cheklar + Tasdiqlash + Ovoz)
- **1C OData adapter** (`services/adapters/one_c_adapter.py`, V129 `OneCBridge` porti): metadata parse, paging, nomenklatura yuklash, chek hujjati tuzilmasini avtomatik aniqlash (Чек ККМ / Отчет о розничных продажах / Реализация), payload qurish, POST, comment-token bo'yicha dublikat tekshiruvi. Clobus ilova URL → OData URL normalizatsiyasi.
- `services/one_c_service.py`: kompaniya bo'yicha ulanish (`one_c_connections`, parol Fernet bilan shifrlangan, kalit = sha256(JWT_SECRET)), test, mahsulot sinxron (`products.external_one_c_id`=Ref_Key), `push_receipt`.
- **Soliq adapter** (`soliq_adapter.py`): my.soliq.uz "Чеклар рўйхати" .xlsx parseri (V129 `_chek_parse_excel` porti). Rasmiy API yo'q — Excel eksport orqali. Qaytarish cheklari o'tkaziladi, dublikat `external_id=soliq:{fm}:{number}`.
- `services/receipts_service.py`: import → `receipts`+`receipt_items`, matching: mapping → MXIK → aniq nom → fuzzy (≥0.85 medium, ≥0.6 taxmin). Qo'lda bog'lash mapping saqlaydi va bir xil nomli qatorlarga qo'llanadi.
- **Tasdiqlash** (`services/approvals.py`, `pending_actions`): import_receipt / import_receipts_batch / sync_products / create_product_mapping. Web `ApprovalsPanel` (Cheklar + AI sahifalarida) va Telegram inline "✅ Tasdiqlash / ❌ Bekor" tugmalari; `/tasdiqlar` buyrug'i.
- AI toollar: `propose_action`, `get_one_c_status`, `get_receipt_details`; `request_approval` ham pending action yaratadi. `run_agent_turn` → `pending_action_ids`.
- **Telegram**: ovozli xabar → ffmpeg (imageio-ffmpeg) ogg→mp3 → OpenAI whisper-1 (Emergent key) → AI; Soliq .xlsx avtomatik aniqlanib cheklar sifatida import qilinadi (aktiv kompaniya kerak).
- API: GET/PUT/DELETE /api/companies/{id}/one-c, POST .../one-c/test, .../one-c/sync-products, POST .../soliq/upload, GET /api/receipts/{id}, POST /api/receipt-items/{id}/match, POST /api/receipts/{id}/rematch, POST .../receipts/import-1c, GET /api/actions, POST /api/actions/{id}/approve|reject.
- Frontend: Kompaniyalar → "1C" dialog; Cheklar → Excel yuklash, moslik ustuni, detal dialog + qo'lda bog'lash, checkbox → "1C ga yozish" → tasdiq paneli.
- Test: iteration_4.json — backend 15/15 pass, frontend pass. Haqiqiy 1C bilan yozish real login/parol bilan sinovdan o'tkazilishi kerak (test 401 qaytardi).

## Backlog / Next phases
### P0 (near-term)
- Soliq: rasmiy API/ERI orqali avtomatik cheklar (hozircha Excel eksport)
- 1C: hisob ustunlari (V129 `_chek_acct_*`), ombor/tashkilot tanlash UI, Отчет rejimida kunlik jamlash
- ERI/EIMZO adapter: encrypted key upload per company (KMS / envelope encryption)
- Streaming AI responses (SSE) — currently non-streaming for MVP

### P1
- Background jobs (sync progress) — Celery / arq
- Receipt line items editor + manual matching UI (side-by-side)
- OCR/document upload
- Payments (subscription tier)

### P2
- Mobile app
- Additional marketplaces
- Bank statement import
- Report exports (Excel/PDF)

## Known deferred items
- CORS uses `*` with credentials — tighten in production.
- `api/routes.py` will be split per-resource as it grows past ~800 lines.
- AI streaming is non-streaming for MVP; SSE upgrade is planned.
