"""Pending actions requiring human approval (web + Telegram buttons)."""
import logging
from typing import Optional
from bson import ObjectId

from core.db import get_db, iso_now

log = logging.getLogger("approvals")

ACTION_LABELS = {
    "import_receipt": "Chekni 1C ga yozish",
    "import_receipts_batch": "Cheklarni 1C ga yozish (to'plam)",
    "sync_products": "1C nomenklaturasini sinxronlash",
    "create_product_mapping": "Mahsulot mappingini yaratish",
    "generic": "Operatsiya",
}


def public_action(a: dict) -> dict:
    return {"id": str(a["_id"]), "action_type": a.get("action_type"), "label": ACTION_LABELS.get(a.get("action_type"), a.get("action_type")),
            "description": a.get("description"), "payload": a.get("payload") or {}, "status": a.get("status"), "company_id": a.get("company_id"),
            "result": a.get("result"), "error": a.get("error"), "source": a.get("source"), "created_at": a.get("created_at"),
            "decided_at": a.get("decided_at")}


async def create_action(user_id: str, company_id: Optional[str], action_type: str, description: str, payload: Optional[dict] = None,
                        conversation_id: Optional[str] = None, source: str = "web") -> dict:
    db = get_db()
    doc = {"user_id": user_id, "company_id": company_id, "action_type": action_type, "description": description, "payload": payload or {},
           "conversation_id": conversation_id, "source": source, "status": "pending", "created_at": iso_now(), "updated_at": iso_now()}
    res = await db.pending_actions.insert_one(doc)
    doc["_id"] = res.inserted_id
    return public_action(doc)


async def list_actions(user_id: Optional[str] = None, company_id: Optional[str] = None, status: Optional[str] = "pending", limit=50) -> list:
    db = get_db()
    q = {}
    if user_id: q["user_id"] = user_id
    if company_id: q["company_id"] = company_id
    if status: q["status"] = status
    return [public_action(a) async for a in db.pending_actions.find(q).sort("_id", -1).limit(limit)]


async def _execute(a: dict) -> dict:
    t, p, cid = a.get("action_type"), a.get("payload") or {}, a.get("company_id")
    if t == "import_receipt":
        from services.one_c_service import push_receipt
        return await push_receipt(cid, p["receipt_id"])
    if t == "import_receipts_batch":
        from services.one_c_service import push_receipt
        ok, failed = [], []
        for rid in p.get("receipt_ids") or []:
            try:
                r = await push_receipt(cid, rid); ok.append({"receipt_id": rid, "ref_key": r.get("ref_key")})
            except Exception as e:
                failed.append({"receipt_id": rid, "error": str(e)[:200]})
        return {"ok": not failed, "imported": len(ok), "failed": failed}
    if t == "sync_products":
        from services.one_c_service import sync_products
        return await sync_products(cid)
    if t == "create_product_mapping":
        db = get_db()
        doc = {"company_id": cid, "soliq_name": p.get("soliq_name"), "soliq_mxik": p.get("soliq_mxik"), "one_c_product_id": p.get("one_c_product_id"),
               "one_c_name": p.get("one_c_name"), "created_by": a["user_id"], "active": True, "created_at": iso_now(), "updated_at": iso_now()}
        res = await db.product_mappings.insert_one(doc)
        return {"ok": True, "mapping_id": str(res.inserted_id)}
    return {"ok": True, "note": "Bu operatsiya faqat qayd etildi (avtomatik bajarish yo'q)."}


async def decide_action(action_id: str, approver_id: str, approve: bool, source: str = "web") -> dict:
    db = get_db()
    a = await db.pending_actions.find_one({"_id": ObjectId(action_id)})
    if not a:
        raise ValueError("Amal topilmadi")
    if a.get("status") != "pending":
        return public_action(a)
    if not approve:
        await db.pending_actions.update_one({"_id": a["_id"]}, {"$set": {"status": "rejected", "decided_by": approver_id, "decided_at": iso_now(), "updated_at": iso_now()}})
        await db.audit_logs.insert_one({"who": approver_id, "what": f"Rad etildi: {a.get('description')}", "when": iso_now(), "company_id": a.get("company_id"),
                                        "source": source, "created_at": iso_now(), "updated_at": iso_now()})
        return public_action(await db.pending_actions.find_one({"_id": a["_id"]}))
    await db.pending_actions.update_one({"_id": a["_id"]}, {"$set": {"status": "running", "decided_by": approver_id, "decided_at": iso_now()}})
    try:
        result = await _execute(a)
        status = "done" if result.get("ok", True) else "failed"
        upd = {"status": status, "result": result, "updated_at": iso_now()}
    except Exception as e:
        log.exception("action failed")
        upd = {"status": "failed", "error": str(e)[:800], "updated_at": iso_now()}
    await db.pending_actions.update_one({"_id": a["_id"]}, {"$set": upd})
    await db.audit_logs.insert_one({"who": approver_id, "what": f"Tasdiqlandi ({upd['status']}): {a.get('description')}", "when": iso_now(),
                                    "company_id": a.get("company_id"), "source": source, "new_value": upd.get("result"),
                                    "created_at": iso_now(), "updated_at": iso_now()})
    return public_action(await db.pending_actions.find_one({"_id": a["_id"]}))
