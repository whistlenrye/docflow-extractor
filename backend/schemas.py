from pydantic import BaseModel, Field
from typing import List, Optional, Literal

DocumentType = Literal[
    "shipping.commercial_invoice",
    "shipping.packing_list",
    "shipping.bill_of_lading",
    "generic.invoice",
    "generic.claim",
]


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    hs_code: Optional[str] = None
    country_of_origin: Optional[str] = None


class Party(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None


class ExtractionResult(BaseModel):
    doc_type: str
    confidence: float = Field(ge=0, le=1)
    shipper: Optional[Party] = None
    consignee: Optional[Party] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    incoterms: Optional[str] = None
    currency: Optional[str] = None
    line_items: List[LineItem] = []
    subtotal: Optional[float] = None
    freight: Optional[float] = None
    insurance: Optional[float] = None
    total: Optional[float] = None
    raw_text: Optional[str] = None
    warnings: List[str] = []
    model_used: Optional[str] = None
