"""Receipts: Soliq Excel import, product matching (mapping -> MXIK -> name -> fuzzy), manual match."""
import difflib
import logging
from typing import Optional
from bson import ObjectId

from core.db import get_db, iso_now
from services.adapters.soliq_adapter import parse_soliq_excel
from services.adapters.one_c_adapter import norm

log = logging.getLogger("receipts")


def public_receipt(r: dict) -> dict:
    return {"id": str(r["_id"]), "company_id": r.get("company_id"), "source": r.get("source"), "external_id": r.get("external_id"),
            "receipt_number": r.get("receipt_number"), "sale_date": r.get("sale_date"), "total_amount": r.get("total_amount"),
            "status": r.get("status"), "notes": r.get("notes"), "items_total": r.get("items_total", 0), "items_matched": r.get("items_matched", 0),
            "one_c_ref": r.get("one_c_ref"), "created_at": r.get("created_at"), "cash": (r.get("raw_payload") or {}).get("cash"),
            "card": (r.get("raw_payload") or {}).get("card")}


def public_item(i: dict) -> dict:
    return {"id": str(i["_id"]), "receipt_id": i.get("receipt_id"), "name": i.get("name"), "mxik": i.get("mxik"), "quantity": i.get("quantity"),
            "unit": i.get("unit"), "price": i.get("price"), "amount": i.get("amount"), "vat": i.get("vat"),
            "matched_product_id": i.get("matched_product_id"), "matched_product_name": i.get("matched_product_name"),
            "match_confidence": i.get("match_confidence"), "match_reason": i.get("match_reason")}


async def match_item(db, company_id: str, item: dict, products: list, mappings: dict) -> dict:
    """Returns {product_id, product_name, confidence, reason} or empty."""
    name_n = norm(item.get("name"))
    mxik = item.get("mxik") or ""
    m = mappings.get(("name", name_n)) or (mappings.get(("mxik", mxik)) if mxik else None)
    if m and m.get("one_c_product_id"):
        return {"product_id": m["one_c_product_id"], "product_name": m.get("one_c_name"), "confidence": "high", "reason": "Saqlangan mapping"}
    if mxik:
        hits = [p for p in products if p.get("mxik") and p["mxik"] == mxik]
        if len(hits) == 1:
            return {"product_id": str(hits[0]["_id"]), "product_name": hits[0]["name"], "confidence": "high", "reason": f"MXIK {mxik} mos"}
        if len(hits) > 1:
            exact = [p for p in hits if norm(p["name"]) == name_n]
            if exact:
                return {"product_id": str(exact[0]["_id"]), "product_name": exact[0]["name"], "confidence": "high", "reason": "MXIK + nom mos"}
            return {"product_id": str(hits[0]["_id"]), "product_name": hits[0]["name"], "confidence": "medium", "reason": f"MXIK {mxik} bo'yicha {len(hits)} ta nomzod"}
    exact = [p for p in products if norm(p["name"]) == name_n]
    if exact:
        return {"product_id": str(exact[0]["_id"]), "product_name": exact[0]["name"], "confidence": "high", "reason": "Nom to'liq mos"}
    best, best_score = None, 0.0
    for p in products:
        s = difflib.SequenceMatcher(None, name_n, norm(p["name"])).ratio()
        if s > best_score:
            best, best_score = p, s
    if best and best_score >= 0.85:
        return {"product_id": str(best["_id"]), "product_name": best["name"], "confidence": "medium", "reason": f"Nom o'xshash ({int(best_score * 100)}%)"}
    if best and best_score >= 0.6:
        return {"product_id": None, "product_name": best["name"], "confidence": "low", "reason": f"Taxmin: {best['name']} ({int(best_score * 100)}%) — tasdiq kerak"}
    return {"product_id": None, "product_name": None, "confidence": "low", "reason": "Mos mahsulot topilmadi"}


async def rematch_receipt(company_id: str, receipt_id: str) -> dict:
    db = get_db()
    products = [p async for p in db.products.find({"company_id": company_id})]
    mappings = {}
    async for m in db.product_mappings.find({"company_id": company_id, "active": True}):
        if m.get("soliq_name"):
            mappings[("name", norm(m["soliq_name"]))] = m
        if m.get("soliq_mxik"):
            mappings[("mxik", m["soliq_mxik"])] = m
    total = matched = 0
    async for it in db.receipt_items.find({"receipt_id": receipt_id}):
        total += 1
        res = await match_item(db, company_id, it, products, mappings)
        if res.get("product_id"):
            matched += 1
        await db.receipt_items.update_one({"_id": it["_id"]}, {"$set": {
            "matched_product_id": res.get("product_id"), "matched_product_name": res.get("product_name"),
            "match_confidence": res.get("confidence"), "match_reason": res.get("reason"), "updated_at": iso_now()}})
    r = await db.receipts.find_one({"_id": ObjectId(receipt_id)})
    if r and r.get("status") not in ("imported", "approved"):
        status = "matched" if total and matched == total else "needs_review"
        await db.receipts.update_one({"_id": r["_id"]}, {"$set": {"status": status, "items_total": total, "items_matched": matched, "updated_at": iso_now()}})
    else:
        await db.receipts.update_one({"_id": ObjectId(receipt_id)}, {"$set": {"items_total": total, "items_matched": matched}})
    return {"items_total": total, "items_matched": matched}


