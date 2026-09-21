"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import Commitments from "@/components/Commitments";
import MonthChart from "@/components/MonthChart";
import Patterns from "@/components/Patterns";
import SourceBar, { type Source } from "@/components/SourceBar";
import SpendStrip from "@/components/SpendStrip";
import Transactions, { type Filter } from "@/components/Transactions";
import { dateRange, percent, rupees, spanWords } from "@/lib/format";
import type { AnalyzeResponse, CategoryId, CategoryTotal, Corrections, TransactionRow } from "@/lib/types";

const PHRASE: Record<CategoryId, string> = {
  travel: "travel",
  food: "food",
  shopping: "shopping",
  bills: "bills",
  entertainment: "entertainment",
  health: "health",
  rent: "rent",
  other: "cash, transfers and fees",
};

function takeaway(categories: CategoryTotal[]): string {
  const [a, b] = [...categories].sort((x, y) => y.total - x.total);
  if (!a) return "";
  const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
  if (!b || a.share >= 0.6) return `${cap(PHRASE[a.category])} took ${percent(a.share)} of it.`;
  // Sum the rounded shares so the sentence matches the legend beneath it.
  const combined = Math.round(a.share * 100) + Math.round(b.share * 100);
  return `${cap(PHRASE[a.category])} and ${PHRASE[b.category]} took ${combined}% of it.`;
}

