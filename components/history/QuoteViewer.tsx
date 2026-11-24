"use client";

import { useEffect, useRef } from "react";
import { QuoteDetails } from "@/components/details/QuoteDetails";
import type { Quote, Requisition } from "@/lib/types";

interface Props {
  requisition: Requisition;
  quote: Quote;
  onClose: () => void;
  /** Switch from reading to editing this quote. */
  onEdit: () => void;
}

/** Read-only side drawer with every field of one quote (same modal pattern as QuoteEditor). */
export function QuoteViewer({ requisition, quote, onClose, onEdit }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  // Open as a modal on mount; the parent unmounts this component on close.
  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
  }, []);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-labelledby="quote-viewer-title"
      className="m-0 ml-auto h-dvh max-h-dvh w-full max-w-3xl overflow-y-auto bg-bg p-0 text-ink backdrop:bg-black/50"
    >
      <header className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 border-b border-line bg-bg/95 px-4 py-3 backdrop-blur md:px-6">
        <div className="min-w-0">
          <p className="micro">
            {requisition.pr_number} · {requisition.item_name}
          </p>
          <h2 id="quote-viewer-title" className="font-display text-xl font-bold">
            Quote {quote.label || "?"} · {quote.supplier_name}
          </h2>
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn" onClick={onEdit}>
            Edit
          </button>
          <button type="button" className="btn btn-primary" onClick={() => dialogRef.current?.close()}>
            Close
          </button>
        </div>
      </header>
      <div className="px-4 py-6 md:px-6">
        <QuoteDetails quote={quote} />
      </div>
    </dialog>
  );
}
