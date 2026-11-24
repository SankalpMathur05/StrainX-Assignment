"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { RequisitionDetails } from "@/components/details/RequisitionDetails";
import { QuoteEditor } from "@/components/history/QuoteEditor";
import { QuoteViewer } from "@/components/history/QuoteViewer";
import { QuotesTable } from "@/components/history/QuotesTable";
import { RequisitionSwitcher } from "@/components/history/RequisitionSwitcher";
import { RunsList } from "@/components/history/RunsList";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { Notice } from "@/components/ui/Notice";
import { Section } from "@/components/ui/Section";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { api, errorMessage } from "@/lib/api";
import type { ComparisonRun, Quote, Requisition } from "@/lib/types";

export function HistoryView() {
  const router = useRouter();
  const reqParam = useSearchParams().get("req");

  const [requisitions, setRequisitions] = useState<Requisition[] | null>(null);
  const [quotes, setQuotes] = useState<Quote[] | null>(null);
  const [runs, setRuns] = useState<ComparisonRun[] | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Quote | "new" | null>(null);
  const [viewing, setViewing] = useState<Quote | null>(null);
  // Bumping these re-fetches the requisition list / the selected requisition's quotes and runs.
  const [listVersion, setListVersion] = useState(0);
  const [detailVersion, setDetailVersion] = useState(0);

  const selected = requisitions?.find((r) => r.id === reqParam) ?? requisitions?.[0] ?? null;
  const selectedId = selected?.id ?? null;

  useEffect(() => {
    let cancelled = false;
    api
      .listRequisitions()
      .then((list) => {
        if (!cancelled) setRequisitions(list);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(err);
      });
    return () => {
      cancelled = true;
    };
  }, [listVersion]);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setQuotes(null);
    setRuns(null);
    Promise.all([api.listQuotes(selectedId), api.listComparisons(selectedId)])
      .then(([qs, rs]) => {
        if (cancelled) return;
        setQuotes(qs);
        setRuns(rs);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(err);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, detailVersion]);

  async function act(action: () => Promise<unknown>, after: () => void) {
    setActionError(null);
    try {
      await action();
      after();
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  function deleteRequisition(r: Requisition) {
    if (!r.id || !window.confirm(`Delete ${r.pr_number} with all its quotes, saved runs and chat? This can't be undone.`)) return;
    const id = r.id;
    act(
      () => api.deleteRequisition(id),
      () => {
        router.replace("/history");
        setListVersion((v) => v + 1);
      },
    );
  }

  function deleteQuote(q: Quote) {
    if (!q.id || !window.confirm(`Delete quote ${q.label} from ${q.supplier_name}?`)) return;
    const id = q.id;
    act(() => api.deleteQuote(id), () => setDetailVersion((v) => v + 1));
  }

  function retry() {
    setLoadError(null);
    setListVersion((v) => v + 1);
  }

  if (loadError) return <ErrorState error={loadError} onRetry={retry} />;
  if (!requisitions) return <Skeleton className="h-96 w-full" />;
  if (requisitions.length === 0 || !selected) {
    return (
      <EmptyState title="No requisitions yet">
        <Link className="btn btn-primary" href="/requisitions/new">
          Create a requisition
        </Link>
      </EmptyState>
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[320px_1fr]">
      <aside>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="micro">Requisitions</h2>
          <Link href="/requisitions/new" className="text-xs font-semibold underline">
            + New
          </Link>
        </div>
        <RequisitionSwitcher
          requisitions={requisitions}
          selectedId={selectedId}
          onSelect={(id) => router.replace(`/history?req=${encodeURIComponent(id)}`)}
        />
      </aside>

      <div className="min-w-0 space-y-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="micro">{selected.pr_number}</p>
            <h1 className="mt-1 font-display text-3xl font-bold tracking-tight md:text-4xl">{selected.item_name}</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="btn btn-primary" href={`/?req=${encodeURIComponent(selectedId ?? "")}`}>
              Open in dashboard
            </Link>
            <button type="button" className="btn btn-danger" onClick={() => deleteRequisition(selected)}>
              Delete requisition
            </button>
          </div>
        </div>

        {actionError && <Notice tone="rose">{actionError}</Notice>}

        <CollapsibleSection index="01" title="Requisition details" id="requisition-details">
          <RequisitionDetails requisition={selected} />
        </CollapsibleSection>

        <Section
          index="02"
          title="Quotes"
          id="quotes"
          actions={
            <button type="button" className="btn btn-primary" onClick={() => setEditing("new")}>
              Add quote
            </button>
          }
        >
          {quotes ? (
            <QuotesTable quotes={quotes} onView={(q) => setViewing(q)} onEdit={(q) => setEditing(q)} onDelete={deleteQuote} />
          ) : (
            <Skeleton className="h-40 w-full" />
          )}
        </Section>

        <Section index="03" title="Saved comparison runs" id="runs">
          {runs ? <RunsList runs={runs} /> : <Skeleton className="h-24 w-full" />}
        </Section>
      </div>

      {viewing && (
        <QuoteViewer
          key={viewing.id ?? viewing.label}
          requisition={selected}
          quote={viewing}
          onClose={() => setViewing(null)}
          onEdit={() => {
            setViewing(null);
            setEditing(viewing);
          }}
        />
      )}

      {editing && (
        <QuoteEditor
          key={editing === "new" ? "new" : (editing.id ?? editing.label)}
          requisition={selected}
          quote={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            setDetailVersion((v) => v + 1);
          }}
        />
      )}
    </div>
  );
}
