import { formatDateLong, formatINR, formatQty } from "@/lib/format";
import type { Requisition } from "@/lib/types";

interface Props {
  requisitions: Requisition[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** List of requisitions; the selected one is highlighted and announced as current. */
export function RequisitionSwitcher({ requisitions, selectedId, onSelect }: Props) {
  return (
    <ul className="space-y-2" aria-label="Requisitions">
      {requisitions.map((r) => {
        const selected = r.id === selectedId;
        return (
          <li key={r.id ?? r.pr_number}>
            <button
              type="button"
              onClick={() => r.id && onSelect(r.id)}
              aria-current={selected ? "true" : undefined}
              className={`w-full rounded-2xl border p-4 text-left transition-colors ${
                selected ? "border-ink bg-ink text-bg" : "border-line bg-surface hover:border-ink"
              }`}
            >
              <p className={`micro ${selected ? "text-bg opacity-80" : ""}`}>{r.pr_number}</p>
              <p className="mt-1 font-display text-lg font-bold leading-tight">{r.item_name}</p>
              <p className={`mt-1 text-xs ${selected ? "opacity-80" : "text-muted"}`}>
                {formatQty(r.required_quantity, r.unit)} · need by {formatDateLong(r.need_by_date)} ·{" "}
                {formatINR(r.approved_budget)}
              </p>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
