"use client";

import { useState } from "react";
import { Notice } from "@/components/ui/Notice";
import { errorMessage } from "@/lib/api";
import type { ExtractResponse } from "@/lib/types";

interface Props {
  id: string;
  label: string;
  placeholder?: string;
  /** Calls the extract route. */
  extract: (text: string) => Promise<ExtractResponse>;
  /** Receives the extracted fields to merge into the form. */
  onFields: (fields: Record<string, unknown>, text: string) => void;
  /** Turns field keys ("valid_until") into form labels ("Valid until"). */
  labelFor: (key: string) => string;
}

/** Paste messy text → AI extraction → fields land in the form for review. Never saves by itself. */
export function PasteToFill({ id, label, placeholder, extract, onFields, labelFor }: Props) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ExtractResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await extract(text);
      setResponse(res);
      if (res.available) onFields(res.fields, text);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card border-dashed p-4 md:p-5">
      <label htmlFor={id} className="micro mb-2 block">
        {label}
      </label>
      <textarea
        id={id}
        className="input min-h-32 font-mono text-xs"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
      />
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button type="button" className="btn btn-primary" onClick={run} disabled={loading || !text.trim()}>
          {loading ? "Reading…" : "Autofill with AI"}
        </button>
        <p className="text-xs text-muted">You review every field before saving.</p>
      </div>

      <div className="mt-3 space-y-3" aria-live="polite">
        {error && <Notice tone="rose">{error}</Notice>}
        {response && !response.available && (
          <Notice>
            {response.message ?? "AI extraction is unavailable."} Fill in the form below manually.
          </Notice>
        )}
        {response?.available && (
          <Notice tone="lavender" title="Filled from your text — fields marked AI-filled need a quick check.">
            {response.missing_fields.length > 0 && (
              <p>
                <strong>Not found:</strong> {response.missing_fields.map(labelFor).join(", ")}
              </p>
            )}
            {response.ambiguities.length > 0 && (
              <div className="mt-1">
                <strong>Ambiguities:</strong>
                <ul className="list-disc pl-5">
                  {response.ambiguities.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            )}
          </Notice>
        )}
      </div>
    </div>
  );
}
