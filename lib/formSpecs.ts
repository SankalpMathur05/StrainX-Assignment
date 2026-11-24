// Field specs and defaults for the requisition form and the quote editor.
// Defaults mirror backend/app/models.py so an untouched field means "use the engine default".
import {
  BRAND_STATUS_OPTIONS,
  COA_OPTIONS,
  LEAD_BASIS_OPTIONS,
  LEAD_START_OPTIONS,
  PRICING_BASIS_OPTIONS,
  PRICING_UNIT_OPTIONS,
  SOURCE_OPTIONS,
  TAX_OPTIONS,
  UNIT_OPTIONS,
} from "@/lib/labels";
import type { FieldGroup } from "@/lib/forms";
import type { Quote, Requisition } from "@/lib/types";

// ---------------------------------------------------------------------------
// Requisition
// ---------------------------------------------------------------------------
export const DEFAULT_SITE = "USP Lab, Tamot plant (near Bhopal)";

export const REQUISITION_DEFAULTS: Requisition = {
  pr_number: "",
  date: "2026-11-24",
  requested_by: "",
  site: DEFAULT_SITE,
  item_name: "",
  specification: "",
  required_quantity: 0,
  unit: "kg",
  need_by_date: "2026-12-05",
  approved_budget: 200000,
  coa_mandatory: true,
  require_named_brand: false,
  quality_notes: "",
};

type RequisitionKey = keyof Requisition & string;

export const REQUISITION_GROUPS: FieldGroup<RequisitionKey>[] = [
  {
    title: "Request",
    fields: [
      { key: "pr_number", label: "PR number", kind: "text", required: true },
      { key: "date", label: "PR date", kind: "date", required: true },
      { key: "requested_by", label: "Requested by", kind: "text" },
      { key: "site", label: "Delivery site", kind: "text" },
    ],
  },
  {
    title: "Item",
    fields: [
      { key: "item_name", label: "Item name", kind: "text", required: true },
      { key: "required_quantity", label: "Required quantity", kind: "number", required: true, min: 0.0001 },
      { key: "unit", label: "Unit", kind: "select", options: UNIT_OPTIONS },
      { key: "specification", label: "Specification", kind: "textarea", wide: true },
    ],
  },
  {
    title: "Deadline, budget & quality",
    fields: [
      { key: "need_by_date", label: "Need by", kind: "date", required: true },
      { key: "approved_budget", label: "Approved budget (Rs)", kind: "number", min: 0 },
      { key: "coa_mandatory", label: "CoA mandatory with every batch", kind: "bool" },
      { key: "require_named_brand", label: "Named brand required", kind: "bool" },
      { key: "quality_notes", label: "Quality notes", kind: "textarea", wide: true },
    ],
  },
];

// ---------------------------------------------------------------------------
// Quote
// ---------------------------------------------------------------------------
export const USD_FX_DEFAULT = 84;

export const QUOTE_DEFAULTS: Quote = {
  label: "",
  supplier_name: "",
  supplier_location: "",
  source_channel: "OTHER",
  product_description: "",
  brand_name: null,
  brand_status: "MISSING",
  coa_status: "MISSING_OR_UNCLEAR",
  price: 0,
  currency: "INR",
  fx_rate_to_inr: 1,
  pricing_unit: "per_unit",
  pack_size_value: null,
  pack_size_unit: null,
  drum_size_kg: null,
  pricing_basis: "UNSPECIFIED",
  tax_treatment: "UNSPECIFIED",
  gst_rate_pct: 18,
  alt_tax_treatment: null,
  alt_gst_rate_pct: null,
  customs_duty_pct: 12,
  igst_rate_pct: 18,
  clearance_fee_inr: null,
  inland_transport_inr: null,
  freight_cost: 0,
  freight_free_above_inr: null,
  moq_quantity: null,
  moq_unit: null,
  lead_time_min_days: null,
  lead_time_max_days: null,
  lead_time_basis: "CALENDAR",
  lead_time_starts: "PO",
  transit_days: 0,
  payment_terms: "",
  advance_pct: 0,
  pre_delivery_pct: 0,
  credit_days: 0,
  valid_until: null,
  raw_text: "",
  contradictions: [],
  notes: "",
};

type QuoteKey = keyof Quote & string;

