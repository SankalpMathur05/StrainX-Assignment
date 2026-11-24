// Collapsed "Full quote details" toggle used inside the dashboard's per-quote detail areas.
import { QuoteDetails } from "@/components/details/QuoteDetails";
import type { Quote } from "@/lib/types";

export function QuoteDetailsDisclosure({ quote }: { quote?: Quote }) {
  if (!quote) {
    return <p className="text-xs text-muted print:hidden">Stored quote not found, so its full details can&apos;t be shown.</p>;
  }
  return (
    <details className="rounded-xl border border-line p-3 print:hidden">
      <summary className="flex items-center gap-2 text-sm font-semibold">
        <span className="chevron inline-block transition-transform" aria-hidden="true">
          ›
        </span>
        Full quote details
        <span className="sr-only">
          {" "}
          for quote {quote.label}, {quote.supplier_name}
        </span>
      </summary>
      <div className="mt-3">
        <QuoteDetails quote={quote} />
      </div>
    </details>
  );
}
