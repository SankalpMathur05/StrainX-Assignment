// Spec-driven form drafts shared by the requisition form and the quote editor.
//
// A form is described by a list of FieldSpecs. While editing, every value lives in a
// "draft" as a string (or boolean for checkboxes), which is what HTML inputs produce.
// Three pure functions move data between the typed model and the draft:
//   toDraft      model  -> draft   (to open a record for editing)
//   fromDraft    draft  -> model   (on save; validates and converts types)
//   applyExtracted AI fields -> draft (paste-to-fill; returns which keys were filled)
import type { Option } from "@/lib/labels";

export type FieldKind =
  | "text" // string
  | "textOrNull" // string | null (empty -> null)
  | "textarea" // string, multi-line
  | "number" // number (empty -> 0 unless required)
  | "numberOrNull" // number | null (empty -> null)
  | "date" // "YYYY-MM-DD"
  | "dateOrNull" // "YYYY-MM-DD" | null
  | "bool" // checkbox
  | "select" // one of options
  | "selectOrNull" // one of options | null
  | "lines" // string[] edited one item per line
  | "freight"; // number | null, with an "unknown / at actual" checkbox meaning null

export interface FieldSpec<K extends string = string> {
  key: K;
  label: string;
  kind: FieldKind;
  options?: Option[];
  hint?: string;
  required?: boolean;
  integer?: boolean;
  min?: number;
  max?: number;
  /** Span the full row of the field grid. */
  wide?: boolean;
}

export interface FieldGroup<K extends string = string> {
  title: string;
  fields: FieldSpec<K>[];
}

/** Draft values keyed by field key. Freight also uses `${key}__unknown` for its checkbox. */
export type Draft = Record<string, string | boolean>;

export const unknownKey = (key: string) => `${key}__unknown`;

/** Converts one model value to its draft representation. */
function valueToDraft(spec: FieldSpec, value: unknown): string | boolean {
  if (spec.kind === "bool") return value === true;
  if (value === null || value === undefined) return "";
  if (spec.kind === "lines") return Array.isArray(value) ? value.map(String).join("\n") : String(value);
  return String(value);
}

export function toDraft(model: object, specs: FieldSpec[]): Draft {
  const source = model as Record<string, unknown>;
  const draft: Draft = {};
  for (const spec of specs) {
    draft[spec.key] = valueToDraft(spec, source[spec.key]);
    if (spec.kind === "freight") draft[unknownKey(spec.key)] = source[spec.key] === null;
  }
  return draft;
}

const asText = (v: string | boolean | undefined) => (typeof v === "string" ? v.trim() : "");

/** Validates and converts a draft back to typed values. Returns errors instead of throwing. */
export function fromDraft<T extends object>(
  base: T,
  draft: Draft,
  specs: FieldSpec[],
): { value: T; errors: string[] } {
  const out: Record<string, unknown> = { ...(base as Record<string, unknown>) };
  const errors: string[] = [];

  for (const spec of specs) {
    const raw = draft[spec.key];
    const text = asText(raw);

    if (spec.required && spec.kind !== "bool" && text === "") {
      errors.push(`${spec.label} is required.`);
      continue;
    }

    switch (spec.kind) {
      case "bool":
        out[spec.key] = raw === true;
        break;
      case "text":
      case "textarea":
      case "date":
      case "select":
        out[spec.key] = text;
        break;
      case "textOrNull":
      case "dateOrNull":
      case "selectOrNull":
        out[spec.key] = text === "" ? null : text;
        break;
      case "lines":
        out[spec.key] = text
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean);
        break;
      case "number":
      case "numberOrNull":
      case "freight": {
        if (spec.kind === "freight" && draft[unknownKey(spec.key)] === true) {
          out[spec.key] = null;
          break;
        }
        if (text === "") {
          out[spec.key] = spec.kind === "numberOrNull" ? null : 0;
          break;
        }
        const n = Number(text);
        if (!Number.isFinite(n)) errors.push(`${spec.label} must be a number.`);
        else if (spec.integer && !Number.isInteger(n)) errors.push(`${spec.label} must be a whole number.`);
        else if (spec.min !== undefined && n < spec.min) errors.push(`${spec.label} must be at least ${spec.min}.`);
        else if (spec.max !== undefined && n > spec.max) errors.push(`${spec.label} must be at most ${spec.max}.`);
        out[spec.key] = n;
        break;
      }
    }
  }
  // Every key in `specs` was converted to the type its kind describes, so this matches T.
  return { value: out as T, errors };
}

/**
 * Merges AI-extracted fields into a draft. Only keys the form knows are applied; select
 * values outside the allowed options are ignored. Returns the keys that were filled.
 */
export function applyExtracted(
  draft: Draft,
  fields: Record<string, unknown>,
  specs: FieldSpec[],
): { draft: Draft; filled: string[] } {
  const next: Draft = { ...draft };
  const filled: string[] = [];

  for (const spec of specs) {
    if (!(spec.key in fields)) continue;
    const value = fields[spec.key];
    if (value === undefined) continue;

    if (spec.kind === "freight") {
      next[unknownKey(spec.key)] = value === null;
      next[spec.key] = value === null ? "" : String(value);
      filled.push(spec.key);
      continue;
    }
    if (value === null && !spec.kind.endsWith("OrNull")) continue; // field can't be null
    if (spec.kind === "bool" && typeof value !== "boolean") continue;
    if ((spec.kind === "select" || spec.kind === "selectOrNull") && value !== null) {
      if (!spec.options?.some((o) => o.value === value)) continue;
    }
    next[spec.key] = valueToDraft(spec, value);
    filled.push(spec.key);
  }
  return { draft: next, filled };
}

/** Flattens grouped specs into one list (for conversion). */
export function allFields<K extends string>(groups: FieldGroup<K>[]): FieldSpec<K>[] {
  return groups.flatMap((g) => g.fields);
}
