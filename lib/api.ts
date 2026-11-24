// Typed fetch helpers for every route in docs/API_CONTRACT.md (base path /api/py).
// Non-2xx responses throw ApiError carrying the server's `detail` message.
import type {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  CompareRequest,
  CompareResult,
  ComparisonRun,
  ComparisonRunCreate,
  ExtractRequest,
  ExtractResponse,
  Health,
  InsightsResponse,
  Quote,
  Requisition,
  Weights,
} from "@/lib/types";

const BASE = "/api/py";

/** Body of POST /insights (defined in backend/app/models.py; not exported by lib/types.ts). */
export interface InsightsRequest {
  compare: CompareRequest;
}

/** Body of POST /requisitions/{id}/compare. */
export interface CompareOptions {
  weights?: Weights;
  reference_date?: string | null;
}

export class ApiError extends Error {
  /** HTTP status; 0 when the request never reached a server. */
  readonly status: number;
  /** True when the API looks unreachable (network error or the dev proxy failing). */
  readonly unreachable: boolean;

  constructor(message: string, status: number, unreachable = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.unreachable = unreachable;
  }
}

export const UNREACHABLE_MESSAGE = "Can't reach the API — start both servers with npm run dev.";

/** FastAPI sends `detail` as a string (404 etc.) or a list of validation errors (422). */
function describeDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        const loc = "loc" in item && Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "";
        return loc ? `${loc}: ${String(item.msg)}` : String(item.msg);
      }
      return String(item);
    });
    return parts.join("; ");
  }
  return null;
}

async function errorFromResponse(res: Response): Promise<ApiError> {
  const text = await res.text();
  try {
    const body: unknown = JSON.parse(text);
    if (body && typeof body === "object" && "detail" in body) {
      const message = describeDetail(body.detail);
      if (message) return new ApiError(message, res.status);
    }
  } catch {
    // Not JSON: in dev this is the Next.js proxy failing because FastAPI is not running.
    if (res.status >= 500) return new ApiError(UNREACHABLE_MESSAGE, res.status, true);
  }
  return new ApiError(`Request failed (${res.status} ${res.statusText})`, res.status);
}

async function request<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: init?.method ?? "GET",
      headers: init?.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(UNREACHABLE_MESSAGE, 0, true);
  }
  if (!res.ok) throw await errorFromResponse(res);
  return (await res.json()) as T;
}

const enc = encodeURIComponent;

export const api = {
  health: () => request<Health>("/health"),

  // Requisitions
  listRequisitions: () => request<Requisition[]>("/requisitions"),
  getRequisition: (id: string) => request<Requisition>(`/requisitions/${enc(id)}`),
  createRequisition: (body: Requisition) =>
    request<Requisition>("/requisitions", { method: "POST", body }),
  updateRequisition: (id: string, body: Requisition) =>
    request<Requisition>(`/requisitions/${enc(id)}`, { method: "PUT", body }),
  deleteRequisition: (id: string) =>
    request<{ deleted: boolean }>(`/requisitions/${enc(id)}`, { method: "DELETE" }),

  // Quotes
  listQuotes: (requisitionId: string) =>
    request<Quote[]>(`/requisitions/${enc(requisitionId)}/quotes`),
  createQuote: (requisitionId: string, body: Quote) =>
    request<Quote>(`/requisitions/${enc(requisitionId)}/quotes`, { method: "POST", body }),
  updateQuote: (id: string, body: Quote) =>
    request<Quote>(`/quotes/${enc(id)}`, { method: "PUT", body }),
  deleteQuote: (id: string) => request<{ deleted: boolean }>(`/quotes/${enc(id)}`, { method: "DELETE" }),

  // Comparison
  compare: (body: CompareRequest) => request<CompareResult>("/compare", { method: "POST", body }),
  compareRequisition: (requisitionId: string, body: CompareOptions) =>
    request<CompareResult>(`/requisitions/${enc(requisitionId)}/compare`, { method: "POST", body }),

  // Saved runs
  listComparisons: (requisitionId?: string) =>
    request<ComparisonRun[]>(
      requisitionId ? `/comparisons?requisition_id=${enc(requisitionId)}` : "/comparisons",
    ),
  createComparison: (body: ComparisonRunCreate) =>
    request<ComparisonRun>("/comparisons", { method: "POST", body }),
  getComparison: (id: string) => request<ComparisonRun>(`/comparisons/${enc(id)}`),

  // AI (always HTTP 200; check `available`)
  getChat: (requisitionId: string) =>
    request<ChatMessage[]>(`/requisitions/${enc(requisitionId)}/chat`),
  sendChat: (body: ChatRequest) => request<ChatResponse>("/chat", { method: "POST", body }),
  extractRequisition: (body: ExtractRequest) =>
    request<ExtractResponse>("/extract/requisition", { method: "POST", body }),
  extractQuote: (body: ExtractRequest) =>
    request<ExtractResponse>("/extract/quote", { method: "POST", body }),
  insights: (body: InsightsRequest) =>
    request<InsightsResponse>("/insights", { method: "POST", body }),
};

/** Message for any thrown value, used by error states. */
export function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return String(err);
}

/** True when the error means "the backend is not running". */
export function isUnreachable(err: unknown): boolean {
  return err instanceof ApiError && err.unreachable;
}
