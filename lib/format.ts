// Display helpers. All money is INR; Indian digit grouping (2,27,150) via the en-IN locale.

const MINUS = "−"; // typographic minus sign, reads better than a hyphen next to numbers

/** Rounds to paise so float noise (e.g. 227150.00000001) never shows up as decimals. */
function toPaise(n: number): number {
  return Math.round(n * 100) / 100;
}

/** "Rs 2,27,150" — two decimals only when the amount is not a whole rupee (or when asked). */
export function formatINR(n: number, decimals?: number): string {
  const abs = toPaise(Math.abs(n));
  const dp = decimals ?? (Number.isInteger(abs) ? 0 : 2);
  const body = abs.toLocaleString("en-IN", {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });
  const sign = n < 0 && abs !== 0 ? MINUS : "";
  return `${sign}Rs ${body}`;
}

/** Amount in its own currency: INR → "Rs 3,850", anything else → "USD 78" / "USD 78.50". */
export function formatMoney(n: number, currency: string): string {
  const code = currency.trim().toUpperCase() || "INR";
  if (code === "INR") return formatINR(n);
  const abs = toPaise(n);
  const dp = Number.isInteger(abs) ? 0 : 2;
  return `${code} ${abs.toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: dp })}`;
}

/** Plain number with Indian grouping and float noise trimmed: 1234.5 → "1,234.5". */
export function formatNumber(n: number): string {
  return toPaise(n).toLocaleString("en-IN");
}

/** Percent keeping up to two decimals: 18 → "18%", 12.5 → "12.5%". */
export function formatPctExact(n: number): string {
  return `${formatNumber(n)}%`;
}

/** Signed variance: "+Rs 27,150" when over, "−Rs 20,050" when under, "Rs 0" when exact. */
export function formatVariance(n: number, decimals?: number): string {
  const abs = toPaise(Math.abs(n));
  if (abs === 0) return "Rs 0";
  return `${n > 0 ? "+" : MINUS}${formatINR(abs, decimals)}`;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Parses "YYYY-MM-DD" as a calendar date (UTC) so time zones never shift the day. */
function parseISODate(iso: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return null;
  return new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
}

/** "2026-11-27" → "Fri 27 Nov". Returns "—" for empty input. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = parseISODate(iso);
  if (!d) return iso;
  return `${WEEKDAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

/** "2026-11-27" → "27 Nov 2026" (used where the year matters, e.g. history lists). */
export function formatDateLong(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = parseISODate(iso);
  if (!d) return iso;
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** ISO datetime → "24 Nov 2026, 17:04" in the viewer's local time. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}, ${hh}:${mm}`;
}

/** Quantity with unit: 25 + "kg" → "25 kg"; trims float noise. */
export function formatQty(n: number, unit: string): string {
  return `${toPaise(n).toLocaleString("en-IN")} ${unit}`;
}

/** Score for display: one decimal. */
export function formatScore(n: number): string {
  return n.toFixed(1);
}

/** Percent with no decimals: 0.3 → never; expects 0–100 input. */
export function formatPct(n: number): string {
  return `${Math.round(n)}%`;
}

/** "1 day" / "3 days". */
export function plural(n: number, word: string): string {
  return `${n} ${word}${Math.abs(n) === 1 ? "" : "s"}`;
}
