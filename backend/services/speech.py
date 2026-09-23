"""Speech-to-text via OpenAI whisper-1 (Emergent LLM key). Telegram .ogg is converted to mp3 with bundled ffmpeg."""
import os
import io
import asyncio
import subprocess
from emergentintegrations.llm.openai import OpenAISpeechToText

SUPPORTED = {"mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"}


def _to_mp3(data: bytes) -> bytes:
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    p = subprocess.run([ff, "-loglevel", "error", "-i", "pipe:0", "-f", "mp3", "-ac", "1", "-ar", "16000", "pipe:1"],
                       input=data, capture_output=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg: {p.stderr.decode(errors='ignore')[:200]}")
    return p.stdout


async def transcribe(data: bytes, filename: str = "voice.ogg") -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED:
        data = await asyncio.to_thread(_to_mp3, data)
        filename = "voice.mp3"
    stt = OpenAISpeechToText(api_key=os.environ["EMERGENT_LLM_KEY"])
    f = io.BytesIO(data)
    f.name = filename
    resp = await stt.transcribe(file=f, model="whisper-1", response_format="json",
                                prompt="Buxgalteriya, 1C, Soliq, chek, MXIK, kompaniya haqida o'zbek tilida ko'rsatma.")
    return (getattr(resp, "text", None) or "").strip()
