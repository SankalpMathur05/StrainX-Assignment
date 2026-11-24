import type { Tone } from "@/lib/labels";
import { TONE_CLASS } from "@/components/ui/Chip";

interface NoticeProps {
  tone?: Tone;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

/** Calm inline note (sky by default) for setup messages, AI caveats and form feedback. */
export function Notice({ tone = "sky", title, children, className = "" }: NoticeProps) {
  return (
    <div role="note" className={`rounded-xl px-4 py-3 text-sm ${TONE_CLASS[tone]} ${className}`}>
      {title && <p className="mb-1 font-semibold">{title}</p>}
      <div className="leading-relaxed">{children}</div>
    </div>
  );
}
