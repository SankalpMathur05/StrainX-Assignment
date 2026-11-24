// Every field of one stored quote, grouped the way a buyer reads it, ending with the raw text
// exactly as the supplier sent it. Lays out in two columns once its container is wide enough.
import { Chip } from "@/components/ui/Chip";
import { DASH, Detail, DetailGroup, Muted, Panel, orDash } from "@/components/details/DetailList";
import {
  formatDateLong,
  formatDateTime,
  formatINR,
  formatMoney,
  formatNumber,
  formatPctExact,
  formatQty,
  plural,
} from "@/lib/format";
import {
  BRAND_STATUS_OPTIONS,
  BRAND_TONE,
  COA_OPTIONS,
  COA_TONE,
  LEAD_BASIS_OPTIONS,
  LEAD_START_OPTIONS,
  PRICING_BASIS_OPTIONS,
  PRICING_UNIT_OPTIONS,
  SOURCE_OPTIONS,
  TAX_OPTIONS,
  labelOf,
} from "@/lib/labels";
import type { Quote } from "@/lib/types";

const isImport = (q: Quote) => q.tax_treatment === "IMPORT_DUTY_IGST" || q.alt_tax_treatment === "IMPORT_DUTY_IGST";

/** "Rs 84 per USD", or "1 (already INR)" for rupee quotes. */
function fxText(q: Quote): string {
  const code = q.currency.trim().toUpperCase();
  if (!code || code === "INR") return q.fx_rate_to_inr === 1 ? "1 (already INR)" : formatNumber(q.fx_rate_to_inr);
  return `${formatINR(q.fx_rate_to_inr)} per ${code}`;
}

/** Import cost that may be left blank: blank means the engine applies its standard figure. */
function ImportCost({ value, quote }: { value: number | null; quote: Quote }) {
  if (value != null) return <span className="tabular-nums">{formatINR(value)}</span>;
  return isImport(quote) ? <Chip tone="sky">Engine default</Chip> : <Muted>Not applicable</Muted>;
}

/** "3 days", "28–35 days", "up to 10 days", or null when not stated. */
function leadTimeText(min: number | null, max: number | null): string | null {
  if (min != null && max != null) return min === max ? plural(min, "day") : `${min}–${max} days`;
  if (max != null) return `up to ${plural(max, "day")}`;
  if (min != null) return `at least ${plural(min, "day")}`;
  return null;
}

function SourceGroup({ q }: { q: Quote }) {
  return (
    <DetailGroup title="Source">
      <Detail label="Label">{orDash(q.label)}</Detail>
      <Detail label="Received via">{labelOf(SOURCE_OPTIONS, q.source_channel)}</Detail>
      <Detail label="Supplier">{orDash(q.supplier_name)}</Detail>
      <Detail label="Location">{orDash(q.supplier_location)}</Detail>
    </DetailGroup>
  );
}

function ProductGroup({ q }: { q: Quote }) {
  return (
    <DetailGroup title="Product & quality">
      <Detail label="Product as quoted" className="col-span-2">
        {orDash(q.product_description)}
      </Detail>
      <Detail label="Brand">{q.brand_name?.trim() ? q.brand_name : <Muted>Not named</Muted>}</Detail>
      <Detail label="Brand status">
        <Chip tone={BRAND_TONE[q.brand_status]}>{labelOf(BRAND_STATUS_OPTIONS, q.brand_status)}</Chip>
      </Detail>
      <Detail label="Certificate of Analysis" className="col-span-2">
        <Chip tone={COA_TONE[q.coa_status]}>{labelOf(COA_OPTIONS, q.coa_status)}</Chip>
      </Detail>
    </DetailGroup>
  );
}

function PriceGroup({ q }: { q: Quote }) {
  return (
    <DetailGroup title="Price">
      <Detail label="Price">
        <span className="tabular-nums">{formatMoney(q.price, q.currency)}</span>
      </Detail>
      <Detail label="Price is">{labelOf(PRICING_UNIT_OPTIONS, q.pricing_unit)}</Detail>
      <Detail label="FX rate to INR">{fxText(q)}</Detail>
      <Detail label="Pricing basis">{labelOf(PRICING_BASIS_OPTIONS, q.pricing_basis)}</Detail>
      <Detail label="Pack size">
        {q.pack_size_value != null ? formatQty(q.pack_size_value, q.pack_size_unit ?? "") : DASH}
      </Detail>
      <Detail label="Drum size">{q.drum_size_kg != null ? formatQty(q.drum_size_kg, "kg") : DASH}</Detail>
    </DetailGroup>
  );
}

function TaxGroup({ q }: { q: Quote }) {
  return (
    <DetailGroup title="Tax">
      <Detail label="Tax treatment">{labelOf(TAX_OPTIONS, q.tax_treatment)}</Detail>
      <Detail label="GST rate">{formatPctExact(q.gst_rate_pct)}</Detail>
      <Detail label="Alternate tax reading">
        {q.alt_tax_treatment ? labelOf(TAX_OPTIONS, q.alt_tax_treatment) : <Muted>None</Muted>}
      </Detail>
      <Detail label="Alternate GST rate">
        {q.alt_gst_rate_pct != null ? formatPctExact(q.alt_gst_rate_pct) : <Muted>{q.alt_tax_treatment ? "Not stated" : "None"}</Muted>}
      </Detail>
      <Detail label="Customs duty (imports)">{formatPctExact(q.customs_duty_pct)}</Detail>
      <Detail label="IGST (imports)">{formatPctExact(q.igst_rate_pct)}</Detail>
      <Detail label="Clearance fee">
        <ImportCost value={q.clearance_fee_inr} quote={q} />
      </Detail>
      <Detail label="Port-to-site transport">
        <ImportCost value={q.inland_transport_inr} quote={q} />
      </Detail>
    </DetailGroup>
  );
}

