"use client";

import { useEffect } from "react";

interface ToastProps {
  children: React.ReactNode;
  onClose: () => void;
  /** Auto-dismiss after this many ms (default 6 s). */
  duration?: number;
}

/** Small status message pinned bottom-left; announced politely to screen readers. */
export function Toast({ children, onClose, duration = 6000 }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [onClose, duration]);

  return (
    <div
      role="status"
      className="fixed bottom-20 left-4 right-4 z-50 flex md:bottom-4 items-center gap-3 rounded-2xl bg-ink px-4 py-3 text-sm text-bg shadow-lg md:right-auto md:max-w-md print:hidden"
    >
      <div className="flex-1">{children}</div>
      <button type="button" onClick={onClose} className="rounded px-1 text-lg leading-none" aria-label="Dismiss">
        ×
      </button>
    </div>
  );
}
