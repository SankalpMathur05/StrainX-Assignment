import { formatDateLong, formatMoney } from "@/lib/format";
import { PRICING_UNIT_OPTIONS, SOURCE_OPTIONS, labelOf } from "@/lib/labels";
import type { Quote } from "@/lib/types";

interface Props {
  quotes: Quote[];
  onView: (quote: Quote) => void;
  onEdit: (quote: Quote) => void;
  onDelete: (quote: Quote) => void;
}

/** "Rs 3,850 per pack" or "USD 78 per kg" — the price as the supplier wrote it. */
function priceText(q: Quote): string {
  return `${formatMoney(q.price, q.currency)} ${labelOf(PRICING_UNIT_OPTIONS, q.pricing_unit).toLowerCase()}`;
}

export function QuotesTable({ quotes, onView, onEdit, onDelete }: Props) {
  if (quotes.length === 0) {
    return <p className="card p-6 text-sm text-muted">No quotes yet. Add the first one — paste the supplier&apos;s message and let AI fill the form.</p>;
  }
  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead>
          <tr className="border-b border-line">
            {["Quote", "Price", "Received via", "Valid until", ""].map((h, i) => (
              <th key={i} scope="col" className="micro px-4 py-3 font-semibold">
                {h || <span className="sr-only">Actions</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {quotes.map((q) => (
            <tr key={q.id ?? q.label} className="border-b border-line last:border-0">
              <th scope="row" className="px-4 py-3 text-left font-normal">
                <span className="mr-2 inline-flex h-5 min-w-5 items-center justify-center rounded bg-ink px-1 font-display text-xs font-bold text-bg">
                  {q.label || "?"}
                </span>
                <span className="font-semibold">{q.supplier_name}</span>
                {q.supplier_location && <span className="text-muted"> · {q.supplier_location}</span>}
              </th>
              <td className="px-4 py-3 tabular-nums">{priceText(q)}</td>
              <td className="px-4 py-3">{labelOf(SOURCE_OPTIONS, q.source_channel)}</td>
              <td className="px-4 py-3">{q.valid_until ? formatDateLong(q.valid_until) : "Not stated"}</td>
              <td className="px-4 py-3">
                <div className="flex justify-end gap-2">
                  <button type="button" className="btn h-9 px-3" onClick={() => onView(q)} aria-label={`View all details of quote ${q.label} from ${q.supplier_name}`}>
                    View
                  </button>
                  <button type="button" className="btn h-9 px-3" onClick={() => onEdit(q)} aria-label={`Edit quote ${q.label} from ${q.supplier_name}`}>
                    Edit
                  </button>
                  <button type="button" className="btn btn-danger h-9 px-3" onClick={() => onDelete(q)} aria-label={`Delete quote ${q.label} from ${q.supplier_name}`}>
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
