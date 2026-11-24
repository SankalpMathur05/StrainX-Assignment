// Small read-only helpers over the engine output (CompareResult / QuoteAnalysis).
// No arithmetic on money happens here: every figure shown comes from the Python engine.
import type {
  CostBreakdown,
  CostScenario,
  QuoteAnalysis,
  QuoteCosting,
  Quote,
  TaxTreatment,
  Weights,
} from "@/lib/types";

/** The scenario the engine ranked on (highest landed cost at commitment quantity). */
export function worstScenario(costing: QuoteCosting): CostScenario | null {
  return costing.scenarios[costing.worst_case_index] ?? costing.scenarios[0] ?? null;
}

/** Any other tax reading(s) of the same quote, e.g. "GST inclusive" vs "GST extra". */
export function otherScenarios(costing: QuoteCosting): CostScenario[] {
  return costing.scenarios.filter((_, i) => i !== costing.worst_case_index);
}

/** "IGST" for imports, "GST" otherwise. */
export function taxName(treatment: TaxTreatment): string {
  return treatment === "IMPORT_DUTY_IGST" ? "IGST" : "GST";
}

export function infoCount(analysis: QuoteAnalysis): number {
  return analysis.flags.filter((f) => f.severity === "INFO").length;
}

/** Finds the stored quote behind an analysis row (by id, then by label). */
export function findQuote(analysis: QuoteAnalysis, quotes: Quote[]): Quote | undefined {
  return (
    quotes.find((q) => analysis.quote_id != null && q.id === analysis.quote_id) ??
    quotes.find((q) => q.label === analysis.label)
  );
}

/** Landed cost per required kg when mass-based, otherwise per requisition unit. */
export function landedPerUnit(b: CostBreakdown, unit: string): { value: number; per: string } {
  if (b.cost_per_kg_landed != null) return { value: b.cost_per_kg_landed, per: "kg" };
  return { value: b.unit_cost_landed, per: unit };
}

/** True when some cost component (usually freight "at actual") is missing from the total. */
export function hasUnknownCost(costing: QuoteCosting): boolean {
  const worst = worstScenario(costing);
  return costing.incomplete || (worst?.commitment.freight_unknown ?? false);
}

export const WEIGHT_KEYS: (keyof Weights)[] = ["price", "delivery", "payment", "quality"];

export const WEIGHT_LABELS: Record<keyof Weights, string> = {
  price: "Price / Budget",
  delivery: "Delivery speed",
  payment: "Payment terms",
  quality: "Quality & risk compliance",
};

export function weightTotal(w: Weights): number {
  return w.price + w.delivery + w.payment + w.quality;
}

/** Weights summary for lists: "Price 30 · Delivery 25 · Payment 10 · Quality 35". */
export function weightsShort(w: Weights): string {
  return `Price ${w.price} · Delivery ${w.delivery} · Payment ${w.payment} · Quality ${w.quality}`;
}
