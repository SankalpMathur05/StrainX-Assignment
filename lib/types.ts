// Mirrors backend/app/models.py — keep in sync.
// Dates are ISO strings (YYYY-MM-DD); datetimes are ISO strings; money is INR unless stated.

export type Unit = "kg" | "g" | "L" | "mL" | "pack" | "drum" | "unit";
export type PricingUnit = "per_unit" | "per_kg" | "per_pack" | "per_drum";
export type PricingBasis = "EX_WORKS" | "CIF" | "DELIVERED" | "PICKUP" | "UNSPECIFIED";
export type TaxTreatment =
  | "EXCLUSIVE_GST"
  | "INCLUSIVE_GST"
  | "IMPORT_DUTY_IGST"
  | "EXEMPT"
  | "UNSPECIFIED";
export type CoaStatus =
  | "EVERY_BATCH"
  | "ON_REQUEST_OR_CONDITIONAL"
  | "WITH_MATERIAL"
  | "MISSING_OR_UNCLEAR";
export type BrandStatus = "VERIFIED" | "NAMED_UNVERIFIED" | "MISSING";
export type SourceChannel = "EMAIL" | "WHATSAPP" | "PDF" | "PHONE" | "OTHER";
export type LeadTimeBasis = "CALENDAR" | "WORKING";
export type LeadTimeStart = "PO" | "PAYMENT";
export type Severity = "CRITICAL" | "WARNING" | "INFO";

export interface Requisition {
  id?: string | null;
  pr_number: string;
  date: string;
  requested_by: string;
  site: string;
  item_name: string;
  specification: string;
  required_quantity: number;
  unit: Unit;
  need_by_date: string;
  approved_budget: number;
  coa_mandatory: boolean;
  require_named_brand: boolean;
  quality_notes: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface Quote {
  id?: string | null;
  requisition_id?: string | null;
  label: string;
  supplier_name: string;
  supplier_location: string;
  source_channel: SourceChannel;
  product_description: string;
  brand_name: string | null;
  brand_status: BrandStatus;
  coa_status: CoaStatus;
  price: number;
  currency: string;
  fx_rate_to_inr: number;
  pricing_unit: PricingUnit;
  pack_size_value: number | null;
  pack_size_unit: Unit | null;
  drum_size_kg: number | null;
  pricing_basis: PricingBasis;
  tax_treatment: TaxTreatment;
  gst_rate_pct: number;
  alt_tax_treatment: TaxTreatment | null;
  alt_gst_rate_pct: number | null;
  customs_duty_pct: number;
  igst_rate_pct: number;
  clearance_fee_inr: number | null;
  inland_transport_inr: number | null;
  freight_cost: number | null; // null = unknown ("at actual")
  freight_free_above_inr: number | null;
  moq_quantity: number | null;
  moq_unit: Unit | null;
  lead_time_min_days: number | null;
  lead_time_max_days: number | null;
  lead_time_basis: LeadTimeBasis;
  lead_time_starts: LeadTimeStart;
  transit_days: number;
  payment_terms: string;
  advance_pct: number;
  pre_delivery_pct: number;
  credit_days: number;
  valid_until: string | null;
  raw_text: string;
  contradictions: string[];
  notes: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface Weights {
  price: number;
  delivery: number;
  payment: number;
  quality: number;
}

export const DEFAULT_WEIGHTS: Weights = { price: 30, delivery: 25, payment: 10, quality: 35 };

export interface CompareRequest {
  requisition: Requisition;
  quotes: Quote[];
  weights?: Weights;
  reference_date?: string | null;
}

export interface CostBreakdown {
  quantity: number;
  packs: number | null;
  goods_pre_tax_inr: number;
  customs_duty_inr: number;
  recoverable_tax_inr: number;
  freight_inr: number;
  clearance_inr: number;
  inland_transport_inr: number;
  total_landed_inr: number;
  freight_unknown: boolean;
  unit_cost_pre_tax: number;
  unit_cost_landed: number;
  unit_cost_landed_per_ordered: number;
  cost_per_kg_pre_tax: number | null;
  cost_per_kg_landed: number | null;
}

export interface CostScenario {
  name: "primary" | "alternate";
  description: string;
  tax_treatment: TaxTreatment;
  gst_rate_pct: number | null;
  commitment: CostBreakdown;
  required_only: CostBreakdown;
}

export interface QuoteCosting {
  comparable: boolean;
  required_quantity: number;
  order_quantity: number;
  moq_applies: boolean;
  scenarios: CostScenario[];
  worst_case_index: number;
  worst_case_landed_inr: number | null;
  budget_variance_inr: number | null;
  incomplete: boolean;
  notes: string[];
}

export interface DeliveryEstimate {
  start_date: string | null;
  earliest_arrival: string | null;
  latest_arrival: string | null;
  buffer_days: number | null;
  on_time: boolean | null;
}

export interface Flag {
  code: string;
  severity: Severity;
  message: string;
  question: string | null;
}

export interface ScoreBreakdown {
  price: number;
  delivery: number;
  payment: number;
  quality: number;
  weighted: number;
  penalty: number;
  final: number;
  display: number;
}

export interface QuoteAnalysis {
  quote_id: string | null;
  label: string;
  supplier_name: string;
  rank: number;
  costing: QuoteCosting;
  delivery: DeliveryEstimate;
  flags: Flag[];
  critical_count: number;
  warning_count: number;
  facts: string[];
  assumptions: string[];
  questions: string[];
  score: ScoreBreakdown;
}

export interface Recommendation {
  quote_id: string | null;
  quote_label: string | null;
  supplier_name: string | null;
  rationale: string;
  caveats: string[];
  runner_up_label: string | null;
}

export interface CompareResult {
  reference_date: string;
  requisition: Requisition;
  weights: Weights;
  analyses: QuoteAnalysis[];
  recommendation: Recommendation;
  summary_text: string;
  global_assumptions: string[];
}

export interface ComparisonRunCreate {
  requisition_id: string;
  weights?: Weights;
  reference_date?: string | null;
  label?: string;
}

export interface ComparisonRun {
  id: string;
  requisition_id: string;
  label: string;
  weights: Weights;
  reference_date: string;
  top_pick_label: string | null;
  top_pick_supplier: string | null;
  result: CompareResult;
  created_at: string | null;
}

export interface ChatMessage {
  id?: string | null;
  requisition_id?: string | null;
  role: "user" | "assistant";
  content: string;
  model?: string | null;
  created_at?: string | null;
}

export interface ExtractRequest {
  text: string;
  requisition?: Requisition | null;
}

export interface ExtractResponse {
  available: boolean;
  message: string | null;
  fields: Record<string, unknown>;
  missing_fields: string[];
  ambiguities: string[];
  model_used: string | null;
}

export interface InsightsResponse {
  available: boolean;
  message: string | null;
  headline: string;
  tradeoffs: string[];
  supplier_questions: Record<string, string[]>;
  ungrounded_numbers: string[];
  model_used: string | null;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  requisition_id?: string | null;
  message: string;
  compare: CompareRequest;
  history?: ChatTurn[];
}

export interface ChatResponse {
  available: boolean;
  message: string | null;
  reply: string;
  ungrounded_numbers: string[];
  model_used: string | null;
}

export interface Health {
  status: "ok";
  groq_configured: boolean;
  supabase_configured: boolean;
  storage: "supabase" | "local";
  reference_date: string;
}
