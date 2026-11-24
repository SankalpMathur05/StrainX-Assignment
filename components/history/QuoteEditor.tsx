"use client";

import { useEffect, useRef, useState } from "react";
import { FormFields } from "@/components/forms/FormFields";
import { PasteToFill } from "@/components/forms/PasteToFill";
import { useDraftForm } from "@/components/forms/useDraftForm";
import { Notice } from "@/components/ui/Notice";
import { api, errorMessage } from "@/lib/api";
import { allFields, fromDraft, toDraft, type Draft } from "@/lib/forms";
import { QUOTE_DEFAULTS, QUOTE_GROUPS, USD_FX_DEFAULT } from "@/lib/formSpecs";
import type { Quote, Requisition } from "@/lib/types";

const FIELDS = allFields(QUOTE_GROUPS);
const labelFor = (key: string) => FIELDS.find((f) => f.key === key)?.label ?? key;

interface Props {
  requisition: Requisition;
  /** Quote to edit, or null to add a new one. */
  quote: Quote | null;
  onClose: () => void;
  onSaved: () => void;
}

/** FX follows the currency (USD → 84, INR → 1) until the user types their own rate. */
function fxFor(currency: string | boolean | undefined): string | null {
  const code = typeof currency === "string" ? currency.trim().toUpperCase() : "";
  if (code === "USD") return String(USD_FX_DEFAULT);
  if (code === "INR") return "1";
  return null;
}

export function QuoteEditor({ requisition, quote, onClose, onSaved }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const form = useDraftForm(
    () => (quote ? toDraft(quote, FIELDS) : { ...toDraft(QUOTE_DEFAULTS, FIELDS), price: "" }),
    FIELDS,
  );
  // An existing quote's FX rate was chosen deliberately; don't overwrite it.
  const [fxTouched, setFxTouched] = useState(quote !== null);
  const [errors, setErrors] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  // Open as a modal on mount (focus trap + Esc come with <dialog>). No cleanup: the parent
  // unmounts this component on close, which removes the dialog from the page anyway.
  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
  }, []);

  function handleChange(key: string, value: string | boolean) {
    form.setField(key, value);
    if (key === "fx_rate_to_inr") setFxTouched(true);
    if (key === "currency" && !fxTouched) {
      const fx = fxFor(value);
      if (fx) form.setDraft((d) => ({ ...d, fx_rate_to_inr: fx }));
    }
  }

  function handleExtracted(fields: Record<string, unknown>, text: string) {
    const merged = form.applyAI(fields);
    const patch: Draft = {};
    if ("fx_rate_to_inr" in fields) setFxTouched(true); // the quote stated its own rate
    else if (!fxTouched) {
      const fx = fxFor(merged.draft.currency);
      if (fx) patch.fx_rate_to_inr = fx;
    }
    if (!merged.draft.raw_text) patch.raw_text = text; // keep the source text with the quote
    if (Object.keys(patch).length > 0) form.setDraft((d) => ({ ...d, ...patch }));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const { value, errors: problems } = fromDraft<Quote>(quote ?? QUOTE_DEFAULTS, form.draft, FIELDS);
    setErrors(problems);
    if (problems.length > 0) return;

    setSaving(true);
    try {
      if (quote?.id) await api.updateQuote(quote.id, value);
      else if (requisition.id) await api.createQuote(requisition.id, value);
      onSaved();
    } catch (err) {
      setErrors([errorMessage(err)]);
      setSaving(false);
    }
  }

  const title = quote ? `Edit quote ${quote.label} · ${quote.supplier_name}` : "Add quote";

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-labelledby="quote-editor-title"
      className="m-0 ml-auto h-dvh max-h-dvh w-full max-w-3xl overflow-y-auto bg-bg p-0 text-ink backdrop:bg-black/50"
    >
      <form onSubmit={save} noValidate>
        <header className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-line bg-bg/95 px-4 py-3 backdrop-blur md:px-6">
          <div>
            <p className="micro">
              {requisition.pr_number} · {requisition.item_name}
            </p>
            <h2 id="quote-editor-title" className="font-display text-xl font-bold">
              {title}
            </h2>
          </div>
          <button type="button" className="btn" onClick={() => dialogRef.current?.close()}>
            Cancel
          </button>
        </header>

        <div className="space-y-6 px-4 py-6 md:px-6">
          <PasteToFill
            id="quote-paste"
            label="Paste supplier quote (email / WhatsApp / PDF text / call notes)"
            placeholder="Paste the supplier's message exactly as received…"
            extract={(text) => api.extractQuote({ text, requisition })}
            onFields={handleExtracted}
            labelFor={labelFor}
          />

          {QUOTE_GROUPS.map((group) => (
            <fieldset key={group.title} className="card p-4 md:p-5">
              <legend className="micro px-1">{group.title}</legend>
              <FormFields idPrefix="quote" fields={group.fields} draft={form.draft} aiFilled={form.aiFilled} onChange={handleChange} />
            </fieldset>
          ))}

          {errors.length > 0 && (
            <Notice tone="rose" title="Please fix:">
              <ul className="list-disc pl-5">
                {errors.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </Notice>
          )}
        </div>

        <footer className="sticky bottom-0 flex justify-end gap-3 border-t border-line bg-bg/95 px-4 py-3 backdrop-blur md:px-6">
          <button type="button" className="btn" onClick={() => dialogRef.current?.close()}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving…" : quote ? "Save changes" : "Add quote"}
          </button>
        </footer>
      </form>
    </dialog>
  );
}
