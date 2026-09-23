# Serverga joylash (Railway) — qadamma-qadam

Loyiha bitta Docker konteynerda ishlaydi: sayt + API + Telegram bot.
Kerak bo'ladi: **MongoDB Atlas** (bepul), **Anthropic API kaliti** (pullik, ishlatganingizcha), **Railway** (~$5/oy).

## 1. MongoDB Atlas (baza) — bepul
1. https://www.mongodb.com/cloud/atlas/register — ro'yxatdan o'ting.
2. **Create** → **M0 (Free)** → region: Frankfurt yoki yaqinrog'i → Create.
3. **Database Access** → Add New Database User → login/parol o'ylab toping (eslab qoling).
4. **Network Access** → Add IP Address → **Allow access from anywhere** (0.0.0.0/0).
5. **Database** → **Connect** → **Drivers** → ulanish satrini nusxalang:
   `mongodb+srv://LOGIN:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
   `<password>` o'rniga 3-qadamdagi parolni yozing.

## 2. Anthropic API kaliti (AI uchun)
1. https://console.anthropic.com — kiring.
2. **Billing** → balansni to'ldiring (masalan $10).
3. **API Keys** → Create Key → nusxalang (`sk-ant-...`). Hech kimga bermang.

## 3. Railway (server)
1. https://railway.com — **GitHub bilan kiring**.
2. **New Project** → **Deploy from GitHub repo** → `ai-buxgalter` ni tanlang.
   Railway `Dockerfile`ni o'zi topadi.
3. Servis → **Variables** → **Raw Editor** → `.env.example` dagi qatorlarni qo'yib, qiymatlarni to'ldiring:
   - `MONGO_URL` — 1-bosqichdagi satr
   - `JWT_SECRET` — 40+ tasodifiy belgi (masalan parol generatoridan). **Keyin o'zgartirmang** — 1C parollari shu bilan shifrlanadi.
   - `ANTHROPIC_API_KEY` — 2-bosqichdagi kalit
   - `CREATOR_PASSWORD` — **yangi, kuchli** parol (eskisi GitHub tarixida ochiq qolgan)
   - `TELEGRAM_BOT_TOKEN` — @BotFather'dan (bot kerak bo'lsa)
4. **Settings** → **Networking** → **Generate Domain** → sayt manzili chiqadi (`...up.railway.app`).
5. **Deployments** oynasida build tugashini kuting (5–8 daqiqa). Manzilni ochib, Creator bilan kiring.

## Muhim eslatmalar
- **Baza yangi bo'ladi.** Emergent'dagi ma'lumotlar (kompaniyalar, qoidalar, cheklar) avtomatik ko'chmaydi — kompaniyalarni qayta qo'shing, 1C ulanishini qayta kiriting, qoidalarni qayta yozing yoki bilim bazasiga faylni qayta yuklang.
- **Telegram bot** bir vaqtda faqat bitta serverda ishlay oladi. Emergent'dagi nusxa hali ishlayotgan bo'lsa, "Conflict: terminated by other getUpdates" xatosi chiqadi — Emergent'dagisini to'xtating.
- **Render** ham bo'ladi (Dockerfile bir xil), lekin bepul tarifda server 15 daqiqa ishlatilmasa uxlab qoladi va Telegram bot to'xtaydi — pullik (Starter) tarif kerak.
- Ovozli xabarlar uchun ixtiyoriy `OPENAI_API_KEY` (whisper-1). Bo'lmasa, bot "matn bilan yozing" deydi.
- Kodni yangilash: GitHub `main`ga yangi commit → Railway o'zi qayta joylaydi.
