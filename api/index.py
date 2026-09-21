"""FastAPI backend: categorize + cluster a statement CSV.

Reuses the same src/categorizer.py (TF-IDF + Naive Bayes) and
src/clusters.py (K-Means over spend-behaviour features) that power the
original Streamlit app, so the two front ends stay in lock-step.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import categorizer, clusters  # noqa: E402

app = FastAPI()

REQUIRED = {"date", "description", "amount"}
SAMPLE_PATH = ROOT / "data" / "seed_labeled.csv"

# Serverless instances are short-lived but Fluid Compute reuses warm ones
# across requests, so caching the trained pipeline on the module avoids
# retraining on every call without needing a writable filesystem.
_model = None


def get_model():
    global _model
    if _model is None:
        seed = pd.read_csv(SAMPLE_PATH)
        pipe, _, _ = categorizer.train(seed)
        _model = pipe
    return _model


@app.post("/api/analyze")
async def analyze(
    file: UploadFile | None = File(None),
    use_sample: str = Form("false"),
    n_clusters: int = Form(4),
):
    if file is not None and use_sample.lower() != "true":
        content = await file.read()
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as exc:  # noqa: BLE001
            return JSONResponse({"error": f"Could not read CSV: {exc}"}, status_code=400)
    else:
        df = pd.read_csv(SAMPLE_PATH).drop(columns=["category"])

    df.columns = [c.strip().lower() for c in df.columns]
    missing = REQUIRED - set(df.columns)
    if missing:
        return JSONResponse(
            {"error": f"Missing column(s): {', '.join(sorted(missing))}"},
            status_code=400,
        )
    if df.empty:
        return JSONResponse({"error": "The CSV has no rows."}, status_code=400)

    # Blank date/description cells load as NaN, which the JSON encoder rejects.
    df["date"] = df["date"].fillna("").astype(str)
    df["description"] = df["description"].fillna("").astype(str)

    amounts = pd.to_numeric(df["amount"], errors="coerce")
    bad = amounts.isna()
    if bad.any():
        first = int(bad.idxmax()) + 2  # +1 for 0-index, +1 for the header row
        return JSONResponse(
            {
                "error": (
                    f"{int(bad.sum())} row(s) have a non-numeric amount "
                    f"(first at CSV line {first})."
                )
            },
            status_code=400,
        )
    df["amount"] = amounts

    n_clusters = max(2, min(int(n_clusters), 8))

    model = get_model()
    preds = categorizer.predict(model, df["description"])
    df = df.reset_index(drop=True)
    df["category"] = preds["category"].values
    df["confidence"] = preds["confidence"].values

    labels, _, silhouette = clusters.fit_clusters(df, n_clusters=n_clusters)
    df["cluster"] = labels
    summary = clusters.describe_clusters(df, labels)
    cluster_names = dict(zip(summary["cluster"], summary["label"]))
    df["cluster_label"] = df["cluster"].map(cluster_names)

    spend = pd.to_numeric(df["amount"], errors="coerce").abs()

    by_cat = (
        df.assign(_amt=spend)
        .groupby("category", as_index=False)["_amt"]
        .sum()
        .rename(columns={"_amt": "total"})
        .sort_values("total", ascending=False)
    )

    rows = df.assign(_amt=spend)[
        ["date", "description", "amount", "_amt", "category", "confidence", "cluster_label"]
    ].rename(columns={"_amt": "abs_amount"})

    return {
        "metrics": {
            "transactions": int(len(df)),
            "total_spend": float(spend.sum()),
            "low_confidence": int((df["confidence"] < 0.5).sum()),
        },
        "categories": by_cat.to_dict(orient="records"),
        "clusters": {
            "silhouette": float(silhouette) if silhouette is not None else None,
            "summary": summary.to_dict(orient="records"),
        },
        "rows": rows.to_dict(orient="records"),
    }
