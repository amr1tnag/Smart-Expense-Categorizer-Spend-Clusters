"use client";

import ThemeToggle from "./ThemeToggle";

type Props = {
  fileName: string | null;
  onPick: () => void;
  clusters: number; // 0 = automatic
  onClusters: (n: number) => void;
};

export default function SourceBar({ fileName, onPick, clusters, onClusters }: Props) {
  const manual = clusters > 0;

  return (
    <header>
      <div className="topbar">
        <span className="wordmark">
          <svg width="26" height="14" viewBox="0 0 26 14" aria-hidden="true">
            <rect x="0" y="0" width="12" height="14" rx="3" fill="var(--cat-rent)" />
            <rect x="14" y="0" width="7" height="14" rx="2" fill="var(--cat-food)" />
            <rect x="23" y="0" width="3" height="14" rx="1.5" fill="var(--cat-travel)" />
          </svg>
          Expense categorizer
        </span>
        <ThemeToggle />
      </div>

      {fileName && (
        <div className="toolbar">
          <button type="button" className="file-btn" onClick={onPick} title="Choose a different CSV">
            {fileName}
            <span style={{ color: "var(--ink-3)" }}>Change</span>
          </button>

          <div className="field">
            <span id="patterns-label">Spending patterns</span>
            <div className="seg" role="radiogroup" aria-labelledby="patterns-label">
              <button type="button" role="radio" aria-checked={!manual} onClick={() => onClusters(0)}>
                Auto
              </button>
              <button type="button" role="radio" aria-checked={manual} onClick={() => onClusters(manual ? clusters : 4)}>
                Choose
              </button>
            </div>
            {manual && (
              <div className="stepper" role="group" aria-label="Number of patterns">
                <button type="button" aria-label="Fewer patterns" disabled={clusters <= 2} onClick={() => onClusters(clusters - 1)}>
                  −
                </button>
                <output className="num" aria-live="polite">
                  {clusters}
                </output>
                <button type="button" aria-label="More patterns" disabled={clusters >= 8} onClick={() => onClusters(clusters + 1)}>
                  +
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
