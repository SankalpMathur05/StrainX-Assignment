// Mobile view: one stacked card per quote with the essentials, details collapsed.
import {
  ArrivalCell,
  BrandChip,
  BudgetCell,
  CoaChip,
  FlagCounts,
  LandedCell,
  OrderQtyCell,
  PerUnitCell,
  QuoteIdentity,
  Rank,
  ScoreBar,
  TaxCell,
} from "@/components/dashboard/cells";
import { ScenarioBreakdown } from "@/components/dashboard/ScenarioBreakdown";
import { TextList } from "@/components/ui/TextList";
import { findQuote } from "@/lib/analysis";
import type { CompareResult, Quote } from "@/lib/types";

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="micro mb-1">{label}</p>
      <div className="text-sm">{children}</div>
    </div>
  );
}

export function QuoteCards({ result, quotes }: { result: CompareResult; quotes: Quote[] }) {
  const unit = result.requisition.unit;
  const topLabel = result.recommendation.quote_label;

  return (
    <ol className="space-y-3">
      {result.analyses.map((a) => {
        const quote = findQuote(a, quotes);
        const top = a.label === topLabel;
        return (
          <li key={a.quote_id ?? a.label} className={`card p-4 ${top ? "border-lavender-ink/40 bg-lavender/50" : ""}`}>
            <div className="flex items-start gap-3">
              <Rank rank={a.rank} top={top} />
              <div className="min-w-0 flex-1">
                <QuoteIdentity analysis={a} quote={quote} />
                {top && <p className="micro mt-1 text-lavender-ink">Top pick</p>}
              </div>
              <ScoreBar analysis={a} top={top} />
            </div>

            <div className="mt-4 grid grid-cols-2 gap-4">
              <Fact label="Landed (worst case)">
                <LandedCell costing={a.costing} />
              </Fact>
              <Fact label="vs Budget">
                <BudgetCell costing={a.costing} />
              </Fact>
              <Fact label="Arrival">
                <ArrivalCell delivery={a.delivery} />
              </Fact>
              <Fact label="Flags">
                <FlagCounts analysis={a} />
              </Fact>
            </div>

            <details className="mt-4 border-t border-line pt-3">
              <summary className="flex items-center gap-2 text-sm font-semibold">
                <span className="chevron inline-block transition-transform" aria-hidden="true">›</span>
                Cost breakdown & details
              </summary>
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Fact label="Landed / unit">
                    <PerUnitCell costing={a.costing} unit={unit} />
                  </Fact>
                  <Fact label="GST / IGST (potential ITC)">
                    <TaxCell costing={a.costing} />
                  </Fact>
                  <Fact label="Order qty">
                    <OrderQtyCell costing={a.costing} unit={unit} />
                  </Fact>
                  <Fact label="Payment">{quote?.payment_terms || "—"}</Fact>
                  <Fact label="CoA">
                    <CoaChip quote={quote} />
                  </Fact>
                  <Fact label="Brand">
                    <BrandChip quote={quote} />
                  </Fact>
                </div>
                <ScenarioBreakdown costing={a.costing} unit={unit} />
                <TextList title="Facts from the quote" items={a.facts} />
                <TextList title="Assumptions made" items={a.assumptions} />
              </div>
            </details>
          </li>
        );
      })}
    </ol>
  );
}
