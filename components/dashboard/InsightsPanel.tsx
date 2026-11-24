"use client";

import { useState } from "react";
import { Notice } from "@/components/ui/Notice";
import { TextList } from "@/components/ui/TextList";
import { api, errorMessage } from "@/lib/api";
import type { CompareRequest, InsightsResponse, QuoteAnalysis } from "@/lib/types";

interface Props {
  compare: CompareRequest;
  analyses: QuoteAnalysis[];
}

/** Identity of the inputs, so we can tell when insights no longer match the sliders/date. */
const inputKey = (c: CompareRequest) => JSON.stringify([c.requisition.id, c.weights, c.reference_date, c.quotes.length]);

export function InsightsPanel({ compare, analyses }: Props) {
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [generatedFor, setGeneratedFor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.insights({ compare });
      setInsights(res);
      setGeneratedFor(inputKey(compare));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const supplierName = (label: string) => analyses.find((a) => a.label === label)?.supplier_name ?? `Quote ${label}`;
  const stale = insights !== null && generatedFor !== inputKey(compare);

  return (
    <div className="card p-4 md:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="micro">AI-generated — numbers come from the deterministic engine</p>
        <button type="button" className="btn btn-primary" onClick={generate} disabled={loading}>
          {loading ? "Generating…" : insights ? "Regenerate" : "Generate AI insights"}
        </button>
      </div>

      {error && (
        <Notice tone="rose" className="mt-4">
          {error}
        </Notice>
      )}

      {insights && (
        <div className="mt-4 space-y-4" aria-live="polite">
          {!insights.available && insights.message && <Notice>{insights.message}</Notice>}
          {stale && <Notice tone="peach">Priorities or date changed since these insights were generated — regenerate to refresh.</Notice>}
          {insights.ungrounded_numbers.length > 0 && (
            <Notice tone="peach" title="Check these numbers — not found in the calculation:">
              {insights.ungrounded_numbers.join(", ")}
            </Notice>
          )}

          {insights.headline && <p className="font-display text-xl font-bold leading-snug">{insights.headline}</p>}
          <TextList title="Trade-offs" items={insights.tradeoffs} />

          {Object.keys(insights.supplier_questions).length > 0 && (
            <div className="grid gap-4 md:grid-cols-2">
              {Object.entries(insights.supplier_questions).map(([label, questions]) => (
                <TextList key={label} title={`Ask ${supplierName(label)} (${label})`} items={questions} />
              ))}
            </div>
          )}
          {insights.model_used && <p className="text-xs text-muted">Model: {insights.model_used}</p>}
        </div>
      )}
    </div>
  );
}
