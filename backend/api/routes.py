"""All API routes. Uses /api prefix via APIRouter in server.py."""
import os
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.db import get_db, iso_now
from core.security import (
    hash_password, verify_password, create_token,
    current_user_payload, require_role,
)
from api.schemas import (
    RegisterIn, LoginIn, AuthOut, CompanyIn, CompanyUpdate,
    RuleIn, MappingIn, ProductIn, ReceiptIn, ChatIn, UserAccessUpdate,
)
from services.ai_agent import run_agent_turn

router = APIRouter(prefix="/api")


# ---------- helpers ----------
async def _log_audit(db, who: str, what: str, company_id: Optional[str] = None, new_value: Optional[dict] = None, old_value: Optional[dict] = None, source: str = "web"):
    await db.audit_logs.insert_one({
        "who": who, "what": what, "when": iso_now(),
        "company_id": company_id, "old_value": old_value, "new_value": new_value,
        "source": source, "created_at": iso_now(), "updated_at": iso_now(),
    })


async def _user_by_id(db, uid: str) -> Optional[dict]:
    try:
        return await db.users.find_one({"_id": ObjectId(uid)})
    except Exception:
        return None


async def _company_visible_to(db, user: dict, company_id: str) -> Optional[dict]:
    """Company is visible if user is owner OR member OR user is creator."""
    try:
        c = await db.companies.find_one({"_id": ObjectId(company_id)})
    except Exception:
        return None
    if not c:
        return None
    uid = str(user["_id"])
    if user.get("role") == "creator":
        return c
    if c.get("owner_user_id") == uid:
        return c
    member = await db.company_members.find_one({"company_id": company_id, "user_id": uid})
    if member:
        return c
    return None


def _public_user(u: dict) -> dict:
    return {
        "id": str(u["_id"]), "email": u.get("email"), "phone": u.get("phone"),
        "full_name": u.get("full_name"), "role": u.get("role"),
        "active": u.get("active", True), "access_granted": u.get("access_granted", True),
        "payment_status": u.get("payment_status", "free"),
        "created_at": u.get("created_at"),
    }


def _public_company(c: dict) -> dict:
    return {
        "id": str(c["_id"]), "name": c.get("name"), "inn": c.get("inn"),
        "address": c.get("address"), "director": c.get("director"),
        "eri_status": c.get("eri_status", "not_connected"),
        "one_c_status": c.get("one_c_status", "not_connected"),
        "soliq_status": c.get("soliq_status", "not_connected"),
        "last_sync": c.get("last_sync"), "owner_user_id": c.get("owner_user_id"),
        "created_at": c.get("created_at"),
    }


# ---------- health ----------
@router.get("/")
async def root():
    return {"status": "ok", "service": "AI Buxgalter API"}


# ---------- auth ----------
@router.post("/auth/register", response_model=AuthOut)
async def register(payload: RegisterIn):
    db = get_db()
    if await db.users.find_one({"email": payload.email.lower()}):
        raise HTTPException(400, "Bu email allaqachon ro'yxatdan o'tgan")
    doc = {
        "email": payload.email.lower(), "phone": payload.phone, "full_name": payload.full_name,
        "password_hash": hash_password(payload.password),
        "role": "administrator", "active": True, "access_granted": True, "payment_status": "free",
        "created_at": iso_now(), "updated_at": iso_now(),
    }
    res = await db.users.insert_one(doc)
    doc["_id"] = res.inserted_id
    token = create_token(sub=str(res.inserted_id), role=doc["role"])
    await _log_audit(db, who=str(res.inserted_id), what="user_registered", new_value={"email": doc["email"]})
    return {"token": token, "user": _public_user(doc)}


@router.post("/auth/login", response_model=AuthOut)
async def login(payload: LoginIn):
    db = get_db()
    u = await db.users.find_one({"email": payload.email.lower()})
    if not u or not verify_password(payload.password, u.get("password_hash", "")):
        raise HTTPException(401, "Email yoki parol xato")
    if not u.get("active", True) or not u.get("access_granted", True):
        raise HTTPException(403, "Sizga hozircha kirish ruxsati berilmagan. Creator bilan bog'laning.")
    token = create_token(sub=str(u["_id"]), role=u.get("role", "administrator"))
    await _log_audit(db, who=str(u["_id"]), what="user_login")
    return {"token": token, "user": _public_user(u)}


