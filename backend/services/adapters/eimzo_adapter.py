"""EIMZO / ERI adapter placeholder — real keys stored encrypted at rest."""


class EimzoAdapter:
    def __init__(self, encrypted_key_ref: str | None = None):
        self.encrypted_key_ref = encrypted_key_ref

    async def status(self) -> dict:
        return {"ok": bool(self.encrypted_key_ref), "note": "ERI faol bo'lishi uchun Creator kalitni yuklashi kerak."}
