"use client";

import { useEffect, useState } from "react";
import { weightTotal } from "@/lib/analysis";
import { api } from "@/lib/api";
import { DEFAULT_WEIGHTS, type CompareResult, type Quote, type Requisition, type Weights } from "@/lib/types";

const DEBOUNCE_MS = 250;

/**
 * Loads everything the dashboard needs and re-runs the comparison when inputs change.
 *  1. Bootstrap: requisitions list, optional saved run (?run=) for weights + date, then quotes.
 *  2. Compare: POST /requisitions/{id}/compare, debounced 250 ms after any slider/date change.
 */
export function useDashboardData(reqParam: string | null, runParam: string | null) {
  const [requisitions, setRequisitions] = useState<Requisition[] | null>(null);
  const [requisitionId, setRequisitionId] = useState<string | null>(null);
  const [quotes, setQuotes] = useState<Quote[] | null>(null);
  const [weights, setWeights] = useState<Weights>(DEFAULT_WEIGHTS);
  const [asOf, setAsOf] = useState<string | null>(null); // null = server's default reference date
  const [result, setResult] = useState<CompareResult | null>(null);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // 1. Bootstrap whenever the URL's requisition/run changes (or on retry).
  useEffect(() => {
    let cancelled = false;
    setError(null);
    setResult(null);
    setQuotes(null);

    async function load() {
      const [reqs, run] = await Promise.all([
        api.listRequisitions(),
        runParam ? api.getComparison(runParam) : Promise.resolve(null),
      ]);
      if (cancelled) return;
      const id = reqParam ?? run?.requisition_id ?? reqs[0]?.id ?? null;
      setRequisitions(reqs);
      setRequisitionId(id);
      if (run) {
        setWeights(run.weights);
        setAsOf(run.reference_date);
      }
      const qs = id ? await api.listQuotes(id) : [];
      if (!cancelled) setQuotes(qs);
    }

    load().catch((err: unknown) => {
      if (!cancelled) setError(err);
    });
    return () => {
      cancelled = true;
    };
  }, [reqParam, runParam, reloadKey]);

  // 2. Compare, debounced. Stale responses are ignored via `cancelled`.
  useEffect(() => {
    if (!requisitionId || !quotes || quotes.length === 0 || weightTotal(weights) === 0) {
      setComparing(false);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      setComparing(true);
      try {
        const res = await api.compareRequisition(requisitionId, { weights, reference_date: asOf });
        if (!cancelled) {
          setResult(res);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err);
      } finally {
        if (!cancelled) setComparing(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [requisitionId, quotes, weights, asOf]);

  return {
    requisitions,
    requisitionId,
    quotes,
    weights,
    setWeights,
    asOf,
    setAsOf,
    result,
    comparing,
    error,
    retry: () => setReloadKey((k) => k + 1),
  };
}