function FreightGroup({ q }: { q: Quote }) {
  return (
    <DetailGroup title="Freight">
      <Detail label="Freight">
        {q.freight_cost == null ? (
          <Chip tone="peach">Unknown / at actual</Chip>
        ) : (
          <span className="tabular-nums">{formatINR(q.freight_cost)}</span>
        )}
      </Detail>
      <Detail label="Free freight above">
        {q.freight_free_above_inr != null ? formatINR(q.freight_free_above_inr) : <Muted>None</Muted>}
      </Detail>
    </DetailGroup>
  );
}

function MoqGroup({ q }: { q: Quote }) {
  return (
    <DetailGroup title="Minimum order">
      <Detail label="MOQ" className="col-span-2">
        {q.moq_quantity != null ? formatQty(q.moq_quantity, q.moq_unit ?? "") : <Muted>None</Muted>}
      </Detail>
    </DetailGroup>
  );
}

function DeliveryGroup({ q }: { q: Quote }) {
  const lead = leadTimeText(q.lead_time_min_days, q.lead_time_max_days);
  return (
    <DetailGroup title="Delivery">
      <Detail label="Lead time">{lead ?? <Muted>Not stated</Muted>}</Detail>
      <Detail label="Counted in">{labelOf(LEAD_BASIS_OPTIONS, q.lead_time_basis)}</Detail>
      <Detail label="Clock starts">{labelOf(LEAD_START_OPTIONS, q.lead_time_starts)}</Detail>
      <Detail label="Extra transit">{plural(q.transit_days, "day")}</Detail>
    </DetailGroup>
  );
}

function PaymentGroup({ q }: { q: Quote }) {
  return (
    <DetailGroup title="Payment">
      <Detail label="Terms (as written)" className="col-span-2">
        {orDash(q.payment_terms)}
      </Detail>
      <Detail label="Advance">{formatPctExact(q.advance_pct)}</Detail>
      <Detail label="Paid before delivery">{formatPctExact(q.pre_delivery_pct)}</Detail>
      <Detail label="Credit">{plural(q.credit_days, "day")}</Detail>
    </DetailGroup>
  );
}

function ValidityGroup({ q }: { q: Quote }) {
  return (
    <DetailGroup title="Validity & record">
      <Detail label="Valid until" className="col-span-2">
        {q.valid_until ? formatDateLong(q.valid_until) : <Muted>Not stated</Muted>}
      </Detail>
      <Detail label="Created">
        <span className="text-xs text-muted">{formatDateTime(q.created_at)}</span>
      </Detail>
      <Detail label="Last updated">
        <span className="text-xs text-muted">{formatDateTime(q.updated_at)}</span>
      </Detail>
    </DetailGroup>
  );
}

function ContradictionsPanel({ items }: { items: string[] }) {
  return (
    <Panel title={`Contradictions (${items.length})`} className="@2xl:col-span-2">
      {items.length > 0 ? (
        <ul className="list-disc space-y-1 rounded-lg bg-peach py-2 pl-7 pr-3 text-sm text-peach-ink">
          {items.map((c, i) => (
            <li key={`${i}-${c}`}>{c}</li>
          ))}
        </ul>
      ) : (
        <p className="text-sm">
          <Muted>None noted</Muted>
        </p>
      )}
    </Panel>
  );
}

function RawText({ q }: { q: Quote }) {
  return (
    <Panel title="Raw text, exactly as received" className="@2xl:col-span-2">
      {q.raw_text ? (
        <pre
          tabIndex={0}
          aria-label={`Raw text of quote ${q.label} from ${q.supplier_name}`}
          className="max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-surface-2 p-3 font-mono text-xs leading-relaxed"
        >
          {q.raw_text}
        </pre>
      ) : (
        <p className="text-sm">
          <Muted>No raw text stored with this quote.</Muted>
        </p>
      )}
    </Panel>
  );
}

export function QuoteDetails({ quote: q }: { quote: Quote }) {
  return (
    <div className="@container">
      <div className="grid gap-3 @2xl:grid-cols-2">
        <SourceGroup q={q} />
        <ProductGroup q={q} />
        <PriceGroup q={q} />
        <TaxGroup q={q} />
        <FreightGroup q={q} />
        <MoqGroup q={q} />
        <DeliveryGroup q={q} />
        <PaymentGroup q={q} />
        <ValidityGroup q={q} />
        <Panel title="Notes">
          <p className="whitespace-pre-wrap text-sm">{q.notes.trim() ? q.notes : <Muted>None</Muted>}</p>
        </Panel>
        <ContradictionsPanel items={q.contradictions} />
        <RawText q={q} />
      </div>
    </div>
  );
}