async def import_soliq_excel(company_id: str, user_id: str, data: bytes, source: str = "web") -> dict:
    db = get_db()
    parsed = parse_soliq_excel(data)
    created, duplicates, ids = 0, 0, []
    for d in parsed["docs"]:
        if await db.receipts.find_one({"company_id": company_id, "external_id": d["token"]}):
            duplicates += 1
            continue
        doc = {"company_id": company_id, "source": "nkm", "external_id": d["token"], "fiscal_id": d["fm"] or None,
               "receipt_number": d["number"], "sale_date": d["dt"].isoformat(), "total_amount": round(d["total"], 2),
               "status": "parsed", "raw_payload": {"cash": round(d["cash"], 2), "card": round(d["card"], 2), "stir": d["stir"], "fm": d["fm"]},
               "imported_by": user_id, "import_source": source, "created_at": iso_now(), "updated_at": iso_now()}
        res = await db.receipts.insert_one(doc)
        rid = str(res.inserted_id)
        for ln in d["lines"]:
            await db.receipt_items.insert_one({"company_id": company_id, "receipt_id": rid, "name": ln["name"], "mxik": ln["mxik"],
                                               "quantity": ln["qty"], "unit": ln["unit"], "price": ln["price"], "amount": ln["amount"],
                                               "vat": ln["vat"], "created_at": iso_now(), "updated_at": iso_now()})
        await rematch_receipt(company_id, rid)
        ids.append(rid); created += 1
    matched_full = await db.receipts.count_documents({"_id": {"$in": [ObjectId(i) for i in ids]}, "status": "matched"}) if ids else 0
    await db.companies.update_one({"_id": ObjectId(company_id)}, {"$set": {"soliq_status": "connected", "updated_at": iso_now()}})
    await db.audit_logs.insert_one({"who": user_id, "what": f"Soliq Excel import: {created} chek, {duplicates} takror", "when": iso_now(),
                                    "company_id": company_id, "source": source, "created_at": iso_now(), "updated_at": iso_now()})
    return {"created": created, "duplicates": duplicates, "matched": matched_full, "needs_review": created - matched_full,
            "skipped": len(parsed["skipped"]), "warnings": parsed["warnings"][:10], "receipt_ids": ids}


async def manual_match(company_id: str, item_id: str, product_id: str, user_id: str, save_mapping: bool = True) -> dict:
    db = get_db()
    it = await db.receipt_items.find_one({"_id": ObjectId(item_id), "company_id": company_id})
    if not it:
        raise ValueError("Qator topilmadi")
    p = await db.products.find_one({"_id": ObjectId(product_id), "company_id": company_id})
    if not p:
        raise ValueError("Mahsulot topilmadi")
    await db.receipt_items.update_one({"_id": it["_id"]}, {"$set": {"matched_product_id": product_id, "matched_product_name": p["name"],
                                                                     "match_confidence": "high", "match_reason": "Qo'lda tasdiqlangan", "updated_at": iso_now()}})
    if save_mapping:
        await db.product_mappings.update_one(
            {"company_id": company_id, "soliq_name": it["name"]},
            {"$set": {"soliq_mxik": it.get("mxik"), "one_c_product_id": product_id, "one_c_name": p["name"], "active": True, "updated_at": iso_now()},
             "$setOnInsert": {"company_id": company_id, "soliq_name": it["name"], "created_by": user_id, "created_at": iso_now()}},
            upsert=True)
        # apply to other unmatched items with same name
        async for other in db.receipt_items.find({"company_id": company_id, "name": it["name"], "matched_product_id": None}):
            await db.receipt_items.update_one({"_id": other["_id"]}, {"$set": {"matched_product_id": product_id, "matched_product_name": p["name"],
                                                                                "match_confidence": "high", "match_reason": "Saqlangan mapping", "updated_at": iso_now()}})
            await rematch_receipt(company_id, other["receipt_id"])
    return await rematch_receipt(company_id, it["receipt_id"])
