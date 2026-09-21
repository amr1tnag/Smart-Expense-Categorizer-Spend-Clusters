"use client";

import { useRef } from "react";
import ThemeToggle from "./ThemeToggle";

export type Source = "sample" | "file";

type Props = {
  source: Source;
  onSource: (s: Source) => void;
  file: File | null;
  onFile: (f: File | null) => void;
  clusters: number; // 0 = automatic
  onClusters: (n: number) => void;
};

export default function SourceBar({ source, onSource, file, onFile, clusters, onClusters }: Props) {
  const input = useRef<HTMLInputElement>(null);
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

      <div className="toolbar">
        <div className="seg" role="radiogroup" aria-label="Statement source">
          <button type="button" role="radio" aria-checked={source === "sample"} onClick={() => onSource("sample")}>
            Sample statement
          </button>
          <button type="button" role="radio" aria-checked={source === "file"} onClick={() => onSource("file")}>
            Your CSV
          </button>
        </div>

        {source === "file" && (
          <>
            <input
              ref={input}
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              tabIndex={-1}
              onChange={(e) => onFile(e.target.files?.[0] ?? null)}
            />
            <button type="button" className="file-btn" onClick={() => input.current?.click()}>
              {file ? file.name : "Choose a CSV"}
            </button>
          </>
        )}

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
    </header>
  );
}
