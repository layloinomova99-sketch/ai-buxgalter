"""1C connection storage (encrypted password), product sync, and receipt push."""
import os
import base64
import hashlib
import logging
from typing import Optional
from bson import ObjectId
from cryptography.fernet import Fernet

from core.db import get_db, iso_now
from services.adapters.one_c_adapter import OneCAdapter, normc

log = logging.getLogger("one_c_service")


def _fernet() -> Fernet:
    key = hashlib.sha256(os.environ["JWT_SECRET"].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(s: str) -> str:
    return _fernet().encrypt(s.encode()).decode() if s else ""


def decrypt(s: str) -> str:
    try:
        return _fernet().decrypt(s.encode()).decode() if s else ""
    except Exception:
        return ""


async def get_connection(company_id: str) -> Optional[dict]:
    return await get_db().one_c_connections.find_one({"company_id": company_id})


def public_connection(c: Optional[dict]) -> dict:
    if not c:
        return {"configured": False, "status": "not_connected"}
    return {"configured": True, "base_url": c.get("base_url"), "username": c.get("username"), "auth_mode": c.get("auth_mode", "basic"),
            "status": c.get("status"), "last_check": c.get("last_check"), "last_error": c.get("last_error"),
            "entities": c.get("entities"), "check_document": c.get("check_document"), "products_synced": c.get("products_synced"),
            "last_products_sync": c.get("last_products_sync"), "has_password": bool(c.get("password_enc"))}


async def adapter_for(company_id: str) -> OneCAdapter:
    c = await get_connection(company_id)
    if not c:
        raise RuntimeError("Bu kompaniya uchun 1C ulanishi sozlanmagan.")
    return OneCAdapter({"base_url": c.get("base_url"), "username": c.get("username"),
                        "password": decrypt(c.get("password_enc", "")), "token": decrypt(c.get("token_enc", "")),
                        "auth_mode": c.get("auth_mode", "basic")})


async def save_connection(company_id: str, base_url: str, username: str, password: Optional[str], auth_mode: str, token: Optional[str]) -> dict:
    db = get_db()
    existing = await get_connection(company_id)
    upd = {"company_id": company_id, "base_url": base_url.strip(), "username": (username or "").strip(),
           "auth_mode": auth_mode or "basic", "updated_at": iso_now()}
    if password:
        upd["password_enc"] = encrypt(password)
    if token:
        upd["token_enc"] = encrypt(token)
    if not existing:
        upd.update({"status": "not_connected", "created_at": iso_now()})
    await db.one_c_connections.update_one({"company_id": company_id}, {"$set": upd}, upsert=True)
    return public_connection(await get_connection(company_id))


async def test_connection(company_id: str) -> dict:
    db = get_db()
    try:
        ad = await adapter_for(company_id)
        h = await ad.health()
    except Exception as e:
        h = {"ok": False, "reason": str(e)}
    upd = {"last_check": iso_now(), "updated_at": iso_now()}
    if h.get("ok"):
        summary = await ad.summary()
        upd.update({"status": "connected", "last_error": None, "entities": summary["entities"],
                    "check_document": summary["check_document"], "structure": summary})
        h["summary"] = summary
    else:
        upd.update({"status": "error", "last_error": h.get("reason")})
    await db.one_c_connections.update_one({"company_id": company_id}, {"$set": upd})
    await db.companies.update_one({"_id": ObjectId(company_id)}, {"$set": {"one_c_status": upd["status"], "updated_at": iso_now()}})
    return h


async def sync_products(company_id: str) -> dict:
    db = get_db()
    ad = await adapter_for(company_id)
    rows = await ad.load_nomenclature()
    if not rows:
        return {"synced": 0, "note": "1C Номенклатура katalogi bo'sh yoki topilmadi."}
    n = 0
    for r in rows:
        await db.products.update_one(
            {"company_id": company_id, "external_one_c_id": r["ref_key"]},
            {"$set": {"name": r["name"], "mxik": r["mxik"] or None, "unit": r["unit"] or None, "code": r["code"], "updated_at": iso_now()},
             "$setOnInsert": {"company_id": company_id, "external_one_c_id": r["ref_key"], "created_at": iso_now()}},
            upsert=True)
        n += 1
    await db.one_c_connections.update_one({"company_id": company_id}, {"$set": {"products_synced": n, "last_products_sync": iso_now()}})
    await db.companies.update_one({"_id": ObjectId(company_id)}, {"$set": {"last_sync": iso_now()}})
    return {"synced": n}


async def build_receipt_payload(ad: OneCAdapter, receipt: dict, items: list) -> tuple:
    """-> (entity, payload, warnings). Requires all items matched to products with external_one_c_id."""
    db = get_db()
    await ad.load_metadata(refresh=True)
    st = ad.check_structure()
    if not st or not st["ok"]:
        raise RuntimeError("1C da chek hujjati (Чек ККМ / Отчет о розничных продажах / Реализация) tuzilmasi topilmadi.")
    warns = []
    from datetime import datetime
    dt = receipt.get("sale_date") or iso_now()
    try:
        dts = datetime.fromisoformat(dt.replace("Z", "")).strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        dts = dt[:19]
    raw = receipt.get("raw_payload") or {}
    payload = {st["date"]: dts}
    if st["comment"]:
        payload[st["comment"]] = f"{receipt.get('external_id')} | soliq chek №{receipt.get('receipt_number')} | naqd {raw.get('cash', 0):,.0f}, karta {raw.get('card', 0):,.0f} | AI BUXGALTER".replace(",", " ")
    if st["amount"]:
        payload[st["amount"]] = round(float(receipt.get("total_amount") or 0), 2)
    if st["operation"]:
        members = ad.enum_members_for(st["etype"], st["operation"])
        pick = [x for x in members if "розничныймагазин" in normc(x)] or [x for x in members if "продаж" in normc(x) and "возврат" not in normc(x)]
        if pick:
            payload[st["operation"]] = pick[0]
        else:
            warns.append(f"{st['operation']} qiymati aniqlanmadi")
    for prop, aliases in ((st["organization"], ["Организации", "Organizations"]), (st["warehouse"], ["Склады", "Warehouses"])):
        if not prop:
            continue
        _, rows = await ad.load_catalog(aliases, 200)
        if len(rows) == 1:
            payload[prop] = rows[0].get("Ref_Key")
        elif rows and aliases[0] == "Организации":
            inn = "".join(ch for ch in str((await db.companies.find_one({"_id": ObjectId(receipt["company_id"])}) or {}).get("inn") or "") if ch.isdigit())
            hit = [r for r in rows if inn and inn in " ".join(str(v) for v in r.values())]
            if hit:
                payload[prop] = hit[0].get("Ref_Key")
            else:
                warns.append(f"{prop}: {len(rows)} ta tashkilot, INN bo'yicha topilmadi — bo'sh qoladi")
        elif rows:
            payload[prop] = rows[0].get("Ref_Key")
            warns.append(f"{prop}: {len(rows)} tadan birinchisi tanlandi")
    t = st["t"]
    vat_members = ad.enum_members_for(st["table"][1], t["vat_rate"]) if t.get("vat_rate") else []
    lines = []
    for i, it in enumerate(items, 1):
        pid = it.get("matched_product_id")
        prod = await db.products.find_one({"_id": ObjectId(pid)}) if pid else None
        if not prod or not prod.get("external_one_c_id"):
            raise RuntimeError(f"'{it.get('name')}' mahsuloti 1C nomenklaturasiga bog'lanmagan.")
        row = {"LineNumber": str(i), t["nom"]: prod["external_one_c_id"], t["qty"]: it.get("quantity"), t["price"]: it.get("price"), t["sum"]: it.get("amount")}
        vat = it.get("vat")
        if t.get("vat_sum") and vat is not None:
            row[t["vat_sum"]] = round(vat, 2)
        if t.get("vat_rate"):
            m = ad.vat_member(vat_members, vat, float(it.get("amount") or 0))
            if m:
                row[t["vat_rate"]] = m
        lines.append(row)
    payload[st["table"][0]] = lines
    if st["pay"] and st["pay"].get("sum") and float(raw.get("card") or 0) > 0:
        payload[st["pay"]["nav"]] = [{"LineNumber": "1", st["pay"]["sum"]: round(float(raw["card"]), 2)}]
    return st["entity"], payload, warns


async def push_receipt(company_id: str, receipt_id: str) -> dict:
    db = get_db()
    r = await db.receipts.find_one({"_id": ObjectId(receipt_id), "company_id": company_id})
    if not r:
        raise RuntimeError("Chek topilmadi")
    if r.get("status") == "imported":
        return {"ok": True, "already": True, "ref_key": r.get("one_c_ref")}
    items = [i async for i in db.receipt_items.find({"receipt_id": receipt_id})]
    ad = await adapter_for(company_id)
    entity, payload, warns = await build_receipt_payload(ad, r, items)
    st = ad.check_structure()
    if st.get("comment") and r.get("external_id"):
        dup = await ad.find_by_comment_token(entity, st["comment"], r["external_id"])
        if dup:
            await db.receipts.update_one({"_id": r["_id"]}, {"$set": {"status": "imported", "one_c_ref": dup, "one_c_entity": entity, "notes": "1C da allaqachon mavjud", "updated_at": iso_now()}})
            return {"ok": True, "already": True, "ref_key": dup, "warnings": warns}
    try:
        res = await ad.create_document(entity, payload)
    except Exception as e:
        await db.receipts.update_one({"_id": r["_id"]}, {"$set": {"status": "failed", "notes": str(e)[:500], "updated_at": iso_now()}})
        raise
    ref = (res.get("Ref_Key") if isinstance(res, dict) else None) or ""
    if not ref:
        await db.receipts.update_one({"_id": r["_id"]}, {"$set": {"status": "failed", "notes": f"Ref_Key yo'q: {str(res)[:300]}", "updated_at": iso_now()}})
        raise RuntimeError(f"1C Ref_Key qaytarmadi: {str(res)[:200]}")
    await db.receipts.update_one({"_id": r["_id"]}, {"$set": {"status": "imported", "one_c_ref": ref, "one_c_entity": entity, "imported_at": iso_now(), "updated_at": iso_now()}})
    return {"ok": True, "ref_key": ref, "entity": entity, "warnings": warns}
