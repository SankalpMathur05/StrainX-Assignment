import type { Metadata } from "next";
import { Suspense } from "react";
import { HistoryView } from "@/components/history/HistoryView";
import { Skeleton } from "@/components/ui/States";

export const metadata: Metadata = { title: "History · StrainX Quote Compare" };

// HistoryView reads ?req= with useSearchParams, which needs a Suspense boundary.
export default function HistoryPage() {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <HistoryView />
    </Suspense>
  );
}
