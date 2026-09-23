# AI BUXGALTER — bitta konteyner: React frontend + FastAPI backend (+ Telegram bot)
# Railway / Render / istalgan Docker server uchun.

# ---- 1) Frontend build ----
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile --network-timeout 600000
COPY frontend/ ./
ENV CI=false GENERATE_SOURCEMAP=false REACT_APP_BACKEND_URL=""
RUN yarn build

# ---- 2) Backend ----
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/build /app/frontend/build
ENV FRONTEND_BUILD_DIR=/app/frontend/build
# Railway/Render PORT ni o'zi beradi
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
