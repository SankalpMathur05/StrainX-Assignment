"use client";

// Renders a list of FieldSpecs as labelled inputs. AI-filled fields get a lavender ring
// and an "AI" tag until the user edits them.
import { unknownKey, type Draft, type FieldSpec } from "@/lib/forms";

interface Props {
  idPrefix: string;
  fields: FieldSpec[];
  draft: Draft;
  aiFilled: ReadonlySet<string>;
  onChange: (key: string, value: string | boolean) => void;
}

const AI_RING = "ring-2 ring-lavender-ink/60 bg-lavender";

export function FormFields({ idPrefix, fields, draft, aiFilled, onChange }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {fields.map((spec) => (
        <Field
          key={spec.key}
          id={`${idPrefix}-${spec.key}`}
          spec={spec}
          draft={draft}
          ai={aiFilled.has(spec.key)}
          onChange={onChange}
        />
      ))}
    </div>
  );
}

interface FieldProps {
  id: string;
  spec: FieldSpec;
  draft: Draft;
  ai: boolean;
  onChange: Props["onChange"];
}

function Field({ id, spec, draft, ai, onChange }: FieldProps) {
  const value = draft[spec.key];
  const text = typeof value === "string" ? value : "";
  const hintId = spec.hint ? `${id}-hint` : undefined;
  const inputClass = `input ${ai ? AI_RING : ""}`;
  const set = (v: string | boolean) => onChange(spec.key, v);

  const aiTag = ai ? (
    <span className="ml-2 rounded-full bg-lavender px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-lavender-ink">
      AI-filled
    </span>
  ) : null;

  if (spec.kind === "bool") {
    return (
      <div className={`flex items-center gap-3 rounded-xl px-1 py-2 ${spec.wide ? "sm:col-span-2" : ""} ${ai ? AI_RING : ""}`}>
        <input id={id} type="checkbox" className="h-5 w-5 accent-current" checked={value === true} onChange={(e) => set(e.target.checked)} />
        <label htmlFor={id} className="text-sm font-medium">
          {spec.label}
          {aiTag}
        </label>
      </div>
    );
  }

  let control: React.ReactNode;
  switch (spec.kind) {
    case "textarea":
    case "lines":
      control = <textarea id={id} className={inputClass} value={text} onChange={(e) => set(e.target.value)} aria-describedby={hintId} />;
      break;
    case "number":
    case "numberOrNull":
      control = (
        <input id={id} type="number" inputMode="decimal" step="any" className={inputClass} value={text} onChange={(e) => set(e.target.value)} aria-describedby={hintId} aria-required={spec.required} />
      );
      break;
    case "date":
    case "dateOrNull":
      control = <input id={id} type="date" className={inputClass} value={text} onChange={(e) => set(e.target.value)} aria-describedby={hintId} aria-required={spec.required} />;
      break;
    case "select":
    case "selectOrNull":
      control = (
        <select id={id} className={inputClass} value={text} onChange={(e) => set(e.target.value)} aria-describedby={hintId}>
          {spec.kind === "selectOrNull" && <option value="">—</option>}
          {spec.options?.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      );
      break;
    case "freight": {
      const unknown = draft[unknownKey(spec.key)] === true;
      control = (
        <div className="flex items-center gap-3">
          <input id={id} type="number" inputMode="decimal" step="any" className={inputClass} value={unknown ? "" : text} disabled={unknown} onChange={(e) => set(e.target.value)} />
          <label className="flex shrink-0 items-center gap-2 text-sm">
            <input type="checkbox" className="h-4 w-4" checked={unknown} onChange={(e) => onChange(unknownKey(spec.key), e.target.checked)} />
            Unknown / at actual
          </label>
        </div>
      );
      break;
    }
    default:
      control = <input id={id} type="text" className={inputClass} value={text} onChange={(e) => set(e.target.value)} aria-describedby={hintId} aria-required={spec.required} />;
  }

  return (
    <div className={spec.wide ? "sm:col-span-2" : ""}>
      <label htmlFor={id} className="mb-1 flex items-center text-sm font-medium">
        {spec.label}
        {spec.required && (
          <span className="ml-0.5 text-rose-ink" aria-hidden="true">
            *
          </span>
        )}
        {aiTag}
      </label>
      {control}
      {spec.hint && (
        <p id={hintId} className="mt-1 text-xs text-muted">
          {spec.hint}
        </p>
      )}
    </div>
  );
}
