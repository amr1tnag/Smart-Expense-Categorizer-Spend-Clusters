import type { CSSProperties } from "react";
import { CATEGORY_LABEL, CATEGORY_ORDER, categoryColor } from "@/lib/categories";

type DropProps = { title: string; dragging: boolean; onPick: () => void };

/** The place a statement goes. The strip is a legend of the eight categories, not data; it swells while a file is dragged over. */
export function DropArea({ title, dragging, onPick }: DropProps) {
  return (
    <div className="drop" data-over={dragging}>
      <div className="drop-head">
        <div>
          <h2 className="drop-title">{dragging ? "Let go to analyze it" : title}</h2>
          <p className="drop-sub">Drag a CSV anywhere on this page, or pick one from your computer.</p>
        </div>
        <button type="button" className="btn primary" onClick={onPick}>
          Choose a CSV
        </button>
      </div>

      <div className="drop-strip" aria-hidden="true">
        {CATEGORY_ORDER.map((id) => (
          <i key={id} style={{ "--c": categoryColor(id) } as CSSProperties} />
        ))}
      </div>
      <p className="drop-cap">Every transaction lands in one of eight groups:</p>
      <ul className="drop-legend">
        {CATEGORY_ORDER.map((id) => (
          <li key={id} style={{ "--c": categoryColor(id) } as CSSProperties}>
            <span className="swatch" aria-hidden="true" />
            {CATEGORY_LABEL[id]}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Landing({ dragging, onPick }: { dragging: boolean; onPick: () => void }) {
  return (
    <div className="landing">
      <section className="l-hero" aria-labelledby="landing-h">
        <h1 id="landing-h">
          <span>Drop in a statement.</span> <span>See where the money went.</span>
        </h1>
        <p className="l-sub">
          Works with any bank or UPI statement saved as a CSV. Each transaction gets a category, the payments
          that repeat every month are found, and anything the model isn&apos;t sure about is marked for you to
          check.
        </p>
      </section>

      <DropArea title="Drop your CSV here" dragging={dragging} onPick={onPick} />

      <section className="gets" aria-label="What you get">
        <div>
          <h3>Every transaction sorted</h3>
          <p>
            Food, travel, rent and five more groups. Merchants the model doesn&apos;t know are marked Check.
            Fix one and it learns from you.
          </p>
        </div>
        <div>
          <h3>Fixed payments, found</h3>
          <p>
            Rent, subscriptions and bills that repeat on a schedule, plus what they add up to in a month.
          </p>
        </div>
        <div>
          <h3>How you actually spend</h3>
          <p>
            Weekend splurges, routine weekday spending and big one-offs, grouped from the amount, the weekday
            and how often something repeats.
          </p>
        </div>
      </section>

      <section className="before">
        <div>
          <h2>What your CSV needs</h2>
          <table className="needs">
            <tbody>
              <tr>
                <th scope="row">
                  <code>date</code>
                </th>
                <td>Day-first like 14/03/2025, or 2025-03-14</td>
              </tr>
              <tr>
                <th scope="row">
                  <code>description</code>
                </th>
                <td>The narration exactly as your bank prints it</td>
              </tr>
              <tr>
                <th scope="row">
                  <code>amount</code>
                </th>
                <td>A number. Debits can be negative or positive</td>
              </tr>
            </tbody>
          </table>
          <p className="fine">Other columns are ignored, and header capitalization doesn&apos;t matter.</p>
        </div>

        <div>
          <h2>Getting a CSV</h2>
          <p>
            Most net banking sites can export a statement as CSV from the transactions or statements page. A PDF
            needs converting to CSV first.
          </p>
          <h2>Your file</h2>
          <p>It is uploaded only to build this page, then discarded. Nothing is stored.</p>
        </div>
      </section>
    </div>
  );
}
