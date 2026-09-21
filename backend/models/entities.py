"""All domain models — kept in one file for MVP density."""
from typing import List, Optional
from pydantic import Field, EmailStr
from core.db import BaseDocument


# ---------- Users ----------
class User(BaseDocument):
    email: str
    phone: Optional[str] = None
    full_name: str
    password_hash: str
    role: str = "administrator"  # creator | administrator | observer
    active: bool = True
    access_granted: bool = True  # Creator may revoke
    payment_status: str = "free"  # free | paid


# ---------- Companies ----------
class Company(BaseDocument):
    owner_user_id: str
    name: str
    inn: Optional[str] = None
    address: Optional[str] = None
    director: Optional[str] = None
    eri_status: str = "not_connected"     # not_connected | connected | error
    one_c_status: str = "not_connected"
    soliq_status: str = "not_connected"
    last_sync: Optional[str] = None


class CompanyMember(BaseDocument):
    """Grants a user access to a company (owner is implicit)."""
    company_id: str
    user_id: str
    role_on_company: str = "administrator"  # administrator | observer


# ---------- Connections ----------
class EriConnection(BaseDocument):
    company_id: str
    label: str
    encrypted_key_ref: Optional[str] = None  # placeholder — real key stored encrypted at rest
    status: str = "not_connected"


class OneCConnection(BaseDocument):
    company_id: str
    base_url: Optional[str] = None
    username: Optional[str] = None
    password_ref: Optional[str] = None  # placeholder
    auth_mode: str = "basic"
    firm_id: Optional[str] = None
    status: str = "not_connected"


class SoliqConnection(BaseDocument):
    company_id: str
    workflow_id: Optional[str] = None  # Creator will define workflow later
    status: str = "not_connected"


# ---------- Receipts & Products ----------
class Receipt(BaseDocument):
    company_id: str
    source: str = "unknown"  # nkm | yandex | uzum | terminal | marketplace | unknown
    external_id: Optional[str] = None  # fiskal ID / chek raqami
    fiscal_id: Optional[str] = None
    receipt_number: Optional[str] = None
    sale_date: Optional[str] = None
    total_amount: float = 0.0
    status: str = "received"  # received|parsed|matched|needs_review|approved|imported|posted|failed|duplicate
    raw_payload: Optional[dict] = None
    notes: Optional[str] = None


class ReceiptItem(BaseDocument):
    company_id: str
    receipt_id: str
    name: str
    mxik: Optional[str] = None
    quantity: float = 0.0
    unit: Optional[str] = None
    price: float = 0.0
    amount: float = 0.0
    matched_product_id: Optional[str] = None
    match_confidence: Optional[str] = None  # high|medium|low
    match_reason: Optional[str] = None


class Product(BaseDocument):
    """1C-side product catalog (mirrored)."""
    company_id: str
    name: str
    mxik: Optional[str] = None
    unit: Optional[str] = None
    external_one_c_id: Optional[str] = None


class ProductMapping(BaseDocument):
    company_id: str
    soliq_name: str
    soliq_mxik: Optional[str] = None
    one_c_product_id: Optional[str] = None
    one_c_name: Optional[str] = None
    created_by: str
    active: bool = True


# ---------- AI Knowledge ----------
class AiRule(BaseDocument):
    creator_id: str
    company_id: Optional[str] = None  # None = global
    category: str  # company_rules | accounting_rules | soliq_rules | one_c_rules |
                   # product_mapping_rules | mxik_rules | receipt_rules |
                   # marketplace_rules | integration_rules | creator_instructions
    instruction: str
    structured_rule: Optional[dict] = None
    status: str = "active"  # active | inactive | draft
    priority: int = 50  # 1..100 higher wins
    source: str = "creator"  # creator | inferred | correction
    version: int = 1


class AiConversation(BaseDocument):
    user_id: str
    company_id: Optional[str] = None
    title: str = "Yangi suhbat"


class AiMessage(BaseDocument):
    conversation_id: str
    user_id: str
    company_id: Optional[str] = None
    role: str  # user | assistant | tool
    content: str
    tool_calls: Optional[List[dict]] = None
    tool_name: Optional[str] = None


class AiAction(BaseDocument):
    """Every material decision taken by the AI is recorded here for audit."""
    user_id: str
    company_id: Optional[str] = None
    conversation_id: Optional[str] = None
    tool: str
    arguments: dict
    result_summary: str
    needs_confirmation: bool = False
    confirmed: bool = False


# ---------- Audit ----------
class AuditLog(BaseDocument):
    who: str
    what: str
    when: str = Field(default_factory=lambda: __import__("core.db", fromlist=["iso_now"]).iso_now())
    company_id: Optional[str] = None
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    source: str = "web"  # web | telegram | ai | system
