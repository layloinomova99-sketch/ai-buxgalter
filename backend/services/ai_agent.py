"""AI Accounting Assistant — Claude Sonnet 4.6 with tool calling.

Non-hallucination principle: when Creator has not defined workflows,
the AI must respond that the rule is not defined and ask for clarification.
"""
import os
import json
from typing import Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage

from core.db import get_db, iso_now
from services.ai_tools import AI_TOOL_SCHEMAS, dispatch_tool


AI_PROVIDER = os.environ.get("AI_MODEL_PROVIDER", "anthropic")
AI_MODEL = os.environ.get("AI_MODEL_NAME", "claude-sonnet-4-6")
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


SYSTEM_PROMPT_UZ = """Sen — AI BUXGALTER, O'zbekiston uchun mo'ljallangan aqlli buxgalteriya yordamchisisan.

Muhim qoidalar:
1. Sen platformaning ichki biznes-logikasini biladigan AI Accounting Assistantsan — oddiy ChatGPT emas.
2. HECH QACHON o'zingdan API endpoint, Soliq/1C hujjat nomlari, qonun yoki accounting policy o'ylab topma.
3. Ma'lumot yetarli emas bo'lsa: "Bu operatsiyani avtomatik bajarish uchun ma'lumot yetarli emas. Iltimos, Creator qoidasini qo'shing." deb tushuntir.
4. Har qanday moliyaviy/1C-ga yozish operatsiyasidan avval `request_approval` toolini chaqir.
5. Kompaniya konteksti aniq bo'lmasa, `get_current_context` toolini chaqir yoki foydalanuvchidan aniqlashtir.
6. Creator qoidalarini avval `list_ai_rules` bilan tekshirib chiq — ular ustuvor.
7. Mahsulot matching qilishda avval `find_product_mapping`, keyin MXIK bo'yicha `search_product`, keyin nom bo'yicha qidir. Noaniqlik yuqori bo'lsa foydalanuvchidan so'ra.
8. Barcha javoblar O'zbek tilida, aniq va professional bo'lsin.
9. 1C, Soliq, EIMZO, integratsiya haqida texnik savol bo'lsa, avval `search_knowledge` tooli bilan Creator yuklagan hujjatlardan qidir.

Sening vazifang: foydalanuvchining savolini tushun, kerakli toolni tanla, natijani strukturali tarzda tushuntir.
"""


def build_chat(session_id: str, extra_context: Optional[str] = None) -> LlmChat:
    system = SYSTEM_PROMPT_UZ
    if extra_context:
        system += "\n\n---\nJoriy kontekst:\n" + extra_context
    chat = (
        LlmChat(api_key=EMERGENT_KEY, session_id=session_id, system_message=system)
        .with_model(AI_PROVIDER, AI_MODEL)
        .with_tools(AI_TOOL_SCHEMAS, tool_choice="auto")
    )
    return chat


async def run_agent_turn(user_id: str, conversation_id: str, company_id: Optional[str], user_text: str, source: str = "web") -> dict:
    """Non-streaming single turn (for MVP simplicity). Records messages + actions."""
    db = get_db()

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
    context_lines = [f"user_id: {user_id}", f"kanal: {source}"]
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

    chat = build_chat(session_id=conversation_id, extra_context="\n".join(context_lines))

    tool_trace = []
    response = await chat.send_message_with_tools(UserMessage(text=user_text))

    # Loop while there are tool calls
    guard = 0
    while response.tool_calls and guard < 6:
        guard += 1
        for tc in response.tool_calls:
            try:
                args = tc.arguments if isinstance(tc.arguments, dict) else json.loads(tc.arguments or "{}")
            except Exception:
                args = {}
            result = await dispatch_tool(
                name=tc.name,
                arguments=args,
                user_id=user_id,
                company_id=company_id,
                conversation_id=conversation_id,
            )
            tool_trace.append({"tool": tc.name, "arguments": args, "result": result})
            chat.add_tool_result(tc.id, json.dumps(result, default=str))
        response = await chat.send_message_with_tools()

    final_text = getattr(response, "content", None) or ""

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

    return {"content": final_text, "tool_trace": tool_trace}
