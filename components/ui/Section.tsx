interface SectionProps {
  /** Two-digit index shown before the title, e.g. "01". */
  index?: string;
  title: string;
  /** Optional controls shown on the right of the heading. */
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  id?: string;
}

/** Page section with a heavy top rule and an uppercase display heading. */
export function Section({ index, title, actions, children, className = "", id }: SectionProps) {
  const headingId = id ? `${id}-heading` : undefined;
  return (
    <section id={id} aria-labelledby={headingId} className={`border-t-2 border-ink pt-4 ${className}`}>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <h2 id={headingId} className="flex items-baseline gap-3 font-display text-xl font-bold uppercase tracking-tight md:text-2xl">
          {index && <span className="text-sm font-semibold text-muted tabular-nums">{index}</span>}
          {title}
        </h2>
        {actions}
      </div>
      {children}
    </section>
  );
}
