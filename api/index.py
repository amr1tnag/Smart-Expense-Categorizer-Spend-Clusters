"""FastAPI backend: categorize + cluster a statement CSV.

Reuses the same src/categorizer.py (TF-IDF + ensemble classifier) and
src/clusters.py (K-Means over spend-behaviour features) that power the
original Streamlit app, so the two front ends stay in lock-step.
"""
from __future__ import annotations

import io
import json
import sys
from functools import lru_cache
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
SEED_PATH = ROOT / "data" / "seed_labeled.csv"
SAMPLE_PATH = ROOT / "data" / "sample_statement.csv"

MAX_CORRECTIONS = 200
# A correction is one row; repeating it makes a single fix outweigh the
# character n-gram noise of a merchant the model has never seen.
CORRECTION_WEIGHT = 5


class BadRequest(Exception):
    pass


@lru_cache(maxsize=1)
def seed_frame() -> pd.DataFrame:
    return pd.read_csv(SEED_PATH)


# Serverless instances are short-lived but Fluid Compute reuses warm ones
# across requests, so caching trained pipelines in memory avoids retraining on
# every call without needing a writable filesystem. Fitting takes ~0.5s, so the
# cache is keyed by the user's corrections and kept small.
@lru_cache(maxsize=16)
def get_model(corrections: tuple[tuple[str, str], ...] = ()):
    train = seed_frame()[["description", "category"]]
    if corrections:
        extra = pd.DataFrame(list(corrections), columns=["description", "category"])
        train = pd.concat([train] + [extra] * CORRECTION_WEIGHT, ignore_index=True)
    return categorizer.fit(train)


def parse_corrections(raw: str) -> tuple[tuple[str, str], ...]:
    try:
        items = json.loads(raw or "[]")
    except json.JSONDecodeError as exc:
        raise BadRequest("corrections must be a JSON list.") from exc
    if not isinstance(items, list) or len(items) > MAX_CORRECTIONS:
        raise BadRequest(f"corrections must be a list of at most {MAX_CORRECTIONS} items.")
    known = set(seed_frame()["category"].unique())
    seen: dict[str, str] = {}
    for item in items:
        desc = str(item.get("description", "")).strip() if isinstance(item, dict) else ""
        cat = item.get("category") if isinstance(item, dict) else None
        if not desc or cat not in known:
            raise BadRequest(f"Each correction needs a description and one of: {', '.join(sorted(known))}.")
        seen[desc] = cat  # last correction for a description wins
    return tuple(sorted(seen.items()))


def read_statement(content: bytes | None, use_sample: bool):
    if content is not None and not use_sample:
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as exc:  # noqa: BLE001
            raise BadRequest(f"Could not read CSV: {exc}") from exc
        truth = None
    else:
        df = pd.read_csv(SAMPLE_PATH)
        truth = df.pop("category")

    df.columns = [c.strip().lower() for c in df.columns]
    missing = REQUIRED - set(df.columns)
    if missing:
        raise BadRequest(f"Missing column(s): {', '.join(sorted(missing))}")
    if df.empty:
        raise BadRequest("The CSV has no rows.")

    # Blank date/description cells load as NaN, which the JSON encoder rejects.
    df["description"] = df["description"].fillna("").astype(str)
    amounts = pd.to_numeric(df["amount"], errors="coerce")
    bad = amounts.isna()
    if bad.any():
        first = int(bad.to_numpy().argmax()) + 2  # +1 for 0-index, +1 for the header row
        raise BadRequest(f"{int(bad.sum())} row(s) have a non-numeric amount (first at CSV line {first}).")
    df["amount"] = amounts

    dates = clusters.parse_dates(df["date"])
    df["date"] = dates.dt.strftime("%Y-%m-%d").fillna(df["date"].fillna("").astype(str))
    return df.reset_index(drop=True), (None if truth is None else truth.reset_index(drop=True))


def _num(x, ndigits: int = 2):
    return None if x is None or pd.isna(x) else round(float(x), ndigits)


