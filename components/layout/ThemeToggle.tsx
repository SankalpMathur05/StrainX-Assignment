"use client";

import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

// True only in the browser, so the toggle never renders a theme the server could not know.
const subscribe = () => () => {};
const useIsClient = () =>
  useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const isClient = useIsClient();
  const isDark = isClient && resolvedTheme === "dark";
  const next = isDark ? "light" : "dark";

  return (
    <button
      type="button"
      className="btn h-10 w-10 p-0"
      onClick={() => setTheme(next)}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    >
      {/* Sun when dark (click for light), moon when light. */}
      <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {isDark ? (
          <>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
          </>
        ) : (
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        )}
      </svg>
    </button>
  );
}
