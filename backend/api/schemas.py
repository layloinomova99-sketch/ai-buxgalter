"""Request/response schemas."""
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class RegisterIn(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    full_name: str
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AuthOut(BaseModel):
    token: str
    user: dict


class CompanyIn(BaseModel):
    name: str
    inn: Optional[str] = None
    address: Optional[str] = None
    director: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    inn: Optional[str] = None
    address: Optional[str] = None
    director: Optional[str] = None


class RuleIn(BaseModel):
    category: str
    instruction: str
    structured_rule: Optional[dict] = None
    priority: int = 50
    company_id: Optional[str] = None  # None = global (creator only)
    status: str = "active"


class MappingIn(BaseModel):
    company_id: str
    soliq_name: str
    soliq_mxik: Optional[str] = None
    one_c_product_id: Optional[str] = None
    one_c_name: str


class ProductIn(BaseModel):
    company_id: str
    name: str
    mxik: Optional[str] = None
    unit: Optional[str] = None
    external_one_c_id: Optional[str] = None


class ReceiptIn(BaseModel):
    company_id: str
    source: str = "unknown"
    external_id: Optional[str] = None
    fiscal_id: Optional[str] = None
    receipt_number: Optional[str] = None
    sale_date: Optional[str] = None
    total_amount: float = 0.0
    items: List[dict] = []
    notes: Optional[str] = None


class ChatIn(BaseModel):
    conversation_id: Optional[str] = None
    company_id: Optional[str] = None
    message: str


class UserAccessUpdate(BaseModel):
    access_granted: Optional[bool] = None
    active: Optional[bool] = None
    role: Optional[str] = None
    payment_status: Optional[str] = None
