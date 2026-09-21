"""K-Means over per-transaction spend behaviour features, plus recurring-payment detection."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .categorizer import clean_description

FEATURES = ["log_amount", "is_weekend", "day_sin", "day_cos", "hour_bucket", "is_recurring"]

# Tokens that describe *how* a payment was made, not *who* it went to. Dropped
# before comparing descriptions so "UPI/NETFLIX/..." and "POS NETFLIX MUMBAI"
# count as the same merchant.
_NOISE_TOKENS = frozenset(
    "upi pos neft imps ach nach ecs bbps billpay dr cr p2a pg debit in online internet d "
    "ybl paytm ibl oksbi axl okhdfcbank hdfc yesb icic sbin utib kkbk punb barb "
    "bengaluru mumbai delhi hyderabad chennai pune kolkata gurgaon noida ahmedabad".split()
)


def parse_dates(values) -> pd.Series:
    """Parse statement dates, preferring day-first when month-first can't read them all.

    Indian statements are usually DD/MM/YYYY. pandas guesses month-first from the
    first row, which silently swaps day and month on ambiguous dates; if that
    guess fails on any row (a day above 12), day-first is the right reading.
    """
    values = pd.Series(values)
    with warnings.catch_warnings():  # pandas warns about the very ambiguity we resolve here
        warnings.simplefilter("ignore", UserWarning)
        month_first = pd.to_datetime(values, errors="coerce")
        if month_first.notna().all():
            return month_first
        day_first = pd.to_datetime(values, errors="coerce", dayfirst=True)
    return day_first if day_first.notna().sum() > month_first.notna().sum() else month_first


def merchant_key(description: str) -> str:
    """Stable identity for a merchant: its first two distinctive words."""
    seen: list[str] = []
    for tok in clean_description(description).split():
        if len(tok) > 1 and tok not in _NOISE_TOKENS and tok not in seen:
            seen.append(tok)
    return " ".join(seen[:2]) or "unknown"


def _recurring_stats(df: pd.DataFrame) -> pd.DataFrame:
    """One row per merchant that pays like a subscription, EMI or rent.

    A merchant counts as recurring when it pays on a steady monthly rhythm (3+
    payments, gaps close to a month and not erratic, which catches variable
    bills like electricity) or repeats at a fixed amount at least ~3 weeks apart
    (which catches a 2-payment history). Merely appearing often isn't enough:
    restaurants and petrol pumps do, and they aren't commitments.
    """
    keys = df["description"].map(merchant_key)
    dates = parse_dates(df["date"])
    amounts = pd.to_numeric(df["amount"], errors="coerce").abs()
    rows = []
    for key, idx in keys.groupby(keys).groups.items():
        n = len(idx)
        if n < 2:
            continue
        amt = amounts.loc[idx].dropna()
        days = dates.loc[idx].dropna().sort_values()
        if amt.empty or len(days) < 2:
            continue
        mean = amt.mean()
        cv = amt.std(ddof=0) / mean if mean > 0 else 1.0
        gaps = days.diff().dt.days.dropna()
        gap = gaps.median()
        monthly = n >= 3 and 24 <= gap <= 38 and gaps.std(ddof=0) <= 7
        fixed = cv <= 0.05 and gap >= 20
        if monthly or fixed:
            category = None
            if "category" in df.columns:
                modes = df.loc[idx, "category"].mode()
                category = modes.iat[0] if len(modes) else None
            rows.append(
                {
                    "key": key,
                    "category": category,
                    "merchant": key.title(),
                    "payments": int(n),
                    "typical_amount": float(amt.median()),
                    "gap_days": float(gap),
                    "last_date": days.iloc[-1].strftime("%Y-%m-%d"),
                    "index": list(idx),
                }
            )
    return pd.DataFrame(
        rows, columns=["key", "merchant", "category", "payments", "typical_amount", "gap_days", "last_date", "index"]
    )


def recurring_payments(df: pd.DataFrame) -> pd.DataFrame:
    """Recurring merchants, largest first (merchant, category, payments, typical_amount, gap_days, last_date)."""
    stats = _recurring_stats(df)
    return (
        stats.drop(columns=["key", "index"])
        .sort_values("typical_amount", ascending=False)
        .reset_index(drop=True)
    )


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Turn raw transactions into the numeric behaviour features we cluster on."""
    dates = parse_dates(df["date"])
    amounts = pd.to_numeric(df["amount"], errors="coerce").abs().fillna(0.0)

    recurring = pd.Series(0, index=df.index)
    stats = _recurring_stats(df)
    for idx in stats["index"]:
        recurring.loc[idx] = 1

    day = dates.dt.day.fillna(15)
    feats = pd.DataFrame(index=df.index)
    feats["log_amount"] = np.log1p(amounts)
    feats["is_weekend"] = (dates.dt.dayofweek >= 5).fillna(False).astype(int)
    # Day of month is circular: the 31st is next to the 1st, not far from it.
    feats["day_sin"] = np.sin(2 * np.pi * day / 31)
    feats["day_cos"] = np.cos(2 * np.pi * day / 31)
    feats["hour_bucket"] = (dates.dt.hour.fillna(12) // 6).astype(int)
    feats["is_recurring"] = recurring.astype(int)
    return feats[FEATURES]


def fit_clusters(df: pd.DataFrame, n_clusters: int | None = 4, seed: int = 42, max_auto: int = 6):
    """Cluster transactions. Returns (labels, model, silhouette or None).

    Pass `n_clusters=None` to choose k in 3..`max_auto` by silhouette score. The
    floor is 3 because a two-way split ("bills" vs "everything else") is true
    but too coarse to be worth showing.
    """
    feats = build_features(df)
    if len(feats) < 3:
        return np.zeros(len(feats), dtype=int), None, None

    def fit_k(k: int):
        model = Pipeline(
            [
                ("scale", StandardScaler()),
                ("kmeans", KMeans(n_clusters=k, n_init=10, random_state=seed)),
            ]
        )
        labels = model.fit_predict(feats)
        score = silhouette_score(feats, labels) if len(set(labels)) > 1 else None
        return labels, model, score

    upper = len(feats) - 1
    if n_clusters is None:
        # Roughly 10+ transactions per pattern, so a short statement isn't sliced into groups of one or two.
        cap = min(max_auto, max(2, len(feats) // 10), upper)
        best = None
        for k in range(min(3, cap), cap + 1):
            cand = fit_k(k)
            if cand[2] is not None and (best is None or cand[2] > best[2]):
                best = cand
        return best if best is not None else fit_k(2)
    return fit_k(max(2, min(int(n_clusters), upper)))


def describe_clusters(df: pd.DataFrame, labels) -> pd.DataFrame:
    """Human-readable summary of each cluster, one row per cluster."""
    work = df.copy()
    work["cluster"] = labels
    work["_amount"] = pd.to_numeric(work["amount"], errors="coerce").abs()
    feats = build_features(df)
    work["_weekend"] = feats["is_weekend"].values
    work["_recurring"] = feats["is_recurring"].values
    overall_median = work["_amount"].median()

    rows = []
    for cid, grp in work.groupby("cluster"):
        top_cat = (
            grp["category"].mode().iat[0] if "category" in grp and not grp["category"].isna().all() else "-"
        )
        rows.append(
            {
                "cluster": cid,
                "label": _name_cluster(grp, overall_median),
                "transactions": len(grp),
                "total_spend": round(grp["_amount"].sum(), 2),
                "avg_amount": round(grp["_amount"].mean(), 2),
                "weekend_share": round(grp["_weekend"].mean(), 2),
                "recurring_share": round(grp["_recurring"].mean(), 2),
                "top_category": top_cat,
            }
        )
    out = pd.DataFrame(rows).sort_values("total_spend", ascending=False).reset_index(drop=True)

    # Two clusters can earn the same name (k is user-chosen); tell them apart by
    # what they mostly buy, and number any that still collide.
    dup = out["label"].duplicated(keep=False)
    out.loc[dup, "label"] = out.loc[dup, "label"] + " · " + out.loc[dup, "top_category"].astype(str)
    dup = out["label"].duplicated(keep=False)
    if dup.any():
        out.loc[dup, "label"] = out.loc[dup, "label"] + " #" + (out[dup].groupby("label").cumcount() + 1).astype(str)
    return out


def _name_cluster(grp: pd.DataFrame, overall_median: float) -> str:
    avg = grp["_amount"].mean()
    if grp["_recurring"].mean() > 0.6:
        return "Fixed monthly payments"
    if avg > 3 * overall_median or avg > 5000:
        return "Big-ticket spends"
    if grp["_weekend"].mean() > 0.5:
        return "Weekend splurges"
    if avg < 0.5 * overall_median:
        return "Small everyday spends"
    return "Routine weekday spends"
