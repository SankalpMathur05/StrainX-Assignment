// Human labels for the enum values in lib/types.ts, plus the tone (pastel token) each one maps to.
import type {
  BrandStatus,
  CoaStatus,
  LeadTimeBasis,
  LeadTimeStart,
  PricingBasis,
  PricingUnit,
  Severity,
  SourceChannel,
  TaxTreatment,
  Unit,
} from "@/lib/types";

/** Pastel accent names; each maps to a bg/ink pair defined in app/globals.css. */
export type Tone = "mint" | "lavender" | "peach" | "sky" | "rose" | "neutral";

export interface Option<V extends string = string> {
  value: V;
  label: string;
}

export const UNIT_OPTIONS: Option<Unit>[] = [
  { value: "kg", label: "kg" },
  { value: "g", label: "g" },
  { value: "L", label: "L" },
  { value: "mL", label: "mL" },
  { value: "pack", label: "pack" },
  { value: "drum", label: "drum" },
  { value: "unit", label: "unit" },
];

export const PRICING_UNIT_OPTIONS: Option<PricingUnit>[] = [
  { value: "per_unit", label: "Per unit" },
  { value: "per_kg", label: "Per kg" },
  { value: "per_pack", label: "Per pack" },
  { value: "per_drum", label: "Per drum" },
];

export const PRICING_BASIS_OPTIONS: Option<PricingBasis>[] = [
  { value: "DELIVERED", label: "Delivered" },
  { value: "EX_WORKS", label: "Ex-works" },
  { value: "CIF", label: "CIF (import)" },
  { value: "PICKUP", label: "Pickup" },
  { value: "UNSPECIFIED", label: "Not stated" },
];

export const TAX_OPTIONS: Option<TaxTreatment>[] = [
  { value: "EXCLUSIVE_GST", label: "GST extra" },
  { value: "INCLUSIVE_GST", label: "GST included" },
  { value: "IMPORT_DUTY_IGST", label: "Import: duty + IGST" },
  { value: "EXEMPT", label: "Exempt" },
  { value: "UNSPECIFIED", label: "Not stated" },
];

export const COA_OPTIONS: Option<CoaStatus>[] = [
  { value: "EVERY_BATCH", label: "Every batch" },
  { value: "WITH_MATERIAL", label: "With material" },
  { value: "ON_REQUEST_OR_CONDITIONAL", label: "On request" },
  { value: "MISSING_OR_UNCLEAR", label: "Missing / unclear" },
];

export const BRAND_STATUS_OPTIONS: Option<BrandStatus>[] = [
  { value: "VERIFIED", label: "Verified" },
  { value: "NAMED_UNVERIFIED", label: "Named, unverified" },
  { value: "MISSING", label: "Not named" },
];

export const SOURCE_OPTIONS: Option<SourceChannel>[] = [
  { value: "EMAIL", label: "Email" },
  { value: "WHATSAPP", label: "WhatsApp" },
  { value: "PDF", label: "PDF" },
  { value: "PHONE", label: "Phone call" },
  { value: "OTHER", label: "Other" },
];

export const LEAD_BASIS_OPTIONS: Option<LeadTimeBasis>[] = [
  { value: "CALENDAR", label: "Calendar days" },
  { value: "WORKING", label: "Working days (Mon–Sat)" },
];

export const LEAD_START_OPTIONS: Option<LeadTimeStart>[] = [
  { value: "PO", label: "From PO" },
  { value: "PAYMENT", label: "From payment" },
];

/** Looks up an option label, falling back to the raw value. */
export function labelOf<V extends string>(options: Option<V>[], value: V | null | undefined): string {
  if (value == null) return "—";
  return options.find((o) => o.value === value)?.label ?? value;
}

export const COA_TONE: Record<CoaStatus, Tone> = {
  EVERY_BATCH: "mint",
  WITH_MATERIAL: "peach",
  ON_REQUEST_OR_CONDITIONAL: "peach",
  MISSING_OR_UNCLEAR: "rose",
};

export const BRAND_TONE: Record<BrandStatus, Tone> = {
  VERIFIED: "mint",
  NAMED_UNVERIFIED: "peach",
  MISSING: "rose",
};

export const SEVERITY_TONE: Record<Severity, Tone> = {
  CRITICAL: "rose",
  WARNING: "peach",
  INFO: "sky",
};

export const SEVERITY_LABEL: Record<Severity, string> = {
  CRITICAL: "Critical",
  WARNING: "Warning",
  INFO: "Info",
};

export const SEVERITY_ORDER: Severity[] = ["CRITICAL", "WARNING", "INFO"];
