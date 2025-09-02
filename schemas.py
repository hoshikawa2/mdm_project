from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any, Dict

Domain = Literal["customer","product","supplier","financial","address"]
Operation = Literal["normalize","validate","dedupe","consolidate","harmonize","enrich","mask","outlier_check"]

class InputRecord(BaseModel):
    source: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    cpf: Optional[str] = None
    cnpj: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    cep: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country_code: Optional[str] = None

class RequestPayload(BaseModel):
    domain: Domain
    operations: List[Operation]
    policies: Dict[str, Any] = Field(default_factory=dict)
    records: List[InputRecord]

class AddressOut(BaseModel):
    thoroughfare: Optional[str] = None
    house_number: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = None
    complement: Optional[str] = None

class ResponseTemplate(BaseModel):
    record_clean: List[dict] = Field(default_factory=list)
    golden_record: Optional[dict] = None
    matches: List[dict] = Field(default_factory=list)
    harmonization: dict = Field(default_factory=lambda: {"codes": [], "units": []})
    enrichment: List[dict] = Field(default_factory=list)
    issues: List[dict] = Field(default_factory=list)
    actions: List[dict] = Field(default_factory=list)
    pii_masks: dict = Field(default_factory=dict)
    audit_log: List[dict] = Field(default_factory=list)
    confidence: float = 0.0
