"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { CATEGORY_LABEL, CATEGORY_ORDER, categoryColor, categoryLabel } from "@/lib/categories";
import { rupees, shortDate } from "@/lib/format";
import type { CategoryId, TransactionRow } from "@/lib/types";

export type Filter = "all" | "review" | "repeats";
type SortKey = "date" | "amount" | "confidence";
type Sort = { key: SortKey; dir: "asc" | "desc" };

const PAGE = 50;

type Props = {
  rows: TransactionRow[];
  filter: Filter;
  onFilter: (f: Filter) => void;
  category: CategoryId | null;
  onCategory: (c: CategoryId | null) => void;
  pattern: string | null;
  onPattern: (p: string | null) => void;
  query: string;
  onQuery: (q: string) => void;
  onCorrect: (description: string, category: CategoryId) => void;
  corrections: number;
  onResetCorrections: () => void;
  onDownload: () => void;
};

export default function Transactions(p: Props) {
  const [userSort, setUserSort] = useState<Sort | null>(null);
  const [limit, setLimit] = useState(PAGE);

  const sort: Sort = userSort ?? (p.filter === "review" ? { key: "confidence", dir: "asc" } : { key: "date", dir: "desc" });

  useEffect(() => setLimit(PAGE), [p.filter, p.category, p.pattern, p.query]);
  useEffect(() => setUserSort(null), [p.filter]);

  const counts = useMemo(
    () => ({
      all: p.rows.length,
      review: p.rows.filter((r) => r.low_confidence && !r.corrected).length,
      repeats: p.rows.filter((r) => r.recurring).length,
    }),
    [p.rows],
  );

  const visible = useMemo(() => {
    const q = p.query.trim().toLowerCase();
    const list = p.rows.filter(
      (r) =>
        (p.filter === "all" ||
          (p.filter === "review" && r.low_confidence && !r.corrected) ||
          (p.filter === "repeats" && r.recurring)) &&
        (!p.category || r.category === p.category) &&
        (!p.pattern || r.cluster_label === p.pattern) &&
        (!q || r.description.toLowerCase().includes(q)),
    );
    const sign = sort.dir === "asc" ? 1 : -1;
    const value = (r: TransactionRow) =>
      sort.key === "amount" ? r.abs_amount : sort.key === "confidence" ? r.confidence : r.date;
    return [...list].sort((a, b) => {
      const va = value(a);
      const vb = value(b);
      return va < vb ? -sign : va > vb ? sign : 0;
    });
  }, [p.rows, p.filter, p.category, p.pattern, p.query, sort]);

  const multiYear = new Set(p.rows.map((r) => r.date.slice(0, 4))).size > 1;

  function header(label: string, key: SortKey, right = false) {
    const on = sort.key === key;
    return (
      <th className={right ? "r" : undefined} aria-sort={on ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}>
        <button
          type="button"
          onClick={() => setUserSort({ key, dir: on && sort.dir === "desc" ? "asc" : "desc" })}
        >
          {label}
          {on ? (sort.dir === "asc" ? " ↑" : " ↓") : ""}
        </button>
      </th>
    );
  }

  const chips: [Filter, string][] = [
    ["all", "All"],
    ["review", "Needs a look"],
    ["repeats", "Repeats"],
  ];

  return (
    <div id="transactions">
      <div className="filters">
        {chips.map(([id, label]) => (
          <button
            key={id}
            type="button"
            className="chip"
            aria-pressed={p.filter === id}
            onClick={() => p.onFilter(id)}
          >
            {label}
            <span className="count num">{counts[id]}</span>
          </button>
        ))}
        {p.category && (
          <button type="button" className="chip" aria-pressed="true" onClick={() => p.onCategory(null)}>
            {CATEGORY_LABEL[p.category]}
            <span aria-hidden="true">×</span>
            <span className="sr-only">Clear category filter</span>
          </button>
        )}
        {p.pattern && (
          <button type="button" className="chip" aria-pressed="true" onClick={() => p.onPattern(null)}>
            {p.pattern}
            <span aria-hidden="true">×</span>
            <span className="sr-only">Clear pattern filter</span>
          </button>
        )}
        <input
          className="search"
          type="search"
          placeholder="Search descriptions"
          aria-label="Search descriptions"
          value={p.query}
          onChange={(e) => p.onQuery(e.target.value)}
        />
      </div>

      {p.corrections > 0 && (
        <div className="notice" role="status">
          <span>
            You have corrected {p.corrections} {p.corrections === 1 ? "transaction" : "transactions"}.
            The model learned from {p.corrections === 1 ? "it" : "them"} and updated similar ones.
          </span>
          <button type="button" className="link-btn" onClick={p.onResetCorrections}>
            Undo all corrections
          </button>
        </div>
      )}

      <div className="table-wrap">
        <table className="txn">
          <thead>
            <tr>
              {header("Date", "date")}
              <th>Description</th>
              <th>Category</th>
              {header("Amount", "amount", true)}
              {header("Confidence", "confidence")}
            </tr>
          </thead>
          <tbody>
            {visible.slice(0, limit).map((r, i) => (
              <tr key={`${r.date}|${r.description}|${r.amount}|${i}`}>
                <td className="date num">{shortDate(r.date, multiYear)}</td>
                <td className="desc" title={r.description}>
                  {r.description}
                  {r.recurring && (
                    <>
                      {" "}
                      <span className="badge plain">Repeats</span>
                    </>
                  )}
                </td>
                <td>
                  <label className="cat-select" style={{ "--c": categoryColor(r.category) } as CSSProperties}>
                    <span className="swatch" aria-hidden="true" />
                    <span className="sr-only">Category for {r.description}</span>
                    <select
                      value={r.category}
                      onChange={(e) => p.onCorrect(r.description, e.target.value as CategoryId)}
                    >
                      {CATEGORY_ORDER.map((id) => (
                        <option key={id} value={id}>
                          {categoryLabel(id)}
                        </option>
                      ))}
                    </select>
                  </label>
                </td>
                <td className="r num">{rupees(r.abs_amount)}</td>
                <td>
                  {r.corrected ? (
                    <span className="badge good">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                      You set this
                    </span>
                  ) : r.low_confidence ? (
                    <span className="badge">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M12 3 2 21h20L12 3Z" />
                        <path d="M12 10v5M12 18v.01" />
                      </svg>
                      Check, {Math.round(r.confidence * 100)}%
                    </span>
                  ) : (
                    <span className="conf num">
                      <span className="meter" aria-hidden="true">
                        <i style={{ width: `${r.confidence * 100}%` }} />
                      </span>
                      {Math.round(r.confidence * 100)}%
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={5} style={{ padding: 28, textAlign: "center", color: "var(--ink-2)" }}>
                  {p.filter === "review" && !p.category && !p.pattern && !p.query
                    ? "Nothing to check. The model is confident about every transaction."
                    : "No transactions match these filters."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {visible.length > limit && (
          <div className="more">
            <button type="button" className="btn" onClick={() => setLimit((n) => n + PAGE)}>
              Show {Math.min(PAGE, visible.length - limit)} more of {visible.length - limit}
            </button>
          </div>
        )}
      </div>

      <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end" }}>
        <button type="button" className="btn primary" onClick={p.onDownload}>
          Download categorized CSV
        </button>
      </div>
    </div>
  );
}
