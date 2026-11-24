import { Skeleton } from "@/components/ui/States";

/** Placeholder with the dashboard's shape, shown while data loads. */
export function DashboardSkeleton() {
  return (
    <div className="space-y-10" aria-busy="true" aria-label="Loading comparison">
      <div className="card space-y-4 p-6">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-10 w-2/3" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-4 w-full max-w-3xl" />
      </div>
      <Skeleton className="h-28 w-full" />
      <div className="space-y-2">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    </div>
  );
}
