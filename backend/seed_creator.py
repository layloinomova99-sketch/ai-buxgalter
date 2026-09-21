"""Idempotently ensure the Creator account exists on startup."""
import os
import logging
from core.db import get_db, iso_now
from core.security import hash_password

log = logging.getLogger("seed")


async def ensure_creator():
    email = os.environ.get("CREATOR_EMAIL", "").strip().lower()
    pw = os.environ.get("CREATOR_PASSWORD", "").strip()
    full = os.environ.get("CREATOR_FULL_NAME", "Creator").strip() or "Creator"
    if not email or not pw:
        log.warning("CREATOR_EMAIL / CREATOR_PASSWORD not set; skipping seed.")
        return
    db = get_db()
    existing = await db.users.find_one({"email": email})
    if existing:
        # If role isn't creator, upgrade it (idempotent).
        if existing.get("role") != "creator":
            await db.users.update_one({"_id": existing["_id"]}, {"$set": {"role": "creator", "active": True, "access_granted": True, "updated_at": iso_now()}})
            log.info(f"Seed: existing user {email} upgraded to creator.")
        else:
            log.info(f"Seed: creator {email} already exists.")
        return
    await db.users.insert_one({
        "email": email, "phone": None, "full_name": full,
        "password_hash": hash_password(pw),
        "role": "creator", "active": True, "access_granted": True, "payment_status": "paid",
        "created_at": iso_now(), "updated_at": iso_now(),
    })
    log.info(f"Seed: creator {email} created.")
