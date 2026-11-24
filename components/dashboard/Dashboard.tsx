"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ChatWidget } from "@/components/dashboard/ChatWidget";
import { ComparisonTable } from "@/components/dashboard/ComparisonTable";
import { DashboardSkeleton } from "@/components/dashboard/DashboardSkeleton";
import { ExecutiveStrip } from "@/components/dashboard/ExecutiveStrip";
import { InsightsPanel } from "@/components/dashboard/InsightsPanel";
import { PrioritySliders } from "@/components/dashboard/PrioritySliders";
import { QuoteCards } from "@/components/dashboard/QuoteCards";
import { RiskPanel } from "@/components/dashboard/RiskPanel";
import { useDashboardData } from "@/components/dashboard/useDashboardData";
import { Notice } from "@/components/ui/Notice";
import { Section } from "@/components/ui/Section";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { errorMessage } from "@/lib/api";
import type { CompareRequest } from "@/lib/types";

export function Dashboard() {
  const router = useRouter();
  const params = useSearchParams();
  const data = useDashboardData(params.get("req"), params.get("run"));
  const { requisitions, requisitionId, quotes, result, error } = data;

  // Nothing to show yet: hard error, empty states, or loading.
  if (error && !result) return <ErrorState error={error} onRetry={data.retry} />;
  if (requisitions && requisitions.length === 0) {
    return (
      <EmptyState title="No requisitions yet">
        <Link className="btn btn-primary" href="/requisitions/new">
          Create a requisition
        </Link>
      </EmptyState>
    );
  }
  if (quotes && quotes.length === 0 && requisitionId) {
    return (
      <EmptyState title="No quotes on this requisition yet">
        <Link className="btn btn-primary" href={`/history?req=${encodeURIComponent(requisitionId)}`}>
          Add quotes in History
        </Link>
      </EmptyState>
    );
  }
  if (!result || !requisitionId || !quotes) return <DashboardSkeleton />;

  // The same inputs the engine just used — sent to the AI routes so they explain, not recalculate.
  const compare: CompareRequest = {
    requisition: result.requisition,
    quotes,
    weights: result.weights,
    reference_date: result.reference_date,
  };

  return (
    <div className="space-y-10 print:space-y-4">
      {/* Toolbar: which requisition, which "today" */}
      <div className="flex flex-wrap items-end gap-4 print:hidden">
        <div>
          <label htmlFor="req-select" className="micro mb-1 block">
            Requisition
          </label>
          <select
            id="req-select"
            className="input min-w-64"
            value={requisitionId}
            onChange={(e) => router.push(`/?req=${encodeURIComponent(e.target.value)}`)}
          >
            {(requisitions ?? []).map((r) => (
              <option key={r.id ?? r.pr_number} value={r.id ?? ""}>
                {r.pr_number} · {r.item_name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="as-of" className="micro mb-1 block">
            As of
          </label>
          <input
            id="as-of"
            type="date"
            className="input"
            value={data.asOf ?? result.reference_date}
            onChange={(e) => data.setAsOf(e.target.value || null)}
          />
        </div>
        <p className="pb-2 text-xs text-muted" aria-live="polite">
          {data.comparing ? "Updating…" : "Up to date"}
        </p>
      </div>

      {error ? <Notice tone="rose">Last update failed: {errorMessage(error)}</Notice> : null}

      <ExecutiveStrip result={result} requisitionId={requisitionId} />

      <Section index="01" title="Your priorities" id="priorities" className="print:hidden">
        <PrioritySliders weights={data.weights} onChange={data.setWeights} />
      </Section>

      <Section index="02" title="Comparison" id="comparison">
        <div className="hidden md:block print:block">
          <ComparisonTable result={result} quotes={quotes} />
        </div>
        <div className="md:hidden print:hidden">
          <QuoteCards result={result} quotes={quotes} />
        </div>
      </Section>

      <Section index="03" title="Risks & questions" id="risks">
        <RiskPanel result={result} />
      </Section>

      <Section index="04" title="AI insights" id="insights" className="print:hidden">
        <InsightsPanel compare={compare} analyses={result.analyses} />
      </Section>

      <ChatWidget key={requisitionId} requisitionId={requisitionId} compare={compare} />
    </div>
  );
}
