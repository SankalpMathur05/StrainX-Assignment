import type { Metadata } from "next";
import { RequisitionForm } from "@/components/forms/RequisitionForm";

export const metadata: Metadata = { title: "New requisition · StrainX Quote Compare" };

export default function NewRequisitionPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <p className="micro">Step 1 of 2</p>
      <h1 className="mt-1 font-display text-3xl font-bold tracking-tight md:text-5xl">New requisition</h1>
      <p className="mb-8 mt-2 text-muted">
        What is needed, by when and for how much. Quotes are added next and compared like-for-like.
      </p>
      <RequisitionForm />
    </div>
  );
}
