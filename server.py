"""AI BUXGALTER PLATFORMASI — main FastAPI app."""
import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from core.db import close_db
from api.routes import router as api_router
from seed_creator import ensure_creator
from services.adapters.telegram_adapter import spawn_telegram_task


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("app")

app = FastAPI(title="AI Buxgalter", version="0.1.0", redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# ---------- Frontend (React build) — bitta serverdan xizmat ko'rsatish ----------
from fastapi import HTTPException
from fastapi.responses import FileResponse

FRONTEND_DIR = Path(os.environ.get("FRONTEND_BUILD_DIR", ROOT_DIR.parent / "frontend" / "build")).resolve()

if (FRONTEND_DIR / "index.html").exists():
    log.info(f"Frontend: {FRONTEND_DIR}")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(404, "Not Found")
        f = (FRONTEND_DIR / full_path).resolve()
        if full_path and f.is_file() and FRONTEND_DIR in f.parents:
            return FileResponse(f)
        return FileResponse(FRONTEND_DIR / "index.html")  # React Router yo'llari (/cheklar, /ai, ...)


@app.on_event("startup")
async def _on_startup():
    try:
        await ensure_creator()
    except Exception as e:
        log.exception(f"Creator seed error: {e}")
    try:
        loop = asyncio.get_event_loop()
        spawn_telegram_task(loop)
    except Exception as e:
        log.warning(f"Telegram bot spawn failed: {e}")


@app.on_event("shutdown")
async def _on_shutdown():
    close_db()
