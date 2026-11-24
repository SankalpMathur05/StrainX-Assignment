"use client";

import { useState } from "react";
import { applyExtracted, type Draft, type FieldSpec } from "@/lib/forms";

/**
 * Draft state for a spec-driven form, plus the set of keys the AI filled.
 * Editing a field removes its AI highlight ("until edited").
 */
export function useDraftForm(initial: () => Draft, specs: FieldSpec[]) {
  const [draft, setDraft] = useState<Draft>(initial);
  const [aiFilled, setAiFilled] = useState<ReadonlySet<string>>(new Set());

  function setField(key: string, value: string | boolean) {
    setDraft((d) => ({ ...d, [key]: value }));
    // Freight's "unknown" checkbox key is `${key}__unknown`; editing it clears the freight highlight too.
    const base = key.split("__")[0];
    setAiFilled((s) => {
      if (!s.has(base)) return s;
      const next = new Set(s);
      next.delete(base);
      return next;
    });
  }

  /** Merges AI fields into the current draft; returns the merged draft for follow-up tweaks. */
  function applyAI(fields: Record<string, unknown>): { draft: Draft; filled: string[] } {
    const merged = applyExtracted(draft, fields, specs);
    setDraft(merged.draft);
    setAiFilled(new Set(merged.filled));
    return merged;
  }

  return { draft, setDraft, aiFilled, setField, applyAI };
}
