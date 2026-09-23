"""To'g'ridan-to'g'ri Anthropic (Claude) va OpenAI (Whisper) mijozlari.

Emergent'ning `emergentintegrations` paketi o'rniga — loyiha istalgan serverda
(Render, Railway, VPS) o'z API kalitlaringiz bilan ishlaydi.

Muhit o'zgaruvchilari:
  ANTHROPIC_API_KEY  — majburiy (AI chat va bilim bazasi uchun)
  AI_MODEL_NAME      — ixtiyoriy, default: claude-sonnet-4-6
  OPENAI_API_KEY     — ixtiyoriy, faqat Telegram ovozli xabarlari uchun (whisper-1)
"""
import os
from typing import Optional

from anthropic import AsyncAnthropic

AI_MODEL = os.environ.get("AI_MODEL_NAME", "claude-sonnet-4-6")
MAX_TOKENS = int(os.environ.get("AI_MAX_TOKENS", "4096"))

_client: Optional[AsyncAnthropic] = None


class LLMNotConfigured(RuntimeError):
    pass


def client() -> AsyncAnthropic:
    global _client
    if _client is None:
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise LLMNotConfigured("ANTHROPIC_API_KEY sozlanmagan — AI ishlamaydi.")
        _client = AsyncAnthropic(api_key=key)
    return _client


def to_anthropic_tools(openai_style: list) -> list:
    """OpenAI {"type":"function","function":{...}} -> Anthropic {"name","description","input_schema"}."""
    out = []
    for t in openai_style:
        f = t.get("function", t)
        out.append({
            "name": f["name"],
            "description": f.get("description", ""),
            "input_schema": f.get("parameters") or {"type": "object", "properties": {}},
        })
    return out


async def create(system: str, messages: list, tools: Optional[list] = None, max_tokens: int = MAX_TOKENS):
    kwargs = {"model": AI_MODEL, "max_tokens": max_tokens, "system": system, "messages": messages}
    if tools:
        kwargs["tools"] = tools
    return await client().messages.create(**kwargs)


def text_of(response) -> str:
    return "".join(b.text for b in response.content if getattr(b, "type", "") == "text").strip()


def block_to_dict(b) -> dict:
    """SDK bloklarini keyingi so'rovga qaytarish uchun oddiy dict'ga aylantiradi."""
    if b.type == "text":
        return {"type": "text", "text": b.text}
    if b.type == "tool_use":
        return {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
    return b.model_dump()


async def transcribe(file_obj, prompt: str = "") -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise LLMNotConfigured("Ovozli xabar uchun OPENAI_API_KEY sozlanmagan. Iltimos, matn bilan yozing.")
    from openai import AsyncOpenAI
    resp = await AsyncOpenAI(api_key=key).audio.transcriptions.create(model="whisper-1", file=file_obj, prompt=prompt)
    return (getattr(resp, "text", None) or "").strip()