export const QUOTE_GROUPS: FieldGroup<QuoteKey>[] = [
  {
    title: "Supplier & source",
    fields: [
      { key: "supplier_name", label: "Supplier name", kind: "text", required: true },
      { key: "label", label: "Label", kind: "text", hint: "Blank = next letter (A, B, …)" },
      { key: "supplier_location", label: "Location", kind: "text" },
      { key: "source_channel", label: "Received via", kind: "select", options: SOURCE_OPTIONS },
      { key: "product_description", label: "Product as quoted", kind: "text", wide: true },
    ],
  },
  {
    title: "Product & quality",
    fields: [
      { key: "brand_name", label: "Brand", kind: "textOrNull", hint: "Blank = not named" },
      { key: "brand_status", label: "Brand status", kind: "select", options: BRAND_STATUS_OPTIONS },
      { key: "coa_status", label: "Certificate of Analysis", kind: "select", options: COA_OPTIONS },
    ],
  },
  {
    title: "Price",
    fields: [
      { key: "price", label: "Price", kind: "number", required: true, min: 0 },
      { key: "currency", label: "Currency", kind: "text", hint: "e.g. INR, USD" },
      { key: "fx_rate_to_inr", label: "FX rate to INR", kind: "number", min: 0.0001, hint: "Auto 84 for USD" },
      { key: "pricing_unit", label: "Price is", kind: "select", options: PRICING_UNIT_OPTIONS },
      { key: "pack_size_value", label: "Pack size", kind: "numberOrNull", min: 0 },
      { key: "pack_size_unit", label: "Pack size unit", kind: "selectOrNull", options: UNIT_OPTIONS },
      { key: "drum_size_kg", label: "Drum size (kg)", kind: "numberOrNull", min: 0, hint: "For per-drum prices" },
      { key: "pricing_basis", label: "Pricing basis", kind: "select", options: PRICING_BASIS_OPTIONS },
    ],
  },
  {
    title: "Tax",
    fields: [
      { key: "tax_treatment", label: "Tax treatment", kind: "select", options: TAX_OPTIONS },
      { key: "gst_rate_pct", label: "GST rate %", kind: "number", min: 0, max: 100 },
      {
        key: "alt_tax_treatment",
        label: "Alternate tax reading",
        kind: "selectOrNull",
        options: TAX_OPTIONS,
        hint: "When terms are unclear or contradictory",
      },
      { key: "alt_gst_rate_pct", label: "Alternate GST rate %", kind: "numberOrNull", min: 0, max: 100 },
      { key: "customs_duty_pct", label: "Customs duty % (imports)", kind: "number", min: 0, max: 100 },
      { key: "igst_rate_pct", label: "IGST % (imports)", kind: "number", min: 0, max: 100 },
      { key: "clearance_fee_inr", label: "Clearance fee (Rs)", kind: "numberOrNull", min: 0, hint: "Blank = default Rs 8,000" },
      { key: "inland_transport_inr", label: "Port-to-site transport (Rs)", kind: "numberOrNull", min: 0, hint: "Blank = default Rs 6,500" },
    ],
  },
  {
    title: "Freight & MOQ",
    fields: [
      { key: "freight_cost", label: "Freight (Rs)", kind: "freight", min: 0 },
      { key: "freight_free_above_inr", label: "Free freight above (Rs)", kind: "numberOrNull", min: 0 },
      { key: "moq_quantity", label: "Minimum order qty", kind: "numberOrNull", min: 0 },
      { key: "moq_unit", label: "MOQ unit", kind: "selectOrNull", options: UNIT_OPTIONS },
    ],
  },
  {
    title: "Delivery",
    fields: [
      { key: "lead_time_min_days", label: "Lead time min (days)", kind: "numberOrNull", integer: true, min: 0 },
      { key: "lead_time_max_days", label: "Lead time max (days)", kind: "numberOrNull", integer: true, min: 0 },
      { key: "lead_time_basis", label: "Counted in", kind: "select", options: LEAD_BASIS_OPTIONS },
      { key: "lead_time_starts", label: "Clock starts", kind: "select", options: LEAD_START_OPTIONS },
      { key: "transit_days", label: "Extra transit days", kind: "number", integer: true, min: 0 },
    ],
  },
  {
    title: "Payment",
    fields: [
      { key: "payment_terms", label: "Payment terms (as written)", kind: "text", wide: true },
      { key: "advance_pct", label: "Advance %", kind: "number", min: 0, max: 100 },
      { key: "pre_delivery_pct", label: "Paid before delivery %", kind: "number", min: 0, max: 100, hint: "Advance + against documents" },
      { key: "credit_days", label: "Credit days", kind: "number", integer: true, min: 0 },
    ],
  },
  {
    title: "Validity & notes",
    fields: [
      { key: "valid_until", label: "Valid until", kind: "dateOrNull", hint: "Blank = not stated" },
      { key: "contradictions", label: "Contradictions (one per line)", kind: "lines", wide: true },
      { key: "notes", label: "Notes & interpretations", kind: "textarea", wide: true },
      { key: "raw_text", label: "Original quote text", kind: "textarea", wide: true },
    ],
  },
];
