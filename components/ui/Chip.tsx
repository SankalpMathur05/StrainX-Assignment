import type { Tone } from "@/lib/labels";
import type { Severity } from "@/lib/types";
import { SEVERITY_LABEL, SEVERITY_TONE } from "@/lib/labels";

// Full class strings (not built from fragments) so Tailwind can see them at build time.
export const TONE_CLASS: Record<Tone, string> = {
  mint: "bg-mint text-mint-ink",
  lavender: "bg-lavender text-lavender-ink",
  peach: "bg-peach text-peach-ink",
  sky: "bg-sky text-sky-ink",
  rose: "bg-rose text-rose-ink",
  neutral: "bg-surface-2 text-ink",
};

interface ChipProps {
  tone: Tone;
  children: React.ReactNode;
  title?: string;
  className?: string;
}

/** Small pill with a pastel tone. Always carries text, never colour alone. */
export function Chip({ tone, children, title, className = "" }: ChipProps) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold leading-4 ${TONE_CLASS[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

/** Severity label in its colour, e.g. "CRITICAL" on rose. */
export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Chip tone={SEVERITY_TONE[severity]} className="uppercase tracking-[0.08em]">
      {SEVERITY_LABEL[severity]}
    </Chip>
  );
}
