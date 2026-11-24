import { isUnreachable, errorMessage } from "@/lib/api";

/** Grey placeholder block while data loads. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`skeleton ${className}`} />;
}

/** Error panel. When the backend is down it shows the "start both servers" hint. */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const unreachable = isUnreachable(error);
  return (
    <div role="alert" className="card border-rose-ink/30 bg-rose p-6 text-rose-ink">
      <p className="micro text-rose-ink">{unreachable ? "API offline" : "Something went wrong"}</p>
      <p className="mt-2 font-display text-xl font-bold">
        {unreachable ? (
          <>
            Can&apos;t reach the API — start both servers with{" "}
            <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-base text-ink">npm run dev</code>.
          </>
        ) : (
          errorMessage(error)
        )}
      </p>
      {onRetry && (
        <button type="button" className="btn mt-4" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

/** Friendly empty state with an optional call to action. */
export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="card p-8 text-center">
      <p className="font-display text-xl font-bold">{title}</p>
      {children && <div className="mt-3 text-sm text-muted">{children}</div>}
    </div>
  );
}
