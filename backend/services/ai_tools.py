"""AI tool schemas + dispatcher. The AI can only affect the system through these tools."""
from typing import Optional
from bson import ObjectId
from core.db import get_db, iso_now


AI_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_context",
            "description": "Joriy foydalanuvchi va tanlangan kompaniya kontekstini qaytaradi.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_companies",
            "description": "Foydalanuvchining barcha kompaniyalarini qaytaradi.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_receipts",
            "description": "Joriy kompaniyaning cheklarini qaytaradi (oxirgi N ta).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Nechta chek olish (default 20)"},
                    "status": {"type": "string", "description": "Filter status (optional)"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_product",
            "description": "1C mahsulotlar katalogidan nom yoki MXIK bo'yicha qidirish.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "mxik": {"type": "string"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_product_mapping",
            "description": "Soliq mahsulot nomi/MXIK bo'yicha oldindan saqlangan mappingni qidiradi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "soliq_name": {"type": "string"},
                    "mxik": {"type": "string"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_product_mapping",
            "description": "Soliq mahsulotini 1C mahsulotiga bog'laydigan mapping yaratadi. Confirmation talab qiladi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "soliq_name": {"type": "string"},
                    "soliq_mxik": {"type": "string"},
                    "one_c_product_id": {"type": "string"},
                    "one_c_name": {"type": "string"}
                },
                "required": ["soliq_name", "one_c_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_ai_rules",
            "description": "Creator tomonidan saqlangan qoidalarni qaytaradi (kompaniya + global).",
            "parameters": {
                "type": "object",
                "properties": {"category": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_creator_rule",
            "description": "Creator uchun yangi AI qoidasini saqlaydi. Faqat Creator chaqira oladi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "instruction": {"type": "string"},
                    "structured_rule": {"type": "object"},
                    "priority": {"type": "integer"},
                    "scope": {"type": "string", "enum": ["global", "company"]},
                },
                "required": ["category", "instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_approval",
            "description": "Muhim moliyaviy operatsiyani bajarishdan avval foydalanuvchidan tasdiqlash so'raydi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string"},
                    "description": {"type": "string"},
                    "payload": {"type": "object"}
                },
                "required": ["action_type", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sync_status",
            "description": "Kompaniyaning ERI, Soliq va 1C ulanish holatini qaytaradi.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Creator yuklagan hujjatlar (bilim bazasi) ichidan kalit so'z bo'yicha qidiradi: 1C, Soliq, EIMZO skriptlari, yo'riqnomalar.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_one_c_status",
            "description": "Joriy kompaniyaning 1C OData ulanish holati, topilgan chek hujjati tuzilmasi va sinxronlangan mahsulotlar soni.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_receipt_details",
            "description": "Bitta chekning qatorlari va ularning 1C mahsulotlariga mosligi (matching) haqida to'liq ma'lumot.",
            "parameters": {"type": "object", "properties": {"receipt_id": {"type": "string"}}, "required": ["receipt_id"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_action",
            "description": "Foydalanuvchi tasdig'ini talab qiluvchi operatsiyani navbatga qo'yadi (Tasdiqlash/Bekor tugmalari ko'rsatiladi). action_type: import_receipt (payload: receipt_id), import_receipts_batch (payload: receipt_ids[]), sync_products, create_product_mapping (payload: soliq_name, soliq_mxik, one_c_product_id, one_c_name).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "enum": ["import_receipt", "import_receipts_batch", "sync_products", "create_product_mapping"]},
                    "description": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["action_type", "description"],
            },
        },
    },
]


async def _require_company(company_id: Optional[str]) -> Optional[str]:
    return company_id


async def dispatch_tool(name: str, arguments: dict, user_id: str, company_id: Optional[str], conversation_id: str) -> dict:
    db = get_db()

    async def _log_action(tool: str, args: dict, summary: str, needs_conf: bool = False):
        await db.ai_actions.insert_one({
            "user_id": user_id,
            "company_id": company_id,
            "conversation_id": conversation_id,
            "tool": tool,
            "arguments": args,
            "result_summary": summary,
            "needs_confirmation": needs_conf,
            "confirmed": False,
            "created_at": iso_now(),
            "updated_at": iso_now(),
        })

    if name == "get_current_context":
        return {"user_id": user_id, "active_company_id": company_id, "note": "Kompaniya tanlanmagan bo'lsa, foydalanuvchidan so'rang."}

    if name == "list_companies":
        cur = db.company_members.find({"user_id": user_id})
        member_ids = [m async for m in cur]
        owned = db.companies.find({"owner_user_id": user_id})
        rows = []
        seen = set()
        async for c in owned:
            cid = str(c["_id"])
            if cid in seen: continue
            seen.add(cid)
            rows.append({"id": cid, "name": c.get("name"), "inn": c.get("inn"), "eri": c.get("eri_status"), "one_c": c.get("one_c_status"), "soliq": c.get("soliq_status")})
        for m in member_ids:
            try:
                cdoc = await db.companies.find_one({"_id": ObjectId(m["company_id"])})
                if cdoc:
                    cid = str(cdoc["_id"])
                    if cid in seen: continue
                    seen.add(cid)
                    rows.append({"id": cid, "name": cdoc.get("name"), "inn": cdoc.get("inn")})
            except Exception:
                pass
        return {"companies": rows, "count": len(rows)}

    if name == "get_company_receipts":
        if not company_id:
            return {"error": "Kompaniya tanlanmagan. Iltimos, foydalanuvchidan qaysi kompaniya ekanini so'rang."}
        limit = int(arguments.get("limit") or 20)
        q = {"company_id": company_id}
        if arguments.get("status"):
            q["status"] = arguments["status"]
        rows = []
        async for r in db.receipts.find(q).sort("_id", -1).limit(limit):
            rows.append({
                "id": str(r["_id"]),
                "source": r.get("source"),
                "receipt_number": r.get("receipt_number"),
                "sale_date": r.get("sale_date"),
                "total_amount": r.get("total_amount"),
                "status": r.get("status"),
                "items_total": r.get("items_total"), "items_matched": r.get("items_matched"),
            })
        return {"receipts": rows, "count": len(rows)}

    if name == "search_product":
        if not company_id:
            return {"error": "Kompaniya tanlanmagan."}
        q = {"company_id": company_id}
        if arguments.get("mxik"):
            q["mxik"] = arguments["mxik"]
        elif arguments.get("query"):
            q["name"] = {"$regex": arguments["query"], "$options": "i"}
        rows = []
        async for p in db.products.find(q).limit(15):
            rows.append({"id": str(p["_id"]), "name": p.get("name"), "mxik": p.get("mxik"), "unit": p.get("unit")})
        return {"products": rows, "count": len(rows), "note": "Agar bo'sh bo'lsa, 1C katalogi hali sinxronlanmagan."}

    if name == "find_product_mapping":
        if not company_id:
            return {"error": "Kompaniya tanlanmagan."}
        q = {"company_id": company_id, "active": True}
        if arguments.get("mxik"):
            q["soliq_mxik"] = arguments["mxik"]
        elif arguments.get("soliq_name"):
            q["soliq_name"] = {"$regex": f"^{arguments['soliq_name']}$", "$options": "i"}
        m = await db.product_mappings.find_one(q)
        if m:
            return {"found": True, "mapping": {"id": str(m["_id"]), "soliq_name": m.get("soliq_name"), "one_c_name": m.get("one_c_name"), "one_c_product_id": m.get("one_c_product_id")}}
        return {"found": False}

    if name == "create_product_mapping":
        if not company_id:
            return {"error": "Kompaniya tanlanmagan."}
        doc = {
            "company_id": company_id,
            "soliq_name": arguments.get("soliq_name"),
            "soliq_mxik": arguments.get("soliq_mxik"),
            "one_c_product_id": arguments.get("one_c_product_id"),
            "one_c_name": arguments.get("one_c_name"),
            "created_by": user_id,
            "active": True,
            "created_at": iso_now(),
            "updated_at": iso_now(),
        }
        res = await db.product_mappings.insert_one(doc)
        await _log_action("create_product_mapping", arguments, f"Mapping yaratildi: {doc['soliq_name']} -> {doc['one_c_name']}", needs_conf=False)
        return {"created": True, "id": str(res.inserted_id)}

    if name == "list_ai_rules":
        q = {"$or": [{"company_id": company_id}, {"company_id": None}]} if company_id else {"company_id": None}
        if arguments.get("category"):
            q["category"] = arguments["category"]
        q["status"] = "active"
        rows = []
        async for r in db.ai_rules.find(q).sort("priority", -1).limit(50):
            rows.append({"id": str(r["_id"]), "category": r.get("category"), "instruction": r.get("instruction"), "priority": r.get("priority"), "scope": "company" if r.get("company_id") else "global"})
        return {"rules": rows, "count": len(rows)}

    if name == "save_creator_rule":
        u = await db.users.find_one({"_id": ObjectId(user_id)})
        if not u or u.get("role") != "creator":
            return {"error": "Faqat Creator qoida saqlay oladi."}
        doc = {
            "creator_id": user_id,
            "company_id": company_id if arguments.get("scope") == "company" else None,
            "category": arguments.get("category"),
            "instruction": arguments.get("instruction"),
            "structured_rule": arguments.get("structured_rule"),
            "priority": int(arguments.get("priority") or 50),
            "status": "active",
            "source": "creator",
            "version": 1,
            "created_at": iso_now(),
            "updated_at": iso_now(),
        }
        res = await db.ai_rules.insert_one(doc)
        await _log_action("save_creator_rule", arguments, f"Yangi qoida: {doc['category']}", needs_conf=False)
        return {"saved": True, "id": str(res.inserted_id)}

    if name == "request_approval":
        from services.approvals import create_action
        act = await create_action(user_id, company_id, "generic", arguments.get("description", ""), arguments.get("payload") or {}, conversation_id, source="ai")
        await _log_action("request_approval", arguments, arguments.get("description", ""), needs_conf=True)
        return {"status": "awaiting_user_confirmation", "action_id": act["id"], "note": "Foydalanuvchiga Tasdiqlash/Bekor tugmalari ko'rsatiladi."}

    if name == "propose_action":
        if not company_id and arguments.get("action_type") != "generic":
            return {"error": "Kompaniya tanlanmagan."}
        from services.approvals import create_action
        act = await create_action(user_id, company_id, arguments.get("action_type"), arguments.get("description", ""), arguments.get("payload") or {}, conversation_id, source="ai")
        await _log_action("propose_action", arguments, arguments.get("description", ""), needs_conf=True)
        return {"status": "awaiting_user_confirmation", "action_id": act["id"], "note": "Foydalanuvchi tasdiqlaganidan keyin bajariladi. Unga tasdiqlash tugmasi ko'rinishini ayt."}

    if name == "get_one_c_status":
        if not company_id:
            return {"error": "Kompaniya tanlanmagan."}
        from services.one_c_service import get_connection, public_connection
        c = public_connection(await get_connection(company_id))
        c["products_in_db"] = await db.products.count_documents({"company_id": company_id})
        return c

    if name == "get_receipt_details":
        from services.receipts_service import public_receipt, public_item
        try:
            r = await db.receipts.find_one({"_id": ObjectId(arguments.get("receipt_id"))})
        except Exception:
            r = None
        if not r or (company_id and r.get("company_id") != company_id):
            return {"error": "Chek topilmadi"}
        items = [public_item(i) async for i in db.receipt_items.find({"receipt_id": str(r["_id"])})]
        return {"receipt": public_receipt(r), "items": items}

    if name == "get_sync_status":
        if not company_id:
            return {"error": "Kompaniya tanlanmagan."}
        c = await db.companies.find_one({"_id": ObjectId(company_id)})
        if not c:
            return {"error": "Kompaniya topilmadi"}
        return {"eri": c.get("eri_status"), "soliq": c.get("soliq_status"), "one_c": c.get("one_c_status"), "last_sync": c.get("last_sync")}

    if name == "search_knowledge":
        from services.knowledge import search_knowledge
        rows = await search_knowledge(arguments.get("query") or "", company_id)
        return {"documents": rows, "count": len(rows), "note": "Bo'sh bo'lsa, Creator hali bu mavzuda hujjat yuklamagan."}

    return {"error": f"Noma'lum tool: {name}"}
