"use client";

import type { CSSProperties } from "react";
import { CATEGORY_LABEL, CATEGORY_ORDER, categoryColor } from "@/lib/categories";
import { monthLabel, rupees, rupeesCompact } from "@/lib/format";
import type { CategoryId, MonthTotal } from "@/lib/types";
import { useTooltip } from "./Tooltip";

/** Ticks at round steps (1, 2, 2.5 or 5 times a power of ten), topped by the first tick at or above the data. */
function niceScale(max: number): { top: number; ticks: number[] } {
  if (max <= 0) return { top: 1, ticks: [1] };
  const raw = max / 4;
  const p = 10 ** Math.floor(Math.log10(raw));
  const f = raw / p;
  const step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
  const n = Math.max(1, Math.ceil(max / step - 1e-9));
  return { top: step * n, ticks: Array.from({ length: n }, (_, i) => step * (i + 1)) };
}

type Props = { monthly: MonthTotal[]; active: CategoryId | null };

export default function MonthChart({ monthly, active }: Props) {
  const { bind, view } = useTooltip();
  if (monthly.length === 0) {
    return <p className="section-note">No dates could be read, so there is no monthly view.</p>;
  }

  const { top, ticks } = niceScale(Math.max(...monthly.map((m) => m.total)));
  const multiYear = new Set(monthly.map((m) => m.month.slice(0, 4))).size > 1;
  const present = CATEGORY_ORDER.filter((id) =>
    monthly.some((m) => (m.by_category[id] ?? 0) > 0),
  );

  return (
    <div>
      <div className="months">
        <div className="yaxis" aria-hidden="true">
          {ticks.map((t) => (
            <span key={t} style={{ bottom: `${(t / top) * 100}%` }} className="num">
              {rupeesCompact(t)}
            </span>
          ))}
        </div>

        <div className="plot">
          {ticks.map((t) => (
            <div key={t} className="gridline" aria-hidden="true" style={{ bottom: `${(t / top) * 100}%` }} />
          ))}
          <div className="cols" data-active={active ?? undefined}>
            {monthly.map((m) => (
              <div className="col" key={m.month}>
                <div className="stack" style={{ height: `${(m.total / top) * 100}%` }}>
                  <span className="col-total num" aria-hidden="true">
                    {rupeesCompact(m.total)}
                  </span>
                  {present.map((id) => {
                    const v = m.by_category[id] ?? 0;
                    if (v <= 0) return null;
                    return (
                      <button
                        key={id}
                        type="button"
                        className="cell"
                        data-on={active === id ? "" : undefined}
                        style={{ "--c": categoryColor(id), flex: `${v} 1 0` } as CSSProperties}
                        aria-label={`${monthLabel(m.month, multiYear)}, ${CATEGORY_LABEL[id]}, ${rupees(v)}`}
                        {...bind(
                          <>
                            <div className="row">
                              <strong>{monthLabel(m.month, multiYear)}</strong>
                              <span className="num">{rupees(m.total)}</span>
                            </div>
                            <div className="row" style={{ color: "var(--ink-2)" }}>
                              <span>{CATEGORY_LABEL[id]}</span>
                              <span className="num">{rupees(v)}</span>
                            </div>
                          </>,
                        )}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="xaxis">
          {monthly.map((m) => (
            <span key={m.month}>{monthLabel(m.month, multiYear)}</span>
          ))}
        </div>
      </div>

      <details className="data-table">
        <summary>Show the numbers as a table</summary>
        <div className="table-wrap" style={{ marginTop: 10 }}>
          <table className="txn" style={{ minWidth: 0 }}>
            <thead>
              <tr>
                <th>Month</th>
                {present.map((id) => (
                  <th key={id} className="r">
                    {CATEGORY_LABEL[id]}
                  </th>
                ))}
                <th className="r">Total</th>
              </tr>
            </thead>
            <tbody>
              {monthly.map((m) => (
                <tr key={m.month}>
                  <td>{monthLabel(m.month, multiYear)}</td>
                  {present.map((id) => (
                    <td key={id} className="r num">
                      {m.by_category[id] ? rupees(m.by_category[id]!) : "–"}
                    </td>
                  ))}
                  <td className="r num">
                    <strong>{rupees(m.total)}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      {view}
    </div>
  );
}
