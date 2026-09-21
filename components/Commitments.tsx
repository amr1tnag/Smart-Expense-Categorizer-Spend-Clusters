"use client";

import { useState, type CSSProperties } from "react";
import { categoryColor } from "@/lib/categories";
import { cadenceLabel, rupees, shortDate } from "@/lib/format";
import type { RecurringPayment } from "@/lib/types";

const COLLAPSED = 6;

type Props = { items: RecurringPayment[]; monthlyTotal: number };

export default function Commitments({ items, monthlyTotal }: Props) {
  const [showAll, setShowAll] = useState(false);

  if (items.length === 0) {
    return (
      <p className="section-note">
        No repeating payments found yet. A merchant shows up here once it has been paid on a steady
        schedule, at least three times for variable bills or twice at the same amount.
      </p>
    );
  }

  const biggest = Math.max(...items.map((i) => i.monthly_equivalent));
  const shown = showAll ? items : items.slice(0, COLLAPSED);
  const hidden = items.length - shown.length;

  return (
    <div>
      <ul className="commit-list">
        {shown.map((it) => (
          <li
            key={it.merchant}
            className="commit"
            style={{ "--c": categoryColor(it.category ?? "other") } as CSSProperties}
          >
            <span className="swatch" aria-hidden="true" />
            <span className="name">{it.merchant}</span>
            <span className="amt num">{rupees(it.typical_amount)}</span>
            <span className="meta">
              {cadenceLabel(it.cadence_days)}, paid {it.payments} times, last on{" "}
              {shortDate(it.last_date)}
            </span>
            <span className="bar" aria-hidden="true">
              <i style={{ width: `${Math.max(3, (it.monthly_equivalent / biggest) * 100)}%` }} />
            </span>
          </li>
        ))}
      </ul>
      {items.length > COLLAPSED && (
        <button
          type="button"
          className="link-btn"
          style={{ marginTop: 12 }}
          aria-expanded={showAll}
          onClick={() => setShowAll((v) => !v)}
        >
          {showAll ? "Show fewer" : `Show ${hidden} more`}
        </button>
      )}
      <p className="commit-total">
        {items.length === 1 ? "That comes" : `All ${items.length} together come`} to about{" "}
        <strong className="num">{rupees(monthlyTotal)}</strong> a month before you buy anything else.
      </p>
    </div>
  );
}
