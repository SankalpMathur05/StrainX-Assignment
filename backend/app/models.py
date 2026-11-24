"""Shared data contract for the quote comparison engine and API.

Everything the engine, API and frontend exchange is defined here.
`lib/types.ts` mirrors these models for the Next.js frontend — keep them in sync.
Dates travel as ISO strings (YYYY-MM-DD); money is INR unless a field says otherwise.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

DEFAULT_REFERENCE_DATE = Date(2026, 11, 24)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Unit(str, Enum):
    KG = "kg"
    G = "g"
    L = "L"
    ML = "mL"
    PACK = "pack"
    DRUM = "drum"
    UNIT = "unit"


class PricingUnit(str, Enum):
    PER_UNIT = "per_unit"  # per one requisition unit (e.g. per kg if requisition is in kg)
    PER_KG = "per_kg"
    PER_PACK = "per_pack"  # uses pack_size_value + pack_size_unit
    PER_DRUM = "per_drum"  # uses drum_size_kg


class PricingBasis(str, Enum):
    EX_WORKS = "EX_WORKS"
    CIF = "CIF"
    DELIVERED = "DELIVERED"
    PICKUP = "PICKUP"
    UNSPECIFIED = "UNSPECIFIED"


class TaxTreatment(str, Enum):
    EXCLUSIVE_GST = "EXCLUSIVE_GST"
    INCLUSIVE_GST = "INCLUSIVE_GST"
    IMPORT_DUTY_IGST = "IMPORT_DUTY_IGST"
    EXEMPT = "EXEMPT"
    UNSPECIFIED = "UNSPECIFIED"


class CoaStatus(str, Enum):
    EVERY_BATCH = "EVERY_BATCH"
    ON_REQUEST_OR_CONDITIONAL = "ON_REQUEST_OR_CONDITIONAL"
    WITH_MATERIAL = "WITH_MATERIAL"
    MISSING_OR_UNCLEAR = "MISSING_OR_UNCLEAR"


class BrandStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NAMED_UNVERIFIED = "NAMED_UNVERIFIED"
    MISSING = "MISSING"


class SourceChannel(str, Enum):
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    PDF = "PDF"
    PHONE = "PHONE"
    OTHER = "OTHER"


class LeadTimeBasis(str, Enum):
    CALENDAR = "CALENDAR"
    WORKING = "WORKING"  # Mon–Sat; Sundays skipped


class LeadTimeStart(str, Enum):
    PO = "PO"
    PAYMENT = "PAYMENT"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
class Requisition(BaseModel):
    id: str | None = None
    pr_number: str
    date: Date = DEFAULT_REFERENCE_DATE
    requested_by: str = ""
    site: str = "USP Lab, Tamot plant (near Bhopal)"
    item_name: str
    specification: str = ""
    required_quantity: float = Field(gt=0)
    unit: Unit = Unit.KG
    need_by_date: Date = Date(2026, 12, 5)
    approved_budget: float = Field(default=200000, ge=0)  # INR
    coa_mandatory: bool = True
    require_named_brand: bool = False
    quality_notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Quote(BaseModel):
    id: str | None = None
    requisition_id: str | None = None
    label: str = ""  # "A", "B", ...
    supplier_name: str
    supplier_location: str = ""
    source_channel: SourceChannel = SourceChannel.OTHER
    product_description: str = ""

    # Quality
    brand_name: str | None = None
    brand_status: BrandStatus = BrandStatus.MISSING
    coa_status: CoaStatus = CoaStatus.MISSING_OR_UNCLEAR

    # Price
    price: float = Field(ge=0)
    currency: str = "INR"
    fx_rate_to_inr: float = Field(default=1.0, gt=0)  # 84.0 for USD in the seed
    pricing_unit: PricingUnit = PricingUnit.PER_UNIT
    pack_size_value: float | None = None  # pack size; also used to round orders up to whole packs
    pack_size_unit: Unit | None = None
    drum_size_kg: float | None = None  # for PER_DRUM pricing
    pricing_basis: PricingBasis = PricingBasis.UNSPECIFIED

    # Tax (primary scenario + optional alternate scenario when terms are unclear/contradictory)
    tax_treatment: TaxTreatment = TaxTreatment.UNSPECIFIED
    gst_rate_pct: float = 18.0
    alt_tax_treatment: TaxTreatment | None = None
    alt_gst_rate_pct: float | None = None
    customs_duty_pct: float = 12.0  # % of CIF value in INR (imports)
    igst_rate_pct: float = 18.0  # % of (CIF INR + customs duty) (imports)
    clearance_fee_inr: float | None = None  # imports: None -> default 8000
    inland_transport_inr: float | None = None  # imports: None -> default 6500 (port to site)

    # Freight (domestic)
    freight_cost: float | None = 0.0  # INR; None = unknown ("at actual")
    freight_free_above_inr: float | None = None  # freight waived if pre-tax goods value >= this

    # Quantity constraints
    moq_quantity: float | None = None
    moq_unit: Unit | None = None

    # Delivery
    lead_time_min_days: int | None = None
    lead_time_max_days: int | None = None
    lead_time_basis: LeadTimeBasis = LeadTimeBasis.CALENDAR
    lead_time_starts: LeadTimeStart = LeadTimeStart.PO
    transit_days: int = 0  # extra calendar days after dispatch, e.g. Indore -> Tamot

    # Payment
    payment_terms: str = ""
    advance_pct: float = Field(default=0, ge=0, le=100)
    pre_delivery_pct: float = Field(default=0, ge=0, le=100)  # total % paid before goods arrive
    credit_days: int = 0

    # Validity & provenance
    valid_until: Date | None = None
    raw_text: str = ""
    contradictions: list[str] = Field(default_factory=list)
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Weights(BaseModel):
    """Priority sliders, each 0-100. Normalised by their sum when scoring."""

    price: float = Field(default=30, ge=0, le=100)
    delivery: float = Field(default=25, ge=0, le=100)
    payment: float = Field(default=10, ge=0, le=100)
    quality: float = Field(default=35, ge=0, le=100)


class CompareRequest(BaseModel):
    requisition: Requisition
    quotes: list[Quote]
    weights: Weights = Field(default_factory=Weights)
    reference_date: Date | None = None  # None -> settings REFERENCE_DATE (default 2026-11-24)


# ---------------------------------------------------------------------------
# Engine outputs
# ---------------------------------------------------------------------------
class CostBreakdown(BaseModel):
    quantity: float  # in requisition unit
    packs: int | None = None  # number of packs/drums when pack-based
    goods_pre_tax_inr: float  # ex-tax goods value (CIF value for imports)
    customs_duty_inr: float = 0.0  # not recoverable
    recoverable_tax_inr: float = 0.0  # GST / import IGST: potential ITC, subject to valid tax invoice
    freight_inr: float = 0.0
    clearance_inr: float = 0.0
    inland_transport_inr: float = 0.0
    total_landed_inr: float  # cash outflow: everything above added up (unknown freight excluded)
    freight_unknown: bool = False
    unit_cost_pre_tax: float  # goods_pre_tax / required quantity (per requisition unit)
    unit_cost_landed: float  # total_landed / required quantity (per requisition unit)
    unit_cost_landed_per_ordered: float  # total_landed / this breakdown's quantity
    cost_per_kg_pre_tax: float | None = None  # per required kg, when mass-based
    cost_per_kg_landed: float | None = None


class CostScenario(BaseModel):
    name: Literal["primary", "alternate"]
    description: str  # e.g. "GST inclusive @ 18%"
    tax_treatment: TaxTreatment
    gst_rate_pct: float | None = None
    commitment: CostBreakdown  # max(required, MOQ), rounded up to whole packs — drives ranking
    required_only: CostBreakdown  # required qty rounded to packs — "if MOQ waived"


class QuoteCosting(BaseModel):
    comparable: bool = True  # False when units cannot be converted (UNIT_MISMATCH)
    required_quantity: float
    order_quantity: float  # commitment quantity in requisition unit
    moq_applies: bool = False
    scenarios: list[CostScenario] = Field(default_factory=list)  # 1 or 2
    worst_case_index: int = 0  # index into scenarios with the highest commitment landed total
    worst_case_landed_inr: float | None = None
    budget_variance_inr: float | None = None  # worst-case commitment landed - approved budget
    incomplete: bool = False  # some cost component unknown (e.g. freight "at actual")
    notes: list[str] = Field(default_factory=list)


class DeliveryEstimate(BaseModel):
    start_date: Date | None = None  # PO or payment date assumed
    earliest_arrival: Date | None = None
    latest_arrival: Date | None = None
    buffer_days: int | None = None  # need_by - latest_arrival (negative = late)
    on_time: bool | None = None  # latest arrival <= need_by


class Flag(BaseModel):
    code: str
    severity: Severity
    message: str
    question: str | None = None  # supplier clarification question this flag generates


class ScoreBreakdown(BaseModel):
    price: float
    delivery: float
    payment: float
    quality: float
    weighted: float  # sum(w_i * s_i) / sum(w_i)
    penalty: float  # 30 per CRITICAL + 5 per WARNING
    final: float  # weighted - penalty (used for ranking)
    display: float  # final clamped to 0..100


class QuoteAnalysis(BaseModel):
    quote_id: str | None = None
    label: str
    supplier_name: str
    rank: int
    costing: QuoteCosting
    delivery: DeliveryEstimate
    flags: list[Flag]
    critical_count: int
    warning_count: int
    facts: list[str]  # confirmed from the quote text
    assumptions: list[str]  # assumptions the engine made for this quote
    questions: list[str]  # clarification questions for this supplier
    score: ScoreBreakdown


class Recommendation(BaseModel):
    quote_id: str | None = None
    quote_label: str | None = None
    supplier_name: str | None = None
    rationale: str  # plain English, deterministic
    caveats: list[str] = Field(default_factory=list)
    runner_up_label: str | None = None


class CompareResult(BaseModel):
    reference_date: Date
    requisition: Requisition
    weights: Weights
    analyses: list[QuoteAnalysis]  # sorted by rank (1 = best)
    recommendation: Recommendation
    summary_text: str  # WhatsApp/email-ready plain text
    global_assumptions: list[str]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
class ComparisonRunCreate(BaseModel):
    requisition_id: str
    weights: Weights = Field(default_factory=Weights)
    reference_date: Date | None = None
    label: str = ""


class ComparisonRun(BaseModel):
    id: str
    requisition_id: str
    label: str = ""
    weights: Weights
    reference_date: Date
    top_pick_label: str | None = None
    top_pick_supplier: str | None = None
    result: dict[str, Any]  # CompareResult snapshot (JSON)
    created_at: datetime | None = None


class ChatMessage(BaseModel):
    id: str | None = None
    requisition_id: str | None = None
    role: Literal["user", "assistant"]
    content: str
    model: str | None = None
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# AI endpoints
# ---------------------------------------------------------------------------
class ExtractRequest(BaseModel):
    text: str = Field(min_length=1)
    requisition: Requisition | None = None  # context for quote extraction (unit, qty, dates)


class ExtractResponse(BaseModel):
    available: bool  # False when GROQ_API_KEY is missing or the AI call failed
    message: str | None = None  # setup / error message for the user
    fields: dict[str, Any] = Field(default_factory=dict)  # partial Requisition or Quote fields
    missing_fields: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    model_used: str | None = None


class InsightsRequest(BaseModel):
    compare: CompareRequest


class InsightsResponse(BaseModel):
    available: bool
    message: str | None = None
    headline: str = ""
    tradeoffs: list[str] = Field(default_factory=list)
    supplier_questions: dict[str, list[str]] = Field(default_factory=dict)  # keyed by quote label
    ungrounded_numbers: list[str] = Field(default_factory=list)  # numbers in AI text not in calc output
    model_used: str | None = None


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    requisition_id: str | None = None
    message: str = Field(min_length=1)
    compare: CompareRequest
    history: list[ChatTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    available: bool
    message: str | None = None
    reply: str = ""
    ungrounded_numbers: list[str] = Field(default_factory=list)
    model_used: str | None = None


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    groq_configured: bool
    supabase_configured: bool
    storage: Literal["supabase", "local"]
    reference_date: Date
