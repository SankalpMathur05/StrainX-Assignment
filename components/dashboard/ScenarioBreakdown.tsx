// Cost build-up for every tax reading of one quote: goods, duty, GST/IGST, freight, clearance, total.
import { taxName } from "@/lib/analysis";
import { formatINR, formatQty } from "@/lib/format";
import type { CostBreakdown, QuoteCosting } from "@/lib/types";

function Row({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between gap-4 py-0.5 ${strong ? "border-t border-line pt-1 font-semibold" : ""}`}>
      <dt className={strong ? "" : "text-muted"}>{label}</dt>
      <dd className="tabular-nums">{value}</dd>
    </div>
  );
}

function Breakdown({ b, tax, title }: { b: CostBreakdown; tax: string; title: string }) {
  return (
    <div>
      <p className="micro mb-1">{title}</p>
      <dl className="text-sm">
        <Row label="Goods (pre-tax)" value={formatINR(b.goods_pre_tax_inr)} />
        {b.customs_duty_inr > 0 && <Row label="Customs duty" value={formatINR(b.customs_duty_inr)} />}
        <Row label={`${tax} (potential ITC)`} value={formatINR(b.recoverable_tax_inr)} />
        <Row label="Freight" value={b.freight_unknown ? "Unknown (at actual)" : formatINR(b.freight_inr)} />
        {b.clearance_inr > 0 && <Row label="Clearance" value={formatINR(b.clearance_inr)} />}
        {b.inland_transport_inr > 0 && <Row label="Port-to-site transport" value={formatINR(b.inland_transport_inr)} />}
        <Row label="Landed total" value={formatINR(b.total_landed_inr)} strong />
      </dl>
    </div>
  );
}

export function ScenarioBreakdown({ costing, unit }: { costing: QuoteCosting; unit: string }) {
  if (!costing.comparable) {
    return <p className="text-sm text-muted">Costs not comparable: the quote&apos;s units can&apos;t be converted to the requisition unit.</p>;
  }
  return (
    <div className="space-y-4">
      {costing.scenarios.map((s, i) => (
        <div key={s.name} className="rounded-xl bg-surface-2 p-3">
          <p className="mb-2 text-sm font-semibold">
            {s.description}
            {costing.scenarios.length > 1 && i === costing.worst_case_index && (
              <span className="ml-2 text-xs font-semibold uppercase tracking-wide text-rose-ink">worst case · ranked on this</span>
            )}
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Breakdown
              b={s.commitment}
              tax={taxName(s.tax_treatment)}
              title={`Order: ${formatQty(s.commitment.quantity, unit)}${costing.moq_applies ? " (MOQ)" : ""}`}
            />
            {costing.moq_applies && (
              <Breakdown
                b={s.required_only}
                tax={taxName(s.tax_treatment)}
                title={`If MOQ waived: ${formatQty(s.required_only.quantity, unit)}`}
              />
            )}
          </div>
        </div>
      ))}
      {costing.notes.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-xs text-muted">
          {costing.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
