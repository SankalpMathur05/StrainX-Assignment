// Desktop (md+) and print view: one row per quote, best rank first.
import {
  ArrivalCell,
  BrandChip,
  BudgetCell,
  CoaChip,
  FlagCounts,
  LandedCell,
  OrderQtyCell,
  PerUnitCell,
  PreTaxCell,
  QuoteIdentity,
  Rank,
  ScoreBar,
  TaxCell,
} from "@/components/dashboard/cells";
import { ScenarioBreakdown } from "@/components/dashboard/ScenarioBreakdown";
import { TextList } from "@/components/ui/TextList";
import { findQuote } from "@/lib/analysis";
import type { CompareResult, Quote } from "@/lib/types";

interface Props {
  result: CompareResult;
  quotes: Quote[];
}

const HEADERS = [
  "Pos",
  "Quote",
  "Landed (worst case)",
  "vs Budget",
  "Landed / unit",
  "Pre-tax",
  "GST / IGST (potential ITC)",
  "Order qty",
  "Arrival",
  "Payment",
  "CoA",
  "Brand",
  "Flags",
  "Score",
];

export function ComparisonTable({ result, quotes }: Props) {
  const unit = result.requisition.unit;
  const topLabel = result.recommendation.quote_label;

  return (
    <div>
      <div className="card overflow-x-auto print:overflow-visible print:rounded-none print:border-0">
        <table className="w-full min-w-[1100px] border-collapse text-left text-sm print:min-w-0 print:text-[8.5px]">
          <caption className="sr-only">
            Quotes ranked best first. Landed cost uses the worst-case tax reading at the order (MOQ) quantity.
          </caption>
          <thead>
            <tr className="border-b border-line">
              {HEADERS.map((h) => (
                <th key={h} scope="col" className="micro px-3 py-3 align-bottom font-semibold print:px-1 print:py-1">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.analyses.map((a) => {
              const quote = findQuote(a, quotes);
              const top = a.label === topLabel;
              return (
                <tr key={a.quote_id ?? a.label} className={`border-b border-line align-top last:border-0 ${top ? "bg-lavender/60" : ""}`}>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <Rank rank={a.rank} top={top} />
                  </td>
                  <th scope="row" className="px-3 py-3 text-left font-normal print:px-1 print:py-1">
                    <QuoteIdentity analysis={a} quote={quote} />
                    {top && <p className="micro mt-1 text-lavender-ink">Top pick</p>}
                  </th>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <LandedCell costing={a.costing} />
                  </td>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <BudgetCell costing={a.costing} />
                  </td>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <PerUnitCell costing={a.costing} unit={unit} />
                  </td>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <PreTaxCell costing={a.costing} />
                  </td>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <TaxCell costing={a.costing} />
                  </td>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <OrderQtyCell costing={a.costing} unit={unit} />
                  </td>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <ArrivalCell delivery={a.delivery} />
                  </td>
                  <td className="max-w-44 px-3 py-3 text-xs print:px-1 print:py-1">{quote?.payment_terms || "—"}</td>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <CoaChip quote={quote} />
                  </td>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <BrandChip quote={quote} />
                  </td>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <FlagCounts analysis={a} />
                  </td>
                  <td className="px-3 py-3 print:px-1 print:py-1">
                    <ScoreBar analysis={a} top={top} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <details className="card mt-3 p-4 print:hidden">
        <summary className="flex items-center gap-2 text-sm font-semibold">
          <span className="chevron inline-block transition-transform" aria-hidden="true">›</span>
          Cost build-up, facts & assumptions per quote
        </summary>
        <div className="mt-4 grid gap-6 lg:grid-cols-2">
          {result.analyses.map((a) => (
            <div key={a.quote_id ?? a.label}>
              <p className="mb-2 font-semibold">
                {a.label} · {a.supplier_name}
              </p>
              <div className="space-y-3">
                <ScenarioBreakdown costing={a.costing} unit={unit} />
                <TextList title="Facts from the quote" items={a.facts} />
                <TextList title="Assumptions made" items={a.assumptions} />
              </div>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
