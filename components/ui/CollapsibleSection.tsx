interface CollapsibleSectionProps {
  /** Two-digit index shown before the title, e.g. "01". */
  index?: string;
  title: string;
  children: React.ReactNode;
  /** Starts expanded unless set to false. */
  defaultOpen?: boolean;
  className?: string;
  id?: string;
}

/** Same look as <Section> (heavy rule, uppercase heading) but the body folds away via <details>. */
export function CollapsibleSection({ index, title, children, defaultOpen = true, className = "", id }: CollapsibleSectionProps) {
  const headingId = id ? `${id}-heading` : undefined;
  return (
    <section id={id} aria-labelledby={headingId} className={`border-t-2 border-ink pt-4 ${className}`}>
      <details open={defaultOpen} className="group">
        <summary className="flex flex-wrap items-end justify-between gap-3">
          <h2 id={headingId} className="flex items-baseline gap-3 font-display text-xl font-bold uppercase tracking-tight md:text-2xl">
            {index && <span className="text-sm font-semibold text-muted tabular-nums">{index}</span>}
            {title}
          </h2>
          {/* Visual hint only; the summary already exposes expanded/collapsed to assistive tech. */}
          <span className="micro flex items-center gap-1.5 pb-1 print:hidden" aria-hidden="true">
            <span className="group-open:hidden">Show</span>
            <span className="hidden group-open:inline">Hide</span>
            <span className="chevron inline-block text-base leading-none transition-transform">›</span>
          </span>
        </summary>
        <div className="mt-4 print:mt-2">{children}</div>
      </details>
    </section>
  );
}
