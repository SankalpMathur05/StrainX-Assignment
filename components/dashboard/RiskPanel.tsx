// Per quote: flags grouped by severity, then the questions to send that supplier.
import { SeverityBadge } from "@/components/ui/Chip";
import { TextList } from "@/components/ui/TextList";
import { SEVERITY_ORDER } from "@/lib/labels";
import type { CompareResult, QuoteAnalysis } from "@/lib/types";

function QuoteRisks({ analysis }: { analysis: QuoteAnalysis }) {
  const groups = SEVERITY_ORDER.map((severity) => ({
    severity,
    flags: analysis.flags.filter((f) => f.severity === severity),
  })).filter((g) => g.flags.length > 0);

  return (
    <article className="card p-4 md:p-5 print:p-2">
      <h3 className="font-display text-lg font-bold">
        <span className="text-muted">P{analysis.rank}</span> {analysis.label} · {analysis.supplier_name}
      </h3>

      {groups.length === 0 ? (
        <p className="mt-2 text-sm text-mint-ink">No risks flagged.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {groups.flatMap((g) =>
            g.flags.map((flag, i) => (
              <li key={`${flag.code}-${i}`} className="flex items-start gap-2 text-sm">
                <span className="mt-0.5 shrink-0">
                  <SeverityBadge severity={g.severity} />
                </span>
                <span>{flag.message}</span>
              </li>
            )),
          )}
        </ul>
      )}

      {analysis.questions.length > 0 && (
        <div className="mt-4 border-t border-line pt-3">
          <TextList title={`Questions to ask ${analysis.supplier_name}`} items={analysis.questions} />
        </div>
      )}
    </article>
  );
}

export function RiskPanel({ result }: { result: CompareResult }) {
  return (
    <div className="space-y-3">
      <div className="grid gap-3 lg:grid-cols-2 print:grid-cols-2">
        {result.analyses.map((a) => (
          <QuoteRisks key={a.quote_id ?? a.label} analysis={a} />
        ))}
      </div>
      {result.global_assumptions.length > 0 && (
        <details className="card p-4 print:hidden">
          <summary className="flex items-center gap-2 text-sm font-semibold">
            <span className="chevron inline-block transition-transform" aria-hidden="true">›</span>
            Assumptions behind every figure ({result.global_assumptions.length})
          </summary>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted">
            {result.global_assumptions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
