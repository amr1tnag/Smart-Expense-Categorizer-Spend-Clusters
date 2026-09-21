// Indian digit grouping (₹4,86,961) throughout: it's how the statements this
// app reads are written, and how their owners read numbers.
const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

export function rupees(n: number): string {
  return inr.format(Math.round(n));
}

/** ₹25k, ₹1.2L, ₹3.4Cr: axis ticks and tight labels. */
export function rupeesCompact(n: number): string {
  const abs = Math.abs(n);
  const trim = (x: number) => x.toFixed(x >= 10 ? 0 : 1).replace(/\.0$/, "");
  if (abs >= 1e7) return `₹${trim(n / 1e7)}Cr`;
  if (abs >= 1e5) return `₹${trim(n / 1e5)}L`;
  if (abs >= 1e3) return `₹${trim(n / 1e3)}k`;
  return `₹${Math.round(n)}`;
}

export function percent(share: number): string {
  const p = share * 100;
  return `${p >= 10 || p === 0 ? Math.round(p) : p.toFixed(1).replace(/\.0$/, "")}%`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2025-03-14" -> "14 Mar" (add the year when the range spans years). */
export function shortDate(iso: string, withYear = false): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return `${d} ${MONTHS[m - 1]}${withYear ? ` ${y}` : ""}`;
}

export function monthLabel(ym: string, withYear = false): string {
  const [y, m] = ym.split("-").map(Number);
  if (!y || !m) return ym;
  return withYear ? `${MONTHS[m - 1]} ${String(y).slice(2)}` : MONTHS[m - 1];
}

export function dateRange(from: string | null, to: string | null): string | null {
  if (!from || !to) return null;
  const sameYear = from.slice(0, 4) === to.slice(0, 4);
  return `${shortDate(from, !sameYear)} to ${shortDate(to, true)}`;
}

export function cadenceLabel(days: number): string {
  if (days >= 26 && days <= 35) return "Monthly";
  if (days >= 6 && days <= 8) return "Weekly";
  if (days >= 84 && days <= 98) return "Quarterly";
  return `Every ${Math.round(days)} days`;
}

export function spanWords(from: string | null, to: string | null): string {
  if (!from || !to) return "this statement";
  const days = (Date.parse(to) - Date.parse(from)) / 86_400_000 + 1;
  const months = days / 30.4;
  if (months < 1.2) return `${Math.round(days)} days`;
  const n = Math.round(months);
  const words = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"];
  return `${n <= 12 ? words[n] : n} months`;
}