function toCsv(rows: TransactionRow[]): string {
  const esc = (v: unknown) => {
    const s = String(v ?? "");
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const head = ["date", "description", "amount", "category", "confidence", "pattern", "repeats"];
  const lines = rows.map((r) =>
    [r.date, r.description, r.amount, r.category, r.confidence.toFixed(3), r.cluster_label, r.recurring].map(esc).join(","),
  );
  return [head.join(","), ...lines].join("\n");
}

export default function Home() {
  const [source, setSource] = useState<Source>("sample");
  const [file, setFile] = useState<File | null>(null);
  const [clusters, setClusters] = useState(0);
  const [corrections, setCorrections] = useState<Corrections>({});

  const [filter, setFilter] = useState<Filter>("all");
  const [category, setCategory] = useState<CategoryId | null>(null);
  const [pattern, setPattern] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    if (source === "file" && !file) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    const ctl = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      const form = new FormData();
      form.set("use_sample", String(source === "sample"));
      form.set("n_clusters", String(clusters));
      form.set(
        "corrections",
        JSON.stringify(Object.entries(corrections).map(([description, category]) => ({ description, category }))),
      );
      if (source === "file" && file) form.set("file", file);
      try {
        const res = await fetch("/api/analyze", { method: "POST", body: form, signal: ctl.signal });
        const text = await res.text();
        let json: { error?: string } & Partial<AnalyzeResponse>;
        try {
          json = JSON.parse(text);
        } catch {
          throw new Error("The analyzer sent back something unexpected. Try again in a moment.");
        }
        if (!res.ok) throw new Error(json.error ?? "The analyzer couldn't process that file.");
        setData(json as AnalyzeResponse);
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setError((e as Error).message);
        setData(null);
      } finally {
        if (!ctl.signal.aborted) setLoading(false);
      }
    }, 200);
    return () => {
      clearTimeout(timer);
      ctl.abort();
    };
  }, [source, file, clusters, corrections]);

  const resetView = useCallback(() => {
    setCorrections({});
    setFilter("all");
    setCategory(null);
    setPattern(null);
    setQuery("");
  }, []);

  const chooseSource = (s: Source) => {
    setSource(s);
    resetView();
  };
  const chooseFile = (f: File | null) => {
    setFile(f);
    resetView();
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) chooseFile(f);
  };

  const review = () => {
    setFilter("review");
    setCategory(null);
    setPattern(null);
    setQuery("");
    requestAnimationFrame(() => {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      document.getElementById("transactions")?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    });
  };

  const download = () => {
    if (!data) return;
    const url = URL.createObjectURL(new Blob([toCsv(data.rows)], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "categorized_transactions.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const headline = useMemo(() => {
    if (!data) return "";
    const { total_spend, date_from, date_to } = data.metrics;
    const span = date_from && date_to ? ` over ${spanWords(date_from, date_to)}` : "";
    return `You spent ${rupees(total_spend)}${span}. ${takeaway(data.categories)}`.trim();
  }, [data]);

  const stale = loading && data !== null;
  const range = data ? dateRange(data.metrics.date_from, data.metrics.date_to) : null;
  const unsure = data ? data.rows.filter((r) => r.low_confidence && !r.corrected).length : 0;

  return (
    <div className="shell">
      <SourceBar
        source={source}
        onSource={chooseSource}
        file={file}
        onFile={chooseFile}
        clusters={clusters}
        onClusters={setClusters}
      />

      {source === "file" && !file && (
        <div
          className="dropzone"
          data-over={dragging}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <h1>Drop in a bank statement</h1>
          <p>
            Any CSV with <code>date</code>, <code>description</code> and <code>amount</code> columns.
            The file is analyzed in memory and not saved.
          </p>
          <p>
            No statement handy?{" "}
            <a className="link-btn" href="/sample_statement.csv" download>
              Download a sample CSV
            </a>{" "}
            or{" "}
            <button type="button" className="link-btn" onClick={() => chooseSource("sample")}>
              use the built-in sample
            </button>
            .
          </p>
        </div>
      )}

      {error && (
        <div className="alert" role="alert">
          <strong>We couldn&apos;t analyze that file</strong>
          {error} Check that the first row has the headers <code>date</code>, <code>description</code> and{" "}
          <code>amount</code>, then try again.
        </div>
      )}

      {loading && !data && !error && !(source === "file" && !file) && (
        <div aria-busy="true" aria-label="Analyzing your statement" style={{ marginTop: 64 }}>
          <div className="skeleton" style={{ height: 120, maxWidth: 760 }} />
          <div className="skeleton" style={{ height: 56, marginTop: 36 }} />
          <div className="skeleton" style={{ height: 220, marginTop: 64 }} />
        </div>
      )}

      {data && (
        <main data-stale={stale} aria-busy={stale}>
          <section className="hero" aria-labelledby="headline">
            <h1 id="headline">{headline}</h1>
            <p className="hero-sub">
              {data.metrics.transactions} {data.metrics.transactions === 1 ? "transaction" : "transactions"}
              {range ? ` from ${range}` : ""}.{" "}
              {unsure > 0 ? (
                <>
                  The model is unsure about {unsure}.{" "}
                  <button type="button" className="link-btn" onClick={review}>
                    Review {unsure === 1 ? "it" : "them"}
                  </button>{" "}
                  and it will learn from your fixes.
                </>
              ) : (
                "The model is confident about every one."
              )}
              {data.evaluation && !data.corrections_applied
                ? ` Checked against the answer key, ${Math.round(data.evaluation.accuracy * 100)}% of these categories are right.`
                : ""}
            </p>
            <SpendStrip categories={data.categories} active={category} onSelect={setCategory} />
          </section>

          <div className="section two-col">
            <section aria-labelledby="months-h">
              <div className="section-head">
                <h2 id="months-h">Month by month</h2>
              </div>
              <MonthChart monthly={data.monthly} active={category} />
            </section>
            <section aria-labelledby="fixed-h">
              <div className="section-head">
                <h2 id="fixed-h">Fixed commitments</h2>
              </div>
              <Commitments items={data.recurring} monthlyTotal={data.metrics.recurring_monthly} />
            </section>
          </div>

          <section className="section" aria-labelledby="patterns-h">
            <div className="section-head">
              <h2 id="patterns-h">How you spend</h2>
              <p className="section-note">
                {data.clusters.k} patterns{data.clusters.auto ? ", picked automatically" : ""}
                {data.clusters.silhouette !== null
                  ? `. How clearly they separate: ${data.clusters.silhouette.toFixed(2)} out of 1`
                  : ""}
                . Select one to see its transactions.
              </p>
            </div>
            <Patterns patterns={data.clusters.summary} active={pattern} onSelect={setPattern} />
          </section>

          <section className="section" aria-labelledby="txn-h">
            <div className="section-head">
              <h2 id="txn-h">Transactions</h2>
              <p className="section-note">Change a category and the model relearns from it.</p>
            </div>
            <Transactions
              rows={data.rows}
              filter={filter}
              onFilter={setFilter}
              category={category}
              onCategory={setCategory}
              pattern={pattern}
              onPattern={setPattern}
              query={query}
              onQuery={setQuery}
              onCorrect={(description, cat) => setCorrections((c) => ({ ...c, [description]: cat }))}
              corrections={Object.keys(corrections).length}
              onResetCorrections={() => setCorrections({})}
              onDownload={download}
            />
          </section>

          <p className="footer">
            Categories come from a text model trained on synthetic Indian UPI and card statements. It reads
            merchant names, so a brand it has never seen can be wrong. Those rows are marked Check. Patterns
            group transactions by amount, weekday, day of month and whether a merchant is paid on a steady
            schedule.
          </p>
        </main>
      )}
    </div>
  );
}
