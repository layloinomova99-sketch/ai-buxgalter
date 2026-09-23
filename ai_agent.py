"""AI Accounting Assistant — Claude (Anthropic API) with tool calling.

Non-hallucination principle: when Creator has not defined workflows,
the AI must respond that the rule is not defined and ask for clarification.
"""
import os
import json
from typing import Optional

from core.db import get_db, iso_now
from services.ai_tools import AI_TOOL_SCHEMAS, dispatch_tool
from services import llm

TOOLS = llm.to_anthropic_tools(AI_TOOL_SCHEMAS)
HISTORY_LIMIT = 20  # suhbatning oxirgi nechta xabari AI'ga beriladi


SYSTEM_PROMPT_UZ = """Sen — AI BUXGALTER, O'zbekiston uchun mo'ljallangan aqlli buxgalteriya yordamchisisan.

Muhim qoidalar:
1. Sen platformaning ichki biznes-logikasini biladigan AI Accounting Assistantsan — oddiy ChatGPT emas.
2. HECH QACHON o'zingdan API endpoint, Soliq/1C hujjat nomlari, qonun yoki accounting policy o'ylab topma.
3. Ma'lumot yetarli emas bo'lsa: "Bu operatsiyani avtomatik bajarish uchun ma'lumot yetarli emas. Iltimos, Creator qoidasini qo'shing." deb tushuntir.
4. Har qanday 1C-ga yozish / sinxronlash operatsiyasi uchun `propose_action` toolini chaqir — u tasdiq tugmalarini chiqaradi; o'zing bajarma.
5. Kompaniya konteksti aniq bo'lmasa, `get_current_context` toolini chaqir yoki foydalanuvchidan aniqlashtir.
6. Creator qoidalarini avval `list_ai_rules` bilan tekshirib chiq — ular ustuvor.
7. Mahsulot matching qilishda avval `find_product_mapping`, keyin MXIK bo'yicha `search_product`, keyin nom bo'yicha qidir. Noaniqlik yuqori bo'lsa foydalanuvchidan so'ra.
8. Barcha javoblar O'zbek tilida, aniq va professional bo'lsin.
9. 1C, Soliq, EIMZO, integratsiya haqida texnik savol bo'lsa, avval `search_knowledge` tooli bilan Creator yuklagan hujjatlardan qidir.
10. Cheklar Soliq (my.soliq.uz) "Чеклар рўйхати" Excel fayli orqali yuklanadi; 1C ulanishi kompaniya sozlamalarida (URL+login) o'rnatiladi. Foydalanuvchi so'rasa shu yo'lni tushuntir.

Sening vazifang: foydalanuvchining savolini tushun, kerakli toolni tanla, natijani strukturali tarzda tushuntir.
"""


def build_system(extra_context: Optional[str] = None) -> str:
    system = SYSTEM_PROMPT_UZ
    if extra_context:
        system += "\n\n---\nJoriy kontekst:\n" + extra_context
    return system


async def _history(db, conversation_id: str, user_id: str) -> list:
    """Oldingi xabarlar (faqat matn) — AI suhbatni eslab qolishi uchun."""
    rows = [m async for m in db.ai_messages.find({"conversation_id": conversation_id, "user_id": user_id}).sort("_id", -1).limit(HISTORY_LIMIT)]
    msgs = []
    for m in reversed(rows):
        role = "user" if m.get("role") == "user" else "assistant"
        text = (m.get("content") or "").strip()
        if not text:
            continue
        if msgs and msgs[-1]["role"] == role:
            msgs[-1]["content"] += "\n\n" + text
        else:
            msgs.append({"role": role, "content": text})
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    return msgs


async def run_agent_turn(user_id: str, conversation_id: str, company_id: Optional[str], user_text: str, source: str = "web") -> dict:
    """Non-streaming single turn (for MVP simplicity). Records messages + actions."""
    db = get_db()

    history = await _history(db, conversation_id, user_id)

    # Persist user message
    await db.ai_messages.insert_one({
        "conversation_id": conversation_id,
        "user_id": user_id,
        "company_id": company_id,
        "role": "user",
        "content": user_text,
        "source": source,
        "created_at": iso_now(),
        "updated_at": iso_now(),
    })

    # Build session context
    from datetime import datetime, timedelta, timezone
    now_tk = datetime.now(timezone(timedelta(hours=5)))  # Asia/Tashkent (UTC+5, DST yo'q)
    context_lines = [
        f"Joriy sana va vaqt (Toshkent): {now_tk.strftime('%Y-%m-%d %H:%M')} — 'bugun', 'kecha', 'shu oy' kabi so'zlarni FAQAT shu sanaga nisbatan hisobla. "
        f"Ma'lumotlardagi eng so'nggi sanani 'bugun' deb olma.",
        f"user_id: {user_id}", f"kanal: {source}",
    ]
    from bson import ObjectId
    try:
        u = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        u = None
    if u and u.get("role") == "creator":
        context_lines.append(
            "Foydalanuvchi roli: CREATOR. U seni o'rgatishi mumkin. Agar u qoida, ko'rsatma, ish tartibi yoki "
            "'shunday qil / bundan keyin' kabi tushuntirish bersa — DARHOL `save_creator_rule` toolini chaqirib saqla "
            "(kategoriya va aniq instruction bilan), keyin nimani saqlaganingni qisqa tasdiqlab ayt. Savol bo'lsa — javob ber."
        )
    if company_id:
        context_lines.append(f"active_company_id: {company_id}")
    else:
        context_lines.append("active_company_id: TANLANMAGAN")

    system = build_system("\n".join(context_lines))
    if history and history[-1]["role"] == "user":
        history[-1]["content"] += "\n\n" + user_text
        messages = history
    else:
        messages = history + [{"role": "user", "content": user_text}]

    tool_trace = []
    response = await llm.create(system, messages, TOOLS)

    # Tool chaqiruvlari tugaguncha davom etamiz
    guard = 0
    while response.stop_reason == "tool_use" and guard < 6:
        guard += 1
        messages.append({"role": "assistant", "content": [llm.block_to_dict(b) for b in response.content]})
        results = []
        for b in response.content:
            if b.type != "tool_use":
                continue
            args = b.input if isinstance(b.input, dict) else {}
            result = await dispatch_tool(
                name=b.name,
                arguments=args,
                user_id=user_id,
                company_id=company_id,
                conversation_id=conversation_id,
            )
            tool_trace.append({"tool": b.name, "arguments": args, "result": result})
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(result, default=str, ensure_ascii=False)[:50000]})
        messages.append({"role": "user", "content": results})
        response = await llm.create(system, messages, TOOLS)

    final_text = llm.text_of(response)

    await db.ai_messages.insert_one({
        "conversation_id": conversation_id,
        "user_id": user_id,
        "company_id": company_id,
        "role": "assistant",
        "content": final_text,
        "tool_calls": tool_trace,
        "created_at": iso_now(),
        "updated_at": iso_now(),
    })

    pending = [t["result"]["action_id"] for t in tool_trace if t.get("tool") in ("request_approval", "propose_action") and t.get("result", {}).get("action_id")]
    return {"content": final_text, "tool_trace": tool_trace, "pending_action_ids": pending}
