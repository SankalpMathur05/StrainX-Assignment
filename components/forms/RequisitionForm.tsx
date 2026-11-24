"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { FormFields } from "@/components/forms/FormFields";
import { PasteToFill } from "@/components/forms/PasteToFill";
import { useDraftForm } from "@/components/forms/useDraftForm";
import { Notice } from "@/components/ui/Notice";
import { api, errorMessage } from "@/lib/api";
import { allFields, fromDraft, toDraft } from "@/lib/forms";
import { REQUISITION_DEFAULTS, REQUISITION_GROUPS } from "@/lib/formSpecs";
import type { Requisition } from "@/lib/types";

const FIELDS = allFields(REQUISITION_GROUPS);
const labelFor = (key: string) => FIELDS.find((f) => f.key === key)?.label ?? key;

/** Start with defaults, but leave quantity blank so the user has to enter it. */
const initialDraft = () => ({ ...toDraft(REQUISITION_DEFAULTS, FIELDS), required_quantity: "" });

export function RequisitionForm() {
  const router = useRouter();
  const form = useDraftForm(initialDraft, FIELDS);
  const [errors, setErrors] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const { value, errors: problems } = fromDraft<Requisition>(REQUISITION_DEFAULTS, form.draft, FIELDS);
    setErrors(problems);
    if (problems.length > 0) return;

    setSaving(true);
    try {
      const created = await api.createRequisition(value);
      router.push(created.id ? `/history?req=${encodeURIComponent(created.id)}` : "/history");
    } catch (err) {
      setErrors([errorMessage(err)]);
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <PasteToFill
        id="req-paste"
        label="Paste requisition text to autofill"
        placeholder="e.g. the email or note from the lab: item, quantity, spec, need-by date, budget…"
        extract={(text) => api.extractRequisition({ text })}
        onFields={(fields) => form.applyAI(fields)}
        labelFor={labelFor}
      />

      <form onSubmit={save} noValidate className="space-y-6">
        {REQUISITION_GROUPS.map((group) => (
          <fieldset key={group.title} className="card p-4 md:p-5">
            <legend className="micro px-1">{group.title}</legend>
            <FormFields idPrefix="req" fields={group.fields} draft={form.draft} aiFilled={form.aiFilled} onChange={form.setField} />
          </fieldset>
        ))}

        {errors.length > 0 && (
          <Notice tone="rose" title="Please fix:">
            <ul className="list-disc pl-5">
              {errors.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </Notice>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Save requisition"}
          </button>
          <p className="text-xs text-muted">Next: add supplier quotes to it in History.</p>
        </div>
      </form>
    </div>
  );
}
