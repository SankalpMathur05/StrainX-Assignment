"use client";

import { useEffect, useRef, useState } from "react";
import { Notice } from "@/components/ui/Notice";
import { api, errorMessage } from "@/lib/api";
import type { ChatTurn, CompareRequest } from "@/lib/types";

interface Props {
  requisitionId: string;
  compare: CompareRequest;
}

/** A chat turn plus any numbers the server could not find in the calculation. */
interface Entry extends ChatTurn {
  ungrounded?: string[];
}

const HISTORY_TURNS = 10;

export function ChatWidget({ requisitionId, compare }: Props) {
  const [open, setOpen] = useState(false);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Load saved conversation for this requisition.
  useEffect(() => {
    let cancelled = false;
    api
      .getChat(requisitionId)
      .then((msgs) => {
        if (!cancelled) setEntries(msgs.map((m) => ({ role: m.role, content: m.content })));
      })
      .catch(() => {
        if (!cancelled) setEntries([]); // chat history is optional; the dashboard works without it
      });
    return () => {
      cancelled = true;
    };
  }, [requisitionId]);

  // Keep the newest message in view.
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [entries, open]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const message = draft.trim();
    if (!message || sending) return;

    const history: ChatTurn[] = entries.slice(-HISTORY_TURNS).map(({ role, content }) => ({ role, content }));
    setEntries((prev) => [...prev, { role: "user", content: message }]);
    setDraft("");
    setSending(true);
    setNotice(null);
    try {
      const res = await api.sendChat({ requisition_id: requisitionId, message, compare, history });
      if (res.available && res.reply) {
        setEntries((prev) => [...prev, { role: "assistant", content: res.reply, ungrounded: res.ungrounded_numbers }]);
      } else {
        setNotice(res.message ?? "The assistant is unavailable right now.");
      }
    } catch (err) {
      setNotice(errorMessage(err));
    } finally {
      setSending(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="btn btn-primary fixed bottom-4 right-4 z-40 shadow-lg print:hidden"
        aria-expanded="false"
        aria-controls="chat-panel"
      >
        Ask about these quotes
      </button>
    );
  }

  return (
    <section
      id="chat-panel"
      aria-label="Chat about these quotes"
      className="fixed inset-x-0 bottom-0 z-40 flex max-h-[75dvh] flex-col border-t border-line bg-surface shadow-2xl md:inset-x-auto md:bottom-4 md:right-4 md:w-[400px] md:rounded-2xl md:border print:hidden"
    >
      <header className="flex items-center justify-between border-b border-line px-4 py-3">
        <div>
          <p className="font-display font-bold">Ask about these quotes</p>
          <p className="text-xs text-muted">AI answers from the engine&apos;s numbers only</p>
        </div>
        <button type="button" className="btn h-9 px-3" onClick={() => setOpen(false)} aria-expanded="true" aria-controls="chat-panel">
          Close
        </button>
      </header>

      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3" aria-live="polite">
        {entries.length === 0 && (
          <p className="text-sm text-muted">Try: “Why is A ranked above D?” or “What if delivery matters most?”</p>
        )}
        {entries.map((entry, i) => (
          <div key={i} className={entry.role === "user" ? "flex justify-end" : ""}>
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${
                entry.role === "user" ? "bg-ink text-bg" : "bg-surface-2"
              }`}
            >
              <span className="sr-only">{entry.role === "user" ? "You: " : "Assistant: "}</span>
              {entry.content}
            </div>
            {entry.ungrounded && entry.ungrounded.length > 0 && (
              <Notice tone="peach" className="mt-1 max-w-[85%] text-xs">
                Check these numbers — not found in the calculation: {entry.ungrounded.join(", ")}
              </Notice>
            )}
          </div>
        ))}
        {sending && <p className="text-sm text-muted">Thinking…</p>}
        {notice && <Notice>{notice}</Notice>}
      </div>

      <form onSubmit={send} className="flex gap-2 border-t border-line p-3">
        <label htmlFor="chat-input" className="sr-only">
          Your question
        </label>
        <input
          id="chat-input"
          className="input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask a question…"
          autoComplete="off"
        />
        <button type="submit" className="btn btn-primary" disabled={sending || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  );
}
