// Cell renderers shared by the desktop comparison table and the mobile quote cards,
// so both views always show the same figures in the same words.
import { Chip } from "@/components/ui/Chip";
import {
  hasUnknownCost,
  infoCount,
  landedPerUnit,
  otherScenarios,
  taxName,
  worstScenario,
} from "@/lib/analysis";
import { formatDate, formatINR, formatQty, formatScore, formatVariance, plural } from "@/lib/format";
import { BRAND_STATUS_OPTIONS, BRAND_TONE, COA_OPTIONS, COA_TONE, SOURCE_OPTIONS, labelOf } from "@/lib/labels";
import type { DeliveryEstimate, Quote, QuoteAnalysis, QuoteCosting } from "@/lib/types";

const NA = <span className="text-muted">N/A</span>;

/** "P1" — race-position style rank. */
export function Rank({ rank, top }: { rank: number; top: boolean }) {
  return (
    <span className={`figure text-2xl ${top ? "text-lavender-ink" : ""}`}>
      <span className="sr-only">Rank </span>P{rank}
    </span>
  );
}

export function QuoteIdentity({ analysis, quote }: { analysis: QuoteAnalysis; quote?: Quote }) {
  return (
    <div className="min-w-0">
      <p className="font-semibold leading-tight">
        <span className="mr-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded bg-ink px-1 font-display text-xs font-bold text-bg">
          {analysis.label}
        </span>
        {analysis.supplier_name}
      </p>
      {quote && (
        <p className="mt-0.5 text-xs text-muted">
          {labelOf(SOURCE_OPTIONS, quote.source_channel)}
          {quote.supplier_location ? ` · ${quote.supplier_location}` : ""}
        </p>
      )}
    </div>
  );
}

/** Worst-case landed total, the other tax reading if any, and an unknown-cost warning. */
export function LandedCell({ costing }: { costing: QuoteCosting }) {
  const worst = worstScenario(costing);
  if (!costing.comparable || !worst || costing.worst_case_landed_inr == null) return NA;
  const others = otherScenarios(costing);
  return (
    <div>
      <p className="font-display text-base font-bold tabular-nums">{formatINR(costing.worst_case_landed_inr)}</p>
      {others.length > 0 && <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">worst case</p>}
      {others.map((s) => (
        <p key={s.name} className="text-xs text-muted">
          {formatINR(s.commitment.total_landed_inr)} if {s.description}
        </p>
      ))}
      {hasUnknownCost(costing) && <p className="text-xs font-semibold text-peach-ink">+ transport (unknown)</p>}
    </div>
  );
}

export function BudgetCell({ costing }: { costing: QuoteCosting }) {
  const v = costing.budget_variance_inr;
  if (v == null) return NA;
  return (
    <Chip tone={v > 0 ? "rose" : "mint"}>
      {formatVariance(v)} {v > 0 ? "over" : "under"}
    </Chip>
  );
}

export function PerUnitCell({ costing, unit }: { costing: QuoteCosting; unit: string }) {
  const worst = worstScenario(costing);
  if (!costing.comparable || !worst) return NA;
  const { value, per } = landedPerUnit(worst.commitment, unit);
  return (
    <span className="tabular-nums">
      {formatINR(value)}
      <span className="text-muted">/{per}</span>
    </span>
  );
}

export function PreTaxCell({ costing }: { costing: QuoteCosting }) {
  const worst = worstScenario(costing);
  if (!costing.comparable || !worst) return NA;
  return <span className="tabular-nums">{formatINR(worst.commitment.goods_pre_tax_inr)}</span>;
}

/** Recoverable GST / IGST (potential input tax credit), plus non-recoverable customs duty. */
export function TaxCell({ costing }: { costing: QuoteCosting }) {
  const worst = worstScenario(costing);
  if (!costing.comparable || !worst) return NA;
  const b = worst.commitment;
  return (
    <div className="tabular-nums">
      <p>
        {formatINR(b.recoverable_tax_inr)} <span className="text-xs text-muted">{taxName(worst.tax_treatment)}</span>
      </p>
      {b.customs_duty_inr > 0 && (
        <p className="text-xs text-muted">+ duty {formatINR(b.customs_duty_inr)} (not recoverable)</p>
      )}
    </div>
  );
}

/** Order quantity; when MOQ forces a bigger order, also the cost if the MOQ were waived. */
export function OrderQtyCell({ costing, unit }: { costing: QuoteCosting; unit: string }) {
  const worst = worstScenario(costing);
  return (
    <div>
      <p className="tabular-nums">
        {formatQty(costing.order_quantity, unit)}
        {costing.moq_applies && <span className="font-semibold text-peach-ink"> (MOQ)</span>}
      </p>
      {costing.moq_applies && worst && (
        <p className="text-xs text-muted">if MOQ waived {formatINR(worst.required_only.total_landed_inr)}</p>
      )}
    </div>
  );
}

export function ArrivalCell({ delivery }: { delivery: DeliveryEstimate }) {
  const { earliest_arrival: first, latest_arrival: last, buffer_days: buffer } = delivery;
  if (!last) return <Chip tone="neutral">Date unknown</Chip>;
  const range = first && first !== last ? `${formatDate(first)} – ${formatDate(last)}` : formatDate(last);
  return (
    <div>
      <p className="whitespace-nowrap tabular-nums">{range}</p>
      {buffer != null && <BufferChip days={buffer} />}
    </div>
  );
}

function BufferChip({ days }: { days: number }) {
  if (days < 0) return <Chip tone="rose">{plural(-days, "day")} late</Chip>;
  if (days <= 1) return <Chip tone="peach">{plural(days, "day")} buffer</Chip>;
  return <Chip tone="mint">{plural(days, "day")} buffer</Chip>;
}

export function CoaChip({ quote }: { quote?: Quote }) {
  if (!quote) return NA;
  return <Chip tone={COA_TONE[quote.coa_status]}>{labelOf(COA_OPTIONS, quote.coa_status)}</Chip>;
}

export function BrandChip({ quote }: { quote?: Quote }) {
  if (!quote) return NA;
  const status = labelOf(BRAND_STATUS_OPTIONS, quote.brand_status);
  return (
    <Chip tone={BRAND_TONE[quote.brand_status]} title={status}>
      {quote.brand_name ? `${quote.brand_name} · ${status.toLowerCase()}` : "Not named"}
    </Chip>
  );
}

/** Flag counts with words, never colour alone. Critical count always shown. */
export function FlagCounts({ analysis }: { analysis: QuoteAnalysis }) {
  const info = infoCount(analysis);
  return (
    <div className="flex flex-wrap gap-1">
      <Chip tone={analysis.critical_count > 0 ? "rose" : "mint"}>{analysis.critical_count} critical</Chip>
      {analysis.warning_count > 0 && <Chip tone="peach">{analysis.warning_count} warn</Chip>}
      {info > 0 && <Chip tone="sky">{info} info</Chip>}
    </div>
  );
}

/** Display score (0–100) with a small horizontal bar. */
export function ScoreBar({ analysis, top }: { analysis: QuoteAnalysis; top: boolean }) {
  const value = analysis.score.display;
  return (
    <div className="min-w-24">
      <p className="figure text-xl">{formatScore(value)}</p>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-2" aria-hidden="true">
        <div
          className={`h-full rounded-full ${top ? "bg-lavender-ink" : "bg-ink"}`}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}
