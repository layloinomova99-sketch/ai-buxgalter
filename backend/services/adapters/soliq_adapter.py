"""Soliq adapter — placeholder. Creator will provide workflow & endpoints later."""


class SoliqAdapter:
    def __init__(self, company_id: str, connection: dict | None = None):
        self.company_id = company_id
        self.connection = connection or {}

    async def test_connection(self) -> dict:
        return {"ok": False, "reason": "Creator hali Soliq workflowni sozlamagan."}

    async def fetch_receipts(self, since: str | None = None) -> list[dict]:
        # Intentionally not implemented — returns empty until Creator defines the workflow.
        return []
