"""What we ask the model, and how we read its answers.

Extraction prompts list the target fields straight from the Pydantic models, so they can
never drift from the contract; replies are re-validated field by field on the server.
Insights and chat see only the engine's output and the quote terms, and must not do maths.
"""

from __future__ import annotations

import json
from datetime import date
from enum import Enum
from typing import Annotated, Any, get_args, get_origin

from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from pydantic.fields import FieldInfo

from backend.app.models import ChatTurn, CompareRequest, CompareResult, Quote, Requisition

Message = dict[str, str]

# Set by the server, never by the model.
SERVER_FIELDS = {"id", "requisition_id", "label", "raw_text", "created_at", "updated_at"}
MAX_CHAT_HISTORY = 10  # turns sent back to the model

# Short guidance for fields whose meaning is not obvious from the name.
FIELD_HINTS = {
    "pr_number": "purchase requisition number, e.g. PR-USP-1147",
    "required_quantity": "number, in `unit`",
    "approved_budget": "INR",
    "coa_mandatory": "true if a Certificate of Analysis is required",
    "require_named_brand": "true if unknown / unbranded material is not acceptable",
    "source_channel": "how the quote arrived",
    "brand_status": (
        "NAMED_UNVERIFIED if a brand is named, MISSING if none, VERIFIED only if the text says it is approved"
    ),
    "coa_status": (
        "EVERY_BATCH = CoA with every batch/lot; WITH_MATERIAL = 'CoA will come with material'; "
        "ON_REQUEST_OR_CONDITIONAL = 'on request' / 'if needed'; else MISSING_OR_UNCLEAR"
    ),
    "price": "the quoted rate exactly as written, in `currency`, per `pricing_unit`",
    "currency": "ISO code, e.g. INR, USD",
    "fx_rate_to_inr": "only if the text states an exchange rate",
    "pricing_unit": (
        "per_kg; per_pack (also set pack_size_value + pack_size_unit); per_drum (also set drum_size_kg); "
        "per_unit = per requisition unit"
    ),
    "pack_size_value": "size of one pack/drum/container, e.g. 500 for a 500 g pack",
    "pricing_basis": (
        "EX_WORKS = ex-works/ex-godown; DELIVERED = delivered to site; CIF = cost, insurance, freight to port"
    ),
    "tax_treatment": (
        "EXCLUSIVE_GST = 'GST extra'; INCLUSIVE_GST = 'incl GST'; IMPORT_DUTY_IGST = import, buyer pays duty + IGST"
    ),
    "gst_rate_pct": "e.g. 18 for 'GST @18%'",
    "alt_tax_treatment": "only when the text contradicts itself on tax: the other reading",
    "alt_gst_rate_pct": "GST rate of the other reading",
    "freight_cost": "INR; 0 if free; null if 'at actual' or the amount is not stated but freight is charged",
    "freight_free_above_inr": "order value above which delivery is free",
    "moq_quantity": "minimum order quantity",
    "lead_time_min_days": "days; convert weeks to days (1 week = 7 days)",
    "lead_time_max_days": "days; same as min when a single figure is given",
    "lead_time_basis": "WORKING if the text says working/business days, else CALENDAR",
    "lead_time_starts": "PAYMENT if counted from payment/advance, else PO",
    "transit_days": "extra transport days after dispatch, only if stated",
    "advance_pct": "% paid with the order",
    "pre_delivery_pct": (
        "advance + anything due before goods arrive (e.g. 'against shipping documents'); 100% advance = 100"
    ),
    "credit_days": "days of credit after invoice/delivery",
    "valid_until": "offer validity date",
    "contradictions": "each place where the text contradicts itself, quoted briefly",
    "notes": "one short sentence on anything you had to interpret",
}

_SIMPLE_TYPES: dict[Any, str] = {
    bool: "true/false",
    int: "integer",
    float: "number",
    str: "string",
    date: "date YYYY-MM-DD",
}


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
def extractable_fields(model: type[BaseModel]) -> dict[str, FieldInfo]:
    return {name: info for name, info in model.model_fields.items() if name not in SERVER_FIELDS}


def _type_hint(annotation: Any) -> str:
    args = get_args(annotation)
    if type(None) in args:  # X | None
        inner = next(a for a in args if a is not type(None))
        return f"{_type_hint(inner)} or null"
    if get_origin(annotation) is list:
        return "list of strings"
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return "one of " + " | ".join(member.value for member in annotation)
    return _SIMPLE_TYPES.get(annotation, "string")


