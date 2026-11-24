"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { Toast } from "@/components/ui/Toast";
import { api, errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { CompareResult } from "@/lib/types";

interface Props {
  requisitionId: string;
  result: CompareResult;
}

type ToastState = { kind: "saved" | "error"; text: string } | null;

/** Copy summary, print / PDF, and save this run (weights + date) to history. */
export function ShareActions({ requisitionId, result }: Props) {
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);
  const closeToast = useCallback(() => setToast(null), []);

  async function copySummary() {
    try {
      await navigator.clipboard.writeText(result.summary_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setToast({ kind: "error", text: "Couldn't copy — your browser blocked clipboard access." });
    }
  }

  async function saveRun() {
    setSaving(true);
    const pick = result.recommendation.quote_label;
    try {
      await api.createComparison({
        requisition_id: requisitionId,
        weights: result.weights,
        reference_date: result.reference_date,
        label: `${pick ? `Top pick ${pick}` : "No pick"} · as of ${formatDate(result.reference_date)}`,
      });
      setToast({ kind: "saved", text: "Run saved." });
    } catch (err) {
      setToast({ kind: "error", text: `Couldn't save: ${errorMessage(err)}` });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-wrap gap-2 print:hidden">
      <button type="button" className="btn btn-primary" onClick={copySummary}>
        {copied ? "Copied" : "Copy for WhatsApp / Email"}
      </button>
      <button type="button" className="btn" onClick={() => window.print()}>
        Print / Export PDF
      </button>
      <button type="button" className="btn" onClick={saveRun} disabled={saving}>
        {saving ? "Saving…" : "Save run"}
      </button>
      {/* Screen readers hear the copy confirmation too. */}
      <span className="sr-only" aria-live="polite">
        {copied ? "Summary copied to clipboard" : ""}
      </span>
      {toast && (
        <Toast onClose={closeToast}>
          {toast.text}{" "}
          {toast.kind === "saved" && (
            <Link href={`/history?req=${encodeURIComponent(requisitionId)}`} className="font-semibold underline">
              View in History
            </Link>
          )}
        </Toast>
      )}
    </div>
  );
}
