// The one-minute read: what to buy, what it costs, how it sits against budget, and the risks.
import { ShareActions } from "@/components/dashboard/ShareActions";
import { hasUnknownCost, taxName, worstScenario } from "@/lib/analysis";
import { formatDate, formatINR, formatQty, formatScore, formatVariance } from "@/lib/format";
import type { CompareResult } from "@/lib/types";

function Stat({
  label,
  children,
  className = "",
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-2xl p-4 md:p-5 ${className}`}>
      <p className="micro mb-2 text-current opacity-80">{label}</p>
      {children}
    </div>
  );
}

export function ExecutiveStrip({ result, requisitionId }: { result: CompareResult; requisitionId: string }) {
  const { requisition: req, recommendation: rec } = result;
  const pick = result.analyses.find((a) => a.label === rec.quote_label) ?? null;
  const worst = pick ? worstScenario(pick.costing) : null;
  const variance = pick?.costing.budget_variance_inr ?? null;
  const totalCritical = result.analyses.reduce((sum, a) => sum + a.critical_count, 0);
  const pickCritical = pick?.critical_count ?? 0;

  return (
    <section aria-labelledby="exec-heading" className="card overflow-hidden border-t-4 border-t-ink p-4 md:p-6">
      {/* Requisition line */}
      <p className="micro">
        {req.pr_number} · as of {formatDate(result.reference_date)}
      </p>
      <h1 id="exec-heading" className="mt-1 font-display text-3xl font-bold tracking-tight md:text-5xl">
        {req.item_name}
      </h1>
      <p className="mt-2 text-sm text-muted">
        {formatQty(req.required_quantity, req.unit)} · need by {formatDate(req.need_by_date)} · budget{" "}
        {formatINR(req.approved_budget)}
      </p>

      {/* Four headline numbers */}
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 print:grid-cols-4">
        <Stat label="Recommended" className="bg-lavender text-lavender-ink">
          {pick ? (
            <>
              <p className="figure text-4xl md:text-5xl">{pick.label}</p>
              <p className="mt-2 font-semibold">{pick.supplier_name}</p>
              <p className="text-sm">Score {formatScore(pick.score.display)} / 100</p>
            </>
          ) : (
            <p className="font-semibold">No recommendation yet</p>
          )}
        </Stat>

        <Stat label="Worst-case landed" className="bg-surface-2">
          <p className="figure text-2xl md:text-3xl xl:text-4xl">
            {pick?.costing.worst_case_landed_inr != null ? formatINR(pick.costing.worst_case_landed_inr) : "—"}
          </p>
          {pick && (
            <p className="mt-2 text-sm text-muted">for {formatQty(pick.costing.order_quantity, req.unit)}</p>
          )}
          {pick && hasUnknownCost(pick.costing) && (
            <p className="text-sm font-semibold text-peach-ink">+ transport (unknown)</p>
          )}
        </Stat>

        <Stat
          label="vs Budget"
          className={variance == null ? "bg-surface-2" : variance > 0 ? "bg-rose text-rose-ink" : "bg-mint text-mint-ink"}
        >
          <p className="figure text-2xl md:text-3xl xl:text-4xl">{variance == null ? "—" : formatVariance(variance)}</p>
          {variance != null && <p className="mt-2 text-sm font-semibold">{variance > 0 ? "Over budget" : "Within budget"}</p>}
          {worst && worst.commitment.recoverable_tax_inr > 0 && (
            <p className="mt-1 text-xs">
              includes {formatINR(worst.commitment.recoverable_tax_inr)} {taxName(worst.tax_treatment)} — potential
              input tax credit, not deducted
            </p>
          )}
        </Stat>

        <Stat label="Critical risks" className={pickCritical > 0 ? "bg-rose text-rose-ink" : "bg-mint text-mint-ink"}>
          <p className="figure text-4xl md:text-5xl">{pickCritical}</p>
          <p className="mt-2 text-sm font-semibold">{pick ? "on the recommended quote" : "—"}</p>
          <p className="text-xs">{totalCritical} across all quotes</p>
        </Stat>
      </div>

      {/* Why */}
      <p className="mt-5 max-w-4xl text-base leading-relaxed md:text-lg">{rec.rationale}</p>
      {rec.caveats.length > 0 && (
        <ul className="mt-2 space-y-1 text-sm text-muted">
          {rec.caveats.map((c) => (
            <li key={c}>— {c}</li>
          ))}
        </ul>
      )}

      <div className="mt-5">
        <ShareActions requisitionId={requisitionId} result={result} />
      </div>
    </section>
  );
}