def _field_lines(model: type[BaseModel]) -> str:
    lines = []
    for name, info in extractable_fields(model).items():
        hint = FIELD_HINTS.get(name)
        lines.append(f"- {name}: {_type_hint(info.annotation)}" + (f" ({hint})" if hint else ""))
    return "\n".join(lines)


_EXTRACTION_RULES = """\
Rules:
1. Extract only what the text states. Omit any field the text does not state; never guess or use defaults.
2. Use exactly the field names and allowed values listed below.
3. Dates as ISO YYYY-MM-DD. Indian dates are day first: 15/11/2026 means 2026-11-15. \
The reference date (today) is {reference_date}; use it only to resolve dates without a year.
4. Numbers as plain JSON numbers, without commas or currency symbols (Rs 2,27,150 -> 227150).
5. Never calculate totals, taxes, conversions or per-kg prices: copy the quoted rate and its unit.
6. missing_fields: names of important fields the text does not state. \
ambiguities: short notes on anything unclear, assumed or contradictory.
"""

_QUOTE_RULES = """\
7. Payment terms: keep the original wording in payment_terms and map it to advance_pct (paid with the order), \
pre_delivery_pct (advance plus anything due before the goods arrive, e.g. "against shipping documents") \
and credit_days.
8. If the text contradicts itself (e.g. "incl GST" in a message but "GST extra" in a footer), list each \
contradiction in `contradictions`. For tax, put the main message's reading in tax_treatment/gst_rate_pct \
and the other in alt_tax_treatment/alt_gst_rate_pct.
"""

_OUTPUT = 'Return only a JSON object: {"fields": {...}, "missing_fields": [...], "ambiguities": [...]}'


