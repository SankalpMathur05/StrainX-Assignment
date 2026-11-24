// Every field of a requisition as a compact definition list (2 cols mobile, 4 desktop, 5 in print).
import { DASH, Detail, YesNoChip, orDash } from "@/components/details/DetailList";
import { formatDateLong, formatDateTime, formatINR, formatQty } from "@/lib/format";
import type { Requisition } from "@/lib/types";

export function RequisitionDetails({ requisition: r }: { requisition: Requisition }) {
  const notes = r.quality_notes.trim();
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-3 md:grid-cols-4 print:grid-cols-5 print:gap-y-1.5">
      <Detail label="PR number">{orDash(r.pr_number)}</Detail>
      <Detail label="PR date">{formatDateLong(r.date)}</Detail>
      <Detail label="Requested by">{orDash(r.requested_by)}</Detail>
      <Detail label="Delivery site">{orDash(r.site)}</Detail>
      <Detail label="Item">{orDash(r.item_name)}</Detail>
      <Detail label="Required quantity">
        <span className="tabular-nums">{formatQty(r.required_quantity, r.unit)}</span>
      </Detail>
      <Detail label="Need by">{formatDateLong(r.need_by_date)}</Detail>
      <Detail label="Approved budget">
        <span className="tabular-nums">{formatINR(r.approved_budget)}</span>
      </Detail>
      <Detail label="CoA mandatory">
        <YesNoChip value={r.coa_mandatory} />
      </Detail>
      <Detail label="Named brand required">
        <YesNoChip value={r.require_named_brand} />
      </Detail>
      <Detail label="Specification" className="col-span-2 print:col-span-2">
        <span className="whitespace-pre-wrap">{orDash(r.specification)}</span>
      </Detail>
      <Detail label="Quality notes" className="col-span-2 md:col-span-4 print:col-span-3">
        {notes ? (
          <span className="block whitespace-pre-wrap rounded-xl bg-peach px-3 py-2 text-peach-ink print:px-2 print:py-1">
            {notes}
          </span>
        ) : (
          DASH
        )}
      </Detail>
      <Stamp label="Created" iso={r.created_at} />
      <Stamp label="Last updated" iso={r.updated_at} />
    </dl>
  );
}

/** Record timestamp: small and muted on screen, left out of print to save space. */
function Stamp({ label, iso }: { label: string; iso: string | null | undefined }) {
  return (
    <div className="min-w-0 print:hidden">
      <dt className="micro">{label}</dt>
      <dd className="mt-0.5 text-xs text-muted">{formatDateTime(iso)}</dd>
    </div>
  );
}
