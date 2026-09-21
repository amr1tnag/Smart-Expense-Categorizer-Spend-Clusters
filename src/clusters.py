"""K-Means over per-transaction spend behaviour features."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["log_amount", "is_weekend", "day_of_month", "hour_bucket", "is_recurring"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Turn raw transactions into the numeric behaviour features we cluster on."""
    dates = pd.to_datetime(df["date"], errors="coerce")
    amounts = pd.to_numeric(df["amount"], errors="coerce").abs().fillna(0.0)

    # A description seen more than once across the statement is very likely a
    # subscription, EMI or rent - the thing people actually want surfaced.
    from .categorizer import clean_description

    keys = df["description"].map(clean_description)
    repeats = keys.map(keys.value_counts())

    feats = pd.DataFrame(index=df.index)
    feats["log_amount"] = np.log1p(amounts)
    feats["is_weekend"] = (dates.dt.dayofweek >= 5).fillna(False).astype(int)
    feats["day_of_month"] = dates.dt.day.fillna(15).astype(int)
    feats["hour_bucket"] = (dates.dt.hour.fillna(12) // 6).astype(int)
    feats["is_recurring"] = (repeats > 1).astype(int)
    return feats[FEATURES]


def fit_clusters(df: pd.DataFrame, n_clusters: int = 4, seed: int = 42):
    """Cluster transactions. Returns (labels, model, silhouette or None)."""
    feats = build_features(df)
    n_clusters = max(2, min(n_clusters, len(feats) - 1)) if len(feats) > 2 else 1
    if len(feats) < 3:
        return np.zeros(len(feats), dtype=int), None, None

    model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("kmeans", KMeans(n_clusters=n_clusters, n_init=10, random_state=seed)),
        ]
    )
    labels = model.fit_predict(feats)
    score = silhouette_score(feats, labels) if len(set(labels)) > 1 else None
    return labels, model, score


def describe_clusters(df: pd.DataFrame, labels) -> pd.DataFrame:
    """Human-readable summary of each cluster, one row per cluster."""
    work = df.copy()
    work["cluster"] = labels
    work["_amount"] = pd.to_numeric(work["amount"], errors="coerce").abs()
    feats = build_features(df)
    work["_weekend"] = feats["is_weekend"].values
    work["_recurring"] = feats["is_recurring"].values

    rows = []
    for cid, grp in work.groupby("cluster"):
        top_cat = (
            grp["category"].mode().iat[0] if "category" in grp and not grp["category"].isna().all() else "-"
        )
        rows.append(
            {
                "cluster": cid,
                "label": _name_cluster(grp),
                "transactions": len(grp),
                "total_spend": round(grp["_amount"].sum(), 2),
                "avg_amount": round(grp["_amount"].mean(), 2),
                "weekend_share": round(grp["_weekend"].mean(), 2),
                "recurring_share": round(grp["_recurring"].mean(), 2),
                "top_category": top_cat,
            }
        )
    return pd.DataFrame(rows).sort_values("total_spend", ascending=False)


def _name_cluster(grp: pd.DataFrame) -> str:
    avg = grp["_amount"].mean()
    overall_weekend = grp["_weekend"].mean()
    recurring = grp["_recurring"].mean()
    if recurring > 0.6:
        return "Recurring bills & subscriptions"
    if avg > grp["_amount"].quantile(0.75) * 1.5 or avg > 5000:
        return "Big-ticket spends"
    if overall_weekend > 0.5:
        return "Weekend splurges"
    if avg < 300:
        return "Small everyday spends"
    return "Routine weekday spends"
