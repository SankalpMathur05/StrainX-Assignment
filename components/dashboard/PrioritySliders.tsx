"use client";

import { WEIGHT_KEYS, WEIGHT_LABELS, weightTotal } from "@/lib/analysis";
import { formatPct } from "@/lib/format";
import { DEFAULT_WEIGHTS, type Weights } from "@/lib/types";

interface Props {
  weights: Weights;
  onChange: (weights: Weights) => void;
}

/** Four 0–100 sliders. The engine normalises them, so the % share is what actually counts. */
export function PrioritySliders({ weights, onChange }: Props) {
  const total = weightTotal(weights);
  const isDefault = WEIGHT_KEYS.every((k) => weights[k] === DEFAULT_WEIGHTS[k]);

  return (
    <div className="card p-4 md:p-5">
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {WEIGHT_KEYS.map((key) => {
          const id = `weight-${key}`;
          const share = total > 0 ? (weights[key] / total) * 100 : 0;
          return (
            <div key={key}>
              <div className="flex items-baseline justify-between gap-2">
                <label htmlFor={id} className="text-sm font-semibold">
                  {WEIGHT_LABELS[key]}
                </label>
                <span className="figure text-lg">{formatPct(share)}</span>
              </div>
              <input
                id={id}
                type="range"
                min={0}
                max={100}
                step={1}
                value={weights[key]}
                onChange={(e) => onChange({ ...weights, [key]: Number(e.target.value) })}
                aria-valuetext={`${weights[key]} of 100, ${formatPct(share)} of total weight`}
                className="mt-2 w-full"
              />
              <p className="text-xs text-muted">Slider {weights[key]} / 100</p>
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
        <p className="text-xs text-muted">
          Shares are normalised to 100%. Penalties sit outside the sliders: each CRITICAL flag −30, each WARNING −5
          points.
        </p>
        <button type="button" className="btn" onClick={() => onChange({ ...DEFAULT_WEIGHTS })} disabled={isDefault}>
          Reset
        </button>
      </div>
      {total === 0 && (
        <p role="alert" className="mt-3 text-sm font-semibold text-rose-ink">
          Set at least one priority above 0 to rank the quotes.
        </p>
      )}
    </div>
  );
}
