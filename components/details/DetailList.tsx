// Small building blocks for read-only "every field" views: a labelled value (dt/dd),
// a titled panel, and a titled definition-list group. Shared by requisition and quote details.
import { Chip } from "@/components/ui/Chip";

export const DASH = "—";

/** The text itself, or an em dash when it is blank. */
export function orDash(value: string | null | undefined): string {
  return value != null && value.trim() !== "" ? value : DASH;
}

/** De-emphasised value, e.g. "Not stated" or "None". */
export function Muted({ children }: { children: React.ReactNode }) {
  return <span className="text-muted">{children}</span>;
}

/** Yes / No in words (never colour alone): lavender when the requirement is on. */
export function YesNoChip({ value }: { value: boolean }) {
  return <Chip tone={value ? "lavender" : "neutral"}>{value ? "Yes" : "No"}</Chip>;
}

interface DetailProps {
  label: string;
  children: React.ReactNode;
  /** Grid placement (e.g. column span) for the dt/dd pair. */
  className?: string;
}

/** One labelled value inside a <dl>: uppercase micro label over the value. */
export function Detail({ label, children, className = "" }: DetailProps) {
  return (
    <div className={`min-w-0 ${className}`}>
      <dt className="micro">{label}</dt>
      <dd className="mt-0.5 break-words text-sm">{children}</dd>
    </div>
  );
}

interface PanelProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

/** Bordered block with a micro heading; holds free-form content (lists, notes, raw text). */
export function Panel({ title, children, className = "" }: PanelProps) {
  return (
    <div className={`min-w-0 rounded-xl border border-line p-3 ${className}`}>
      <h3 className="micro mb-2">{title}</h3>
      {children}
    </div>
  );
}

/** Panel whose body is a two-column definition list of <Detail> items. */
export function DetailGroup({ title, children, className = "" }: PanelProps) {
  return (
    <Panel title={title} className={className}>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2">{children}</dl>
    </Panel>
  );
}
