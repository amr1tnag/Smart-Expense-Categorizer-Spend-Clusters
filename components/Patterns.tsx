import { categoryLabel } from "@/lib/categories";
import { percent, rupees } from "@/lib/format";
import type { ClusterSummary } from "@/lib/types";

type Props = {
  patterns: ClusterSummary[];
  active: string | null;
  onSelect: (label: string | null) => void;
};

function describe(p: ClusterSummary): string {
  const parts = [
    `${p.transactions} ${p.transactions === 1 ? "transaction" : "transactions"} averaging ${rupees(p.avg_amount)}.`,
    `${Math.round(p.weekend_share * 100)}% on a weekend.`,
  ];
  if (p.top_category !== "-") parts.push(`Mostly ${categoryLabel(p.top_category).toLowerCase()}.`);
  return parts.join(" ");
}

export default function Patterns({ patterns, active, onSelect }: Props) {
  return (
    <ul className="patterns">
      {patterns.map((p) => (
        <li key={p.cluster}>
          <button
            type="button"
            className="pattern"
            aria-pressed={active === p.label}
            onClick={() => onSelect(active === p.label ? null : p.label)}
          >
            <span className="title">{p.label}</span>
            <span className="desc">{describe(p)}</span>
            <span className="share num">
              <b>{percent(p.share)}</b>
              <span>of spend</span>
            </span>
            <span className="track" aria-hidden="true">
              <i style={{ width: `${Math.max(1, p.share * 100)}%` }} />
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