def _extraction_messages(kind: str, model: type[BaseModel], rules: str, user: str) -> list[Message]:
    system = (
        f"You extract structured data from a {kind} pasted by a procurement officer in India.\n"
        f"{_OUTPUT}\n\n{rules}\nFields:\n{_field_lines(model)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def requisition_extraction_messages(text: str, reference_date: date) -> list[Message]:
    rules = _EXTRACTION_RULES.format(reference_date=reference_date.isoformat())
    return _extraction_messages("purchase requisition", Requisition, rules, f"Requisition text:\n<<<\n{text}\n>>>")


def quote_extraction_messages(text: str, requisition: Requisition | None, reference_date: date) -> list[Message]:
    rules = _EXTRACTION_RULES.format(reference_date=reference_date.isoformat()) + _QUOTE_RULES
    user = f"Supplier quote text:\n<<<\n{text}\n>>>"
    if requisition is not None:
        context = requisition.model_dump(
            mode="json", include={"item_name", "specification", "required_quantity", "unit", "need_by_date"}
        )
        user = f"The quote answers this requisition (context only, do not copy it): {_json(context)}\n\n{user}"
    return _extraction_messages("supplier quotation", Quote, rules, user)


def _str_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _validate(info: FieldInfo, value: Any) -> Any:
    """Validate one value against the model field's type and constraints; return it JSON-safe."""
    annotation = Annotated[(info.annotation, *info.metadata)] if info.metadata else info.annotation
    adapter: TypeAdapter[Any] = TypeAdapter(annotation)
    return adapter.dump_python(adapter.validate_python(value), mode="json")


def parse_extraction(raw: dict[str, Any], model: type[BaseModel]) -> tuple[dict[str, Any], list[str], list[str]]:
    """Model reply -> (fields, missing_fields, ambiguities).

    Unknown and server-managed fields are dropped; values that fail validation are dropped
    and reported in ambiguities; required fields that are absent are added to missing_fields.
    """
    allowed = extractable_fields(model)
    raw_fields = raw.get("fields")
    fields: dict[str, Any] = {}
    ambiguities = _str_list(raw.get("ambiguities"))
    for name, value in (raw_fields if isinstance(raw_fields, dict) else {}).items():
        info = allowed.get(name)
        if info is None:
            continue
        try:
            fields[name] = _validate(info, value)
        except ValidationError as exc:
            if value is not None:  # null on a non-nullable field just means "not stated"
                ambiguities.append(f"{name}: ignored {value!r} ({exc.errors()[0]['msg']})")
    missing = [n for n in dict.fromkeys(_str_list(raw.get("missing_fields"))) if n in allowed and n not in fields]
    missing += [n for n, info in allowed.items() if info.is_required() and n not in fields and n not in missing]
    return fields, missing, ambiguities


# ---------------------------------------------------------------------------
# Insights and chat
# ---------------------------------------------------------------------------
_DROP_KEYS = {"raw_text", "summary_text", "id", "quote_id", "requisition_id", "created_at", "updated_at"}


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def compact(value: Any) -> Any:
    """Drop bulky or irrelevant keys and empty values, to keep prompts small."""
    if isinstance(value, dict):
        kept = {k: compact(v) for k, v in value.items() if k not in _DROP_KEYS}
        return {k: v for k, v in kept.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        return [compact(item) for item in value]
    return value


# Quote terms worth showing next to the engine output (tax maths, lead times and payment
# percentages are already in the analyses, as costs, dates and flags).
QUOTE_TERMS = {
    "label", "supplier_name", "supplier_location", "source_channel", "product_description",
    "brand_name", "brand_status", "coa_status", "price", "currency", "fx_rate_to_inr", "pricing_unit",
    "pack_size_value", "pack_size_unit", "pricing_basis", "freight_cost", "freight_free_above_inr",
    "moq_quantity", "moq_unit", "payment_terms", "valid_until", "contradictions", "notes",
}  # fmt: skip


def ai_context(request: CompareRequest, result: CompareResult) -> dict[str, Any]:
    """Everything the model may see, and therefore cite: the engine's output plus the quote terms.

    Kept small (Groq free-tier limits are per-minute tokens): empty values are dropped, the
    "required quantity only" cost is dropped when it equals the commitment cost (no MOQ effect),
    and each flag's question is dropped because the analysis's `questions` list repeats it.
    """
    comparison = result.model_dump(mode="json")
    for analysis in comparison["analyses"]:
        for scenario in analysis["costing"]["scenarios"]:
            if scenario["required_only"] == scenario["commitment"]:
                del scenario["required_only"]
        for flag in analysis["flags"]:
            flag.pop("question", None)
    quotes = [quote.model_dump(mode="json", include=QUOTE_TERMS) for quote in request.quotes]
    return compact({"comparison": comparison, "quotes": quotes})


_NUMBER_RULES = """\
- Use ONLY numbers that appear in the data, copied exactly. You may add Indian digit grouping \
(227150 -> Rs 2,27,150), nothing else.
- Never do arithmetic: no sums, differences, savings, averages, percentages or rounding of your own.
- Landed totals are cash outflow. Recoverable GST/IGST is potential input tax credit, not a saving."""

INSIGHT_SYSTEM = f"""\
You are a senior procurement analyst at a biotech manufacturer in India, briefing a director who has one minute.
You receive JSON from a deterministic comparison engine (landed costs, delivery dates, flags, scores, \
recommendation) plus each supplier's quote terms.
{_NUMBER_RULES}
- Explain the engine's recommendation; never change its ranking.
- Be specific and brief. Plain sentences, no markdown.
Return only a JSON object:
{{"headline": "one sentence: the recommended quote and the main reason",
 "tradeoffs": ["2-4 short sentences on what each alternative gains or risks"],
 "supplier_questions": {{"<quote label>": ["up to 3 questions that most need answering before a PO"]}}}}"""


class InsightsDraft(BaseModel):
    """The JSON shape INSIGHT_SYSTEM asks for."""

    headline: str = Field(min_length=1)
    tradeoffs: list[str] = Field(default_factory=list)
    supplier_questions: dict[str, list[str]] = Field(default_factory=dict)

    def all_text(self) -> str:
        questions = [q for qs in self.supplier_questions.values() for q in qs]
        return "\n".join([self.headline, *self.tradeoffs, *questions])


def insight_messages(context: dict[str, Any]) -> list[Message]:
    return [
        {"role": "system", "content": INSIGHT_SYSTEM},
        {"role": "user", "content": f"Comparison data (JSON):\n{_json(context)}"},
    ]


CHAT_SYSTEM = f"""\
You answer a procurement officer's questions about one purchase requisition and its supplier quotes.
The data below is the only source of truth: the engine's costs, delivery dates, flags, assumptions, \
scores and recommendation, plus each quote's terms.
- Answer only from this data. If the answer is not in it, say "That is not in the data."
{_NUMBER_RULES}
- Be concise: at most 5 short sentences or bullet points. Plain text, no tables."""


def chat_messages(context: dict[str, Any], history: list[ChatTurn], question: str) -> list[Message]:
    system = f"{CHAT_SYSTEM}\n\nData (JSON):\n{_json(context)}"
    turns: list[Message] = [{"role": t.role, "content": t.content} for t in history[-MAX_CHAT_HISTORY:]]
    return [{"role": "system", "content": system}, *turns, {"role": "user", "content": question}]
