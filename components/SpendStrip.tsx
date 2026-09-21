"use client";

import type { CSSProperties } from "react";
import { CATEGORY_LABEL, CATEGORY_ORDER, categoryColor } from "@/lib/categories";
import { percent, rupees } from "@/lib/format";
import type { CategoryId, CategoryTotal } from "@/lib/types";
import { useTooltip } from "./Tooltip";

type Props = {
  categories: CategoryTotal[];
  active: CategoryId | null;
  onSelect: (id: CategoryId | null) => void;
};

/** The whole statement as one bar: each category's width is its share of spend. */
export default function SpendStrip({ categories, active, onSelect }: Props) {
  const { bind, view } = useTooltip();
  const byId = new Map(categories.map((c) => [c.category, c]));
  const shown = CATEGORY_ORDER.map((id) => byId.get(id)).filter(
    (c): c is CategoryTotal => !!c && c.total > 0,
  );

  const style = (id: CategoryId): CSSProperties =>
    ({ "--c": categoryColor(id), "--on": `var(--on-${id})` }) as CSSProperties;

  const tipFor = (c: CategoryTotal) => (
    <>
      <div className="row">
        <strong>{CATEGORY_LABEL[c.category]}</strong>
        <span className="num">{rupees(c.total)}</span>
      </div>
      <div style={{ color: "var(--ink-3)" }}>
        {percent(c.share)} of spend across {c.count}{" "}
        {c.count === 1 ? "transaction" : "transactions"}
      </div>
    </>
  );

  const toggle = (id: CategoryId) => onSelect(active === id ? null : id);

  return (
    <div>
      <div
        className="strip"
        data-active={active ?? undefined}
        role="group"
        aria-label="Spend by category"
      >
        {shown.map((c) => (
          <button
            key={c.category}
            type="button"
            className="seg-cell"
            style={{ ...style(c.category), flex: `${c.share} 1 0` }}
            aria-pressed={active === c.category}
            aria-label={`${CATEGORY_LABEL[c.category]}, ${rupees(c.total)}, ${percent(c.share)} of spend`}
            onClick={() => toggle(c.category)}
            {...bind(tipFor(c))}
          >
            {c.share >= 0.13 && (
              <>
                {CATEGORY_LABEL[c.category]}
                <span className="pct num">{percent(c.share)}</span>
              </>
            )}
            {c.share >= 0.045 && c.share < 0.13 && (
              <span className="num">{percent(c.share)}</span>
            )}
          </button>
        ))}
      </div>

      <ul className="legend">
        {shown.map((c) => (
          <li key={c.category}>
            <button
              type="button"
              style={style(c.category)}
              aria-pressed={active === c.category}
              onClick={() => toggle(c.category)}
            >
              <span className="swatch" />
              <span>{CATEGORY_LABEL[c.category]}</span>
              <span className="amt num">{rupees(c.total)}</span>
              <span className="share num">{percent(c.share)}</span>
            </button>
          </li>
        ))}
      </ul>
      {view}
    </div>
  );
}
