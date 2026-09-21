"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import CategoryChart from "@/components/CategoryChart";
import ClusterChart from "@/components/ClusterChart";
import DataTable, { type Column } from "@/components/DataTable";
import type { AnalyzeResponse, TransactionRow } from "@/lib/types";

type Tab = "categories" | "clusters" | "transactions";

function fmtNum(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function toCsv(rows: TransactionRow[]): string {
  const cols: (keyof TransactionRow)[] = [
    "date",
    "description",
    "amount",
    "category",
    "confidence",
    "cluster_label",
  ];
  const escape = (v: unknown) => {
    const s = String(v ?? "");
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [cols.join(",")];
  for (const row of rows) {
    lines.push(cols.map((c) => escape(row[c])).join(","));
  }
  return lines.join("\n");
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [useSample, setUseSample] = useState(true);
  const [nClusters, setNClusters] = useState(4);
  const [tab, setTab] = useState<Tab>("categories");
  const [lowOnly, setLowOnly] = useState(false);

  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!useSample && !file) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const form = new FormData();
      form.set("use_sample", String(useSample));
      form.set("n_clusters", String(nClusters));
      if (!useSample && file) form.set("file", file);

      setLoading(true);
      setError(null);
      fetch("/api/analyze", { method: "POST", body: form })
        .then(async (res) => {
          const json = await res.json();
          if (!res.ok) throw new Error(json.error ?? "Request failed");
          setData(json as AnalyzeResponse);
        })
        .catch((err: Error) => {
          setError(err.message);
          setData(null);
        })
        .finally(() => setLoading(false));
    }, 200);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [file, useSample, nClusters]);

  const clusterOrder = useMemo(
    () =>
      data
        ? [...data.clusters.summary]
            .sort((a, b) => a.cluster - b.cluster)
            .map((s) => s.label)
        : [],
    [data],
  );

  const transactionRows = useMemo(() => {
    if (!data) return [];
    return lowOnly ? data.rows.filter((r) => r.confidence < 0.5) : data.rows;
  }, [data, lowOnly]);

  const rowColumns: Column<TransactionRow>[] = [
    { key: "date", header: "Date" },
    { key: "description", header: "Description" },
    {
      key: "amount",
      header: "Amount",
      align: "right",
      format: (v) => fmtNum(v as number),
    },
    { key: "category", header: "Category" },
    {
      key: "confidence",
      header: "Confidence",
      align: "right",
      format: (v) => (v as number).toFixed(2),
    },
    { key: "cluster_label", header: "Cluster" },
  ];

  const clusterColumns: Column<AnalyzeResponse["clusters"]["summary"][number]>[] = [
    { key: "label", header: "Cluster" },
    { key: "transactions", header: "Transactions", align: "right" },
    {
      key: "total_spend",
      header: "Total spend",
      align: "right",
      format: (v) => fmtNum(v as number),
    },
    {
      key: "avg_amount",
      header: "Avg amount",
      align: "right",
      format: (v) => fmtNum(v as number),
    },
    {
      key: "weekend_share",
      header: "Weekend share",
      align: "right",
      format: (v) => (v as number).toFixed(2),
    },
    {
      key: "recurring_share",
      header: "Recurring share",
      align: "right",
      format: (v) => (v as number).toFixed(2),
    },
    { key: "top_category", header: "Top category" },
  ];

  function download() {
    if (!data) return;
    const csv = toCsv(data.rows);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "categorized_transactions.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="mx-auto flex max-w-[1400px] gap-8 p-6 lg:p-10">
      <aside className="w-64 shrink-0">
        <h2 className="mb-4 text-lg font-semibold">Input</h2>

        <label className="mb-1 block text-sm" style={{ color: "#c3c2b7" }}>
          Statement CSV
        </label>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => {
            const f = e.target.files?.[0] ?? null;
            setFile(f);
            if (f) setUseSample(false);
          }}
          className="mb-4 block w-full cursor-pointer rounded-md border p-2 text-xs file:mr-2 file:rounded file:border-0 file:bg-white/10 file:px-2 file:py-1 file:text-xs"
          style={{ borderColor: "rgba(255,255,255,0.1)" }}
        />

        <label className="mb-4 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={useSample}
            onChange={(e) => setUseSample(e.target.checked)}
          />
          Use the bundled sample statement
        </label>

        <label className="mb-1 block text-sm" style={{ color: "#c3c2b7" }}>
          Spend clusters: <span className="tabular">{nClusters}</span>
        </label>
        <input
          type="range"
          min={2}
          max={8}
          value={nClusters}
          onChange={(e) => setNClusters(Number(e.target.value))}
          className="mb-4 w-full"
        />

        <p className="text-xs" style={{ color: "#898781" }}>
          CSV needs columns: <code>date</code>, <code>description</code>,{" "}
          <code>amount</code>.
        </p>
      </aside>

      <main className="min-w-0 flex-1">
        <h1 className="text-3xl font-bold">
          Smart Expense Categorizer + Spend Clusters
        </h1>
        <p className="mb-6 mt-1 text-sm" style={{ color: "#898781" }}>
          Naive Bayes labels each transaction; K-Means groups your spending
          behaviour.
        </p>

        {error && (
          <div
            className="mb-6 rounded-md border px-4 py-3 text-sm"
            style={{ borderColor: "#e66767", color: "#e66767" }}
          >
            {error}
          </div>
        )}

        {!error && !data && (
          <p style={{ color: "#898781" }}>
            {loading ? "Analyzing…" : "Upload a CSV or tick the sample box to get started."}
          </p>
        )}

        {data && (
          <>
            <div className="mb-6 grid grid-cols-3 gap-6">
              <Stat label="Transactions" value={fmtNum(data.metrics.transactions)} />
              <Stat label="Total spend" value={fmtNum(data.metrics.total_spend)} />
              <Stat
                label="Low-confidence rows"
                value={fmtNum(data.metrics.low_confidence)}
              />
            </div>

            <div
              className="mb-4 flex gap-6 border-b text-sm"
              style={{ borderColor: "rgba(255,255,255,0.1)" }}
            >
              {(
                [
                  ["categories", "Categories"],
                  ["clusters", "Clusters"],
                  ["transactions", "Transactions"],
                ] as [Tab, string][]
              ).map(([id, label]) => (
                <button
                  key={id}
                  onClick={() => setTab(id)}
                  className="-mb-px border-b-2 px-1 pb-2"
                  style={{
                    borderColor: tab === id ? "#3987e5" : "transparent",
                    color: tab === id ? "#ffffff" : "#898781",
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            {tab === "categories" && (
              <div className="flex flex-col gap-4">
                <CategoryChart data={data.categories} />
                <DataTable
                  rowKey={(r) => r.category}
                  columns={[
                    { key: "category", header: "Category" },
                    {
                      key: "total",
                      header: "Total",
                      align: "right",
                      format: (v) => fmtNum(v as number),
                    },
                  ]}
                  rows={data.categories}
                />
              </div>
            )}

            {tab === "clusters" && (
              <div className="flex flex-col gap-4">
                {data.clusters.silhouette !== null && (
                  <p className="text-xs" style={{ color: "#898781" }}>
                    Silhouette score: {data.clusters.silhouette.toFixed(3)}{" "}
                    (higher means better separated clusters)
                  </p>
                )}
                <DataTable
                  rowKey={(r) => String(r.cluster)}
                  columns={clusterColumns}
                  rows={data.clusters.summary}
                />
                <ClusterChart rows={data.rows} clusterOrder={clusterOrder} />
              </div>
            )}

            {tab === "transactions" && (
              <div className="flex flex-col gap-4">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={lowOnly}
                    onChange={(e) => setLowOnly(e.target.checked)}
                  />
                  Show only rows the model is unsure about
                </label>
                <DataTable
                  rowKey={(r, i) => `${r.date}-${r.description}-${i}`}
                  columns={rowColumns}
                  rows={transactionRows}
                />
                <button
                  onClick={download}
                  className="w-fit rounded-md px-4 py-2 text-sm font-medium"
                  style={{ background: "#3987e5", color: "white" }}
                >
                  Download categorized CSV
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-sm" style={{ color: "#898781" }}>
        {label}
      </div>
      <div className="tabular text-2xl font-semibold">{value}</div>
    </div>
  );
}