@router.get("/auth/me")
async def me(payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    if not u:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    return _public_user(u)


# ---------- companies ----------
@router.get("/companies")
async def list_my_companies(payload: dict = Depends(current_user_payload)):
    db = get_db()
    uid = payload["sub"]
    owned = db.companies.find({"owner_user_id": uid})
    seen, rows = set(), []
    async for c in owned:
        seen.add(str(c["_id"])); rows.append(_public_company(c))
    async for m in db.company_members.find({"user_id": uid}):
        cid = m.get("company_id")
        if cid in seen: continue
        try:
            cdoc = await db.companies.find_one({"_id": ObjectId(cid)})
            if cdoc:
                seen.add(cid); rows.append(_public_company(cdoc))
        except Exception:
            pass
    return {"companies": rows, "count": len(rows), "limit": 10}


@router.post("/companies")
async def create_company(payload_in: CompanyIn, payload: dict = Depends(current_user_payload)):
    db = get_db()
    uid = payload["sub"]
    count = await db.companies.count_documents({"owner_user_id": uid})
    if count >= 10:
        raise HTTPException(400, "Kompaniyalar limiti: 10 ta. Adminstrator bilan bog'laning.")
    doc = {
        "owner_user_id": uid, "name": payload_in.name, "inn": payload_in.inn,
        "address": payload_in.address, "director": payload_in.director,
        "eri_status": "not_connected", "one_c_status": "not_connected", "soliq_status": "not_connected",
        "created_at": iso_now(), "updated_at": iso_now(),
    }
    res = await db.companies.insert_one(doc); doc["_id"] = res.inserted_id
    await _log_audit(db, who=uid, what="company_created", company_id=str(res.inserted_id), new_value={"name": doc["name"]})
    return _public_company(doc)


@router.patch("/companies/{company_id}")
async def update_company(company_id: str, payload_in: CompanyUpdate, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    if not u: raise HTTPException(401)
    c = await _company_visible_to(db, u, company_id)
    if not c: raise HTTPException(404, "Kompaniya topilmadi")
    updates = {k: v for k, v in payload_in.model_dump(exclude_unset=True).items() if v is not None}
    if not updates: return _public_company(c)
    updates["updated_at"] = iso_now()
    await db.companies.update_one({"_id": ObjectId(company_id)}, {"$set": updates})
    c2 = await db.companies.find_one({"_id": ObjectId(company_id)})
    await _log_audit(db, who=str(u["_id"]), what="company_updated", company_id=company_id, new_value=updates)
    return _public_company(c2)


@router.delete("/companies/{company_id}")
async def delete_company(company_id: str, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    if not u: raise HTTPException(401)
    c = await _company_visible_to(db, u, company_id)
    if not c: raise HTTPException(404)
    if c.get("owner_user_id") != str(u["_id"]) and u.get("role") != "creator":
        raise HTTPException(403, "Faqat egasi yoki Creator o'chira oladi")
    await db.companies.delete_one({"_id": ObjectId(company_id)})
    await db.company_members.delete_many({"company_id": company_id})
    await _log_audit(db, who=str(u["_id"]), what="company_deleted", company_id=company_id)
    return {"deleted": True}


# ---------- receipts ----------
@router.get("/companies/{company_id}/receipts")
async def list_receipts(company_id: str, status: Optional[str] = None, limit: int = 100, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    if not await _company_visible_to(db, u, company_id): raise HTTPException(404)
    q = {"company_id": company_id}
    if status: q["status"] = status
    rows = []
    async for r in db.receipts.find(q).sort("_id", -1).limit(limit):
        rows.append({
            "id": str(r["_id"]), "source": r.get("source"), "external_id": r.get("external_id"),
            "receipt_number": r.get("receipt_number"), "sale_date": r.get("sale_date"),
            "total_amount": r.get("total_amount"), "status": r.get("status"),
            "notes": r.get("notes"), "created_at": r.get("created_at"),
        })
    return {"receipts": rows, "count": len(rows)}


@router.post("/receipts")
async def create_receipt(payload_in: ReceiptIn, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    if not await _company_visible_to(db, u, payload_in.company_id): raise HTTPException(404)
    # Duplicate check
    if payload_in.external_id or payload_in.fiscal_id:
        dup_q = {"company_id": payload_in.company_id}
        if payload_in.external_id: dup_q["external_id"] = payload_in.external_id
        if payload_in.fiscal_id: dup_q["fiscal_id"] = payload_in.fiscal_id
        dup = await db.receipts.find_one(dup_q)
        if dup:
            return {"duplicate": True, "id": str(dup["_id"]), "message": "Bu chek oldin qayta ishlangan."}
    doc = {
        "company_id": payload_in.company_id, "source": payload_in.source,
        "external_id": payload_in.external_id, "fiscal_id": payload_in.fiscal_id,
        "receipt_number": payload_in.receipt_number, "sale_date": payload_in.sale_date,
        "total_amount": payload_in.total_amount, "status": "parsed",
        "notes": payload_in.notes, "created_at": iso_now(), "updated_at": iso_now(),
    }
    res = await db.receipts.insert_one(doc)
    for it in (payload_in.items or []):
        it_doc = {"company_id": payload_in.company_id, "receipt_id": str(res.inserted_id), **it,
                  "created_at": iso_now(), "updated_at": iso_now()}
        await db.receipt_items.insert_one(it_doc)
    await _log_audit(db, who=str(u["_id"]), what="receipt_created", company_id=payload_in.company_id, new_value={"receipt_id": str(res.inserted_id)})
    return {"id": str(res.inserted_id), "status": "parsed"}


# ---------- products ----------
@router.get("/companies/{company_id}/products")
async def list_products(company_id: str, q: Optional[str] = None, limit: int = 100, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    if not await _company_visible_to(db, u, company_id): raise HTTPException(404)
    mongo_q = {"company_id": company_id}
    if q: mongo_q["name"] = {"$regex": q, "$options": "i"}
    rows = []
    async for p in db.products.find(mongo_q).limit(limit):
        rows.append({"id": str(p["_id"]), "name": p.get("name"), "mxik": p.get("mxik"), "unit": p.get("unit"), "external_one_c_id": p.get("external_one_c_id")})
    return {"products": rows, "count": len(rows)}


@router.post("/products")
async def create_product(payload_in: ProductIn, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    if not await _company_visible_to(db, u, payload_in.company_id): raise HTTPException(404)
    if u.get("role") == "observer": raise HTTPException(403, "Observer o'zgartira olmaydi")
    doc = payload_in.model_dump(); doc["created_at"] = iso_now(); doc["updated_at"] = iso_now()
    res = await db.products.insert_one(doc)
    return {"id": str(res.inserted_id)}


# ---------- mappings ----------
@router.get("/companies/{company_id}/mappings")
async def list_mappings(company_id: str, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    if not await _company_visible_to(db, u, company_id): raise HTTPException(404)
    rows = []
    async for m in db.product_mappings.find({"company_id": company_id}).sort("_id", -1):
        rows.append({
            "id": str(m["_id"]), "soliq_name": m.get("soliq_name"), "soliq_mxik": m.get("soliq_mxik"),
            "one_c_name": m.get("one_c_name"), "one_c_product_id": m.get("one_c_product_id"),
            "active": m.get("active", True), "created_at": m.get("created_at"),
        })
    return {"mappings": rows, "count": len(rows)}


@router.post("/mappings")
async def create_mapping(payload_in: MappingIn, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    if not await _company_visible_to(db, u, payload_in.company_id): raise HTTPException(404)
    if u.get("role") == "observer": raise HTTPException(403)
    doc = payload_in.model_dump()
    doc.update({"created_by": str(u["_id"]), "active": True, "created_at": iso_now(), "updated_at": iso_now()})
    res = await db.product_mappings.insert_one(doc)
    await _log_audit(db, who=str(u["_id"]), what="mapping_created", company_id=payload_in.company_id, new_value={"soliq": payload_in.soliq_name, "one_c": payload_in.one_c_name})
    return {"id": str(res.inserted_id)}


@router.delete("/mappings/{mapping_id}")
async def delete_mapping(mapping_id: str, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    try:
        m = await db.product_mappings.find_one({"_id": ObjectId(mapping_id)})
    except Exception:
        raise HTTPException(404)
    if not m: raise HTTPException(404)
    if not await _company_visible_to(db, u, m["company_id"]): raise HTTPException(403)
    await db.product_mappings.delete_one({"_id": ObjectId(mapping_id)})
    await _log_audit(db, who=str(u["_id"]), what="mapping_deleted", company_id=m["company_id"])
    return {"deleted": True}


# ---------- AI rules ----------
@router.get("/rules")
async def list_rules(company_id: Optional[str] = None, category: Optional[str] = None, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    q: dict = {"status": "active"}
    if u.get("role") == "creator":
        if company_id: q["$or"] = [{"company_id": company_id}, {"company_id": None}]
    else:
        if not company_id: raise HTTPException(400, "company_id kerak")
        if not await _company_visible_to(db, u, company_id): raise HTTPException(403)
        q["$or"] = [{"company_id": company_id}, {"company_id": None}]
    if category: q["category"] = category
    rows = []
    async for r in db.ai_rules.find(q).sort("priority", -1):
        rows.append({
            "id": str(r["_id"]), "category": r.get("category"), "instruction": r.get("instruction"),
            "structured_rule": r.get("structured_rule"), "priority": r.get("priority", 50),
            "company_id": r.get("company_id"), "status": r.get("status"), "version": r.get("version", 1),
            "created_at": r.get("created_at"),
        })
    return {"rules": rows, "count": len(rows)}


@router.post("/rules", dependencies=[Depends(require_role("creator"))])
async def create_rule(payload_in: RuleIn, payload: dict = Depends(current_user_payload)):
    db = get_db()
    doc = payload_in.model_dump()
    doc.update({"creator_id": payload["sub"], "source": "creator", "version": 1,
                "created_at": iso_now(), "updated_at": iso_now()})
    res = await db.ai_rules.insert_one(doc)
    await _log_audit(db, who=payload["sub"], what="rule_created", new_value={"category": payload_in.category})
    return {"id": str(res.inserted_id)}


@router.patch("/rules/{rule_id}", dependencies=[Depends(require_role("creator"))])
async def update_rule(rule_id: str, payload_in: RuleIn, payload: dict = Depends(current_user_payload)):
    db = get_db()
    try:
        existing = await db.ai_rules.find_one({"_id": ObjectId(rule_id)})
    except Exception: raise HTTPException(404)
    if not existing: raise HTTPException(404)
    updates = payload_in.model_dump()
    updates["version"] = int(existing.get("version", 1)) + 1
    updates["updated_at"] = iso_now()
    await db.ai_rules.update_one({"_id": ObjectId(rule_id)}, {"$set": updates})
    await _log_audit(db, who=payload["sub"], what="rule_updated", new_value=updates)
    return {"updated": True}


@router.delete("/rules/{rule_id}", dependencies=[Depends(require_role("creator"))])
async def delete_rule(rule_id: str, payload: dict = Depends(current_user_payload)):
    db = get_db()
    try:
        await db.ai_rules.delete_one({"_id": ObjectId(rule_id)})
    except Exception: raise HTTPException(404)
    await _log_audit(db, who=payload["sub"], what="rule_deleted")
    return {"deleted": True}


# ---------- AI chat ----------
@router.get("/ai/conversations")
async def list_conversations(payload: dict = Depends(current_user_payload)):
    db = get_db()
    rows = []
    async for c in db.ai_conversations.find({"user_id": payload["sub"]}).sort("_id", -1).limit(50):
        rows.append({"id": str(c["_id"]), "title": c.get("title"), "company_id": c.get("company_id"), "created_at": c.get("created_at")})
    return {"conversations": rows}


@router.post("/ai/conversations")
async def create_conversation(company_id: Optional[str] = None, title: str = "Yangi suhbat", payload: dict = Depends(current_user_payload)):
    db = get_db()
    doc = {"user_id": payload["sub"], "company_id": company_id, "title": title,
           "created_at": iso_now(), "updated_at": iso_now()}
    res = await db.ai_conversations.insert_one(doc)
    return {"id": str(res.inserted_id), "title": title, "company_id": company_id}


@router.get("/ai/conversations/{conv_id}/messages")
async def list_messages(conv_id: str, payload: dict = Depends(current_user_payload)):
    db = get_db()
    rows = []
    async for m in db.ai_messages.find({"conversation_id": conv_id, "user_id": payload["sub"]}).sort("_id", 1):
        rows.append({
            "id": str(m["_id"]), "role": m.get("role"), "content": m.get("content"),
            "tool_calls": m.get("tool_calls"), "created_at": m.get("created_at"),
        })
    return {"messages": rows}


@router.post("/ai/chat")
async def ai_chat(payload_in: ChatIn, payload: dict = Depends(current_user_payload)):
    db = get_db()
    conv_id = payload_in.conversation_id
    if not conv_id:
        res = await db.ai_conversations.insert_one({
            "user_id": payload["sub"], "company_id": payload_in.company_id,
            "title": payload_in.message[:60], "created_at": iso_now(), "updated_at": iso_now(),
        })
        conv_id = str(res.inserted_id)

    # Verify user can access selected company (if any)
    if payload_in.company_id:
        u = await _user_by_id(db, payload["sub"])
        if not await _company_visible_to(db, u, payload_in.company_id):
            raise HTTPException(403, "Kompaniyaga ruxsat yo'q")

    try:
        result = await run_agent_turn(
            user_id=payload["sub"], conversation_id=conv_id,
            company_id=payload_in.company_id, user_text=payload_in.message,
        )
    except Exception as e:
        # Non-hallucination: technical detail to logs, friendly message to user.
        import logging
        logging.getLogger("ai").exception(f"AI xatolik: {e}")
        raise HTTPException(500, "AI bilan bog'lanishda texnik xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

    return {"conversation_id": conv_id, **result}


# ---------- Creator: users management ----------
@router.get("/creator/users", dependencies=[Depends(require_role("creator"))])
async def creator_list_users():
    db = get_db()
    rows = []
    async for u in db.users.find({}).sort("_id", -1):
        cnt = await db.companies.count_documents({"owner_user_id": str(u["_id"])})
        item = _public_user(u); item["companies_count"] = cnt
        rows.append(item)
    return {"users": rows, "count": len(rows)}


@router.patch("/creator/users/{user_id}", dependencies=[Depends(require_role("creator"))])
async def creator_update_user(user_id: str, payload_in: UserAccessUpdate, payload: dict = Depends(current_user_payload)):
    db = get_db()
    updates = {k: v for k, v in payload_in.model_dump(exclude_unset=True).items() if v is not None}
    if not updates: raise HTTPException(400, "Bo'sh yangilanish")
    updates["updated_at"] = iso_now()
    try:
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": updates})
    except Exception: raise HTTPException(404)
    await _log_audit(db, who=payload["sub"], what="user_access_updated", new_value=updates)
    u = await db.users.find_one({"_id": ObjectId(user_id)})
    return _public_user(u)


# ---------- Audit ----------
@router.get("/audit")
async def list_audit(company_id: Optional[str] = None, limit: int = 200, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    q: dict = {}
    if company_id:
        if u.get("role") != "creator" and not await _company_visible_to(db, u, company_id):
            raise HTTPException(403)
        q["company_id"] = company_id
    elif u.get("role") != "creator":
        raise HTTPException(400, "company_id kerak")
    rows = []
    async for a in db.audit_logs.find(q).sort("_id", -1).limit(limit):
        rows.append({
            "id": str(a["_id"]), "who": a.get("who"), "what": a.get("what"),
            "when": a.get("when"), "company_id": a.get("company_id"),
            "new_value": a.get("new_value"), "source": a.get("source"),
        })
    return {"audit_logs": rows, "count": len(rows)}


# ---------- Dashboard stats ----------
@router.get("/companies/{company_id}/stats")
async def company_stats(company_id: str, payload: dict = Depends(current_user_payload)):
    db = get_db()
    u = await _user_by_id(db, payload["sub"])
    if not await _company_visible_to(db, u, company_id): raise HTTPException(404)
    async def _cnt(coll, q): return await db[coll].count_documents(q)
    return {
        "receipts_total": await _cnt("receipts", {"company_id": company_id}),
        "receipts_needs_review": await _cnt("receipts", {"company_id": company_id, "status": "needs_review"}),
        "receipts_imported": await _cnt("receipts", {"company_id": company_id, "status": "imported"}),
        "products_total": await _cnt("products", {"company_id": company_id}),
        "mappings_total": await _cnt("product_mappings", {"company_id": company_id, "active": True}),
        "rules_total": await _cnt("ai_rules", {"$or": [{"company_id": company_id}, {"company_id": None}], "status": "active"}),
    }
