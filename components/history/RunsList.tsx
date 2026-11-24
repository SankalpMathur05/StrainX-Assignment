import Link from "next/link";
import { weightsShort } from "@/lib/analysis";
import { formatDateLong, formatDateTime } from "@/lib/format";
import type { ComparisonRun } from "@/lib/types";

/** Saved comparison runs; "Open" restores the weights and "as of" date on the dashboard. */
export function RunsList({ runs }: { runs: ComparisonRun[] }) {
  if (runs.length === 0) {
    return <p className="card p-6 text-sm text-muted">No saved runs yet. Use “Save run” on the dashboard to keep a snapshot.</p>;
  }
  return (
    <ul className="space-y-2">
      {runs.map((run) => (
        <li key={run.id} className="card flex flex-wrap items-center gap-x-6 gap-y-2 p-4">
          <div className="min-w-0 flex-1">
            <p className="font-semibold">{run.label || "Untitled run"}</p>
            <p className="text-xs text-muted">
              Saved {formatDateTime(run.created_at)} · as of {formatDateLong(run.reference_date)}
            </p>
            <p className="text-xs text-muted">{weightsShort(run.weights)}</p>
          </div>
          <div>
            <p className="micro">Top pick</p>
            <p className="font-semibold">
              {run.top_pick_label ? `${run.top_pick_label} · ${run.top_pick_supplier ?? ""}` : "—"}
            </p>
          </div>
          <Link
            className="btn"
            href={`/?req=${encodeURIComponent(run.requisition_id)}&run=${encodeURIComponent(run.id)}`}
            aria-label={`Open run “${run.label || "Untitled run"}” in the dashboard`}
          >
            Open
          </Link>
        </li>
      ))}
    </ul>
  );
}