@app.post("/api/analyze")
async def analyze(
    file: UploadFile | None = File(None),
    use_sample: str = Form("false"),
    n_clusters: int = Form(0),  # 0 = pick automatically
    corrections: str = Form("[]"),
):
    content = await file.read() if file is not None else None
    try:
        df, truth = read_statement(content, use_sample.lower() == "true" or content is None)
        fixes = parse_corrections(corrections)
    except BadRequest as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    model = get_model(fixes)
    preds = categorizer.predict(model, df["description"])
    df["category"] = preds["category"].values
    df["confidence"] = preds["confidence"].values
    # The model learns from corrections, but a row the user set by hand should
    # never come back different, so pin exact matches.
    pinned = dict(fixes)
    df["corrected"] = df["description"].isin(pinned)
    if pinned:
        df.loc[df["corrected"], "category"] = df.loc[df["corrected"], "description"].map(pinned)
        df.loc[df["corrected"], "confidence"] = 1.0

    auto = n_clusters <= 0
    k = None if auto else max(2, min(int(n_clusters), 8))
    labels, _, silhouette = clusters.fit_clusters(df, n_clusters=k)
    df["cluster"] = labels
    summary = clusters.describe_clusters(df, labels)
    df["cluster_label"] = df["cluster"].map(dict(zip(summary["cluster"], summary["label"])))
    df["recurring"] = clusters.build_features(df)["is_recurring"].astype(bool)

    spend = df["amount"].abs()
    total = float(spend.sum())
    work = df.assign(_amt=spend)

    by_cat = (
        work.groupby("category")
        .agg(total=("_amt", "sum"), count=("_amt", "size"))
        .reset_index()
        .sort_values("total", ascending=False)
    )
    by_cat["share"] = by_cat["total"] / total if total else 0.0

    month = pd.to_datetime(work["date"], errors="coerce").dt.strftime("%Y-%m")
    monthly = (
        work.assign(_month=month)
        .dropna(subset=["_month"])
        .pivot_table(index="_month", columns="category", values="_amt", aggfunc="sum")
        .fillna(0.0)
    )
    monthly_rows = [
        {"month": m, "total": float(r.sum()), "by_category": {c: float(v) for c, v in r.items() if v}}
        for m, r in monthly.iterrows()
    ]

    recurring = clusters.recurring_payments(df)
    recurring_rows = [
        {
            "merchant": r.merchant,
            "category": r.category,
            "payments": int(r.payments),
            "typical_amount": _num(r.typical_amount),
            "cadence_days": _num(r.gap_days, 0),
            "monthly_equivalent": _num(r.typical_amount * 30 / max(r.gap_days, 1)),
            "last_date": r.last_date,
        }
        for r in recurring.itertuples()
    ]

    cluster_rows = summary.to_dict(orient="records")
    for row in cluster_rows:
        row["share"] = _num(row["total_spend"] / total if total else 0, 4)

    rows = work[
        ["date", "description", "amount", "_amt", "category", "confidence", "cluster_label", "recurring", "corrected"]
    ].rename(columns={"_amt": "abs_amount"})
    rows = rows.assign(low_confidence=rows["confidence"] < categorizer.LOW_CONFIDENCE)

    dated = pd.to_datetime(df["date"], errors="coerce").dropna()
    result = {
        "metrics": {
            "transactions": int(len(df)),
            "total_spend": total,
            "low_confidence": int(rows["low_confidence"].sum()),
            "recurring_monthly": float(sum(r["monthly_equivalent"] or 0 for r in recurring_rows)),
            "date_from": dated.min().strftime("%Y-%m-%d") if len(dated) else None,
            "date_to": dated.max().strftime("%Y-%m-%d") if len(dated) else None,
        },
        "categories": by_cat.to_dict(orient="records"),
        "monthly": monthly_rows,
        "recurring": recurring_rows,
        "clusters": {
            "silhouette": _num(silhouette, 3),
            "k": int(len(summary)),
            "auto": auto,
            "summary": cluster_rows,
        },
        "rows": rows.to_dict(orient="records"),
        "corrections_applied": len(fixes),
    }
    if truth is not None:
        result["evaluation"] = {"accuracy": float((df["category"] == truth).mean()), "rows": int(len(df))}
    return result
