"""1C / OData adapter — placeholder that preserves the shape of the legacy OneCBridge."""


class OneCAdapter:
    def __init__(self, connection: dict | None = None):
        self.connection = connection or {}

    async def test_connection(self) -> dict:
        if not self.connection.get("base_url"):
            return {"ok": False, "reason": "1C base_url sozlanmagan"}
        return {"ok": False, "reason": "Ulanish sozlamalari tekshirilmagan (placeholder)."}

    async def list_products(self) -> list[dict]:
        return []

    async def create_document(self, payload: dict) -> dict:
        return {"ok": False, "reason": "1C yozish adapteri hali faol emas."}
