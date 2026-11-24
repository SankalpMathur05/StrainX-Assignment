import { Suspense } from "react";
import { Dashboard } from "@/components/dashboard/Dashboard";
import { DashboardSkeleton } from "@/components/dashboard/DashboardSkeleton";

// Dashboard reads ?req= and ?run= with useSearchParams, which needs a Suspense boundary.
export default function HomePage() {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <Dashboard />
    </Suspense>
  );
}
