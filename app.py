"""Streamlit UI: upload a statement, get categories and spend clusters."""
import altair as alt
import pandas as pd
import streamlit as st

from src import categorizer, clusters

REQUIRED = {"date", "description", "amount"}

st.set_page_config(page_title="Smart Expense Categorizer", layout="wide")
st.title("Smart Expense Categorizer + Spend Clusters")
st.caption("An ensemble text classifier labels each transaction; K-Means groups your spending behaviour.")


@st.cache_resource
def get_model():
    # Fitting takes well under a second, so train in memory at launch instead of
    # loading a saved artifact that can go stale when the model changes.
    return categorizer.fit(pd.read_csv("data/seed_labeled.csv"))


@st.cache_data
def read_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


with st.sidebar:
    st.header("Input")
    upload = st.file_uploader("Statement CSV", type="csv")
    auto_k = st.checkbox("Choose the number of clusters automatically", value=True)
    n_clusters = st.slider("Spend clusters", 2, 8, 4, disabled=auto_k)
    st.markdown("CSV needs columns: `date`, `description`, `amount`.")

if upload is None:
    st.info("Upload a statement CSV in the sidebar to get started.")
    st.stop()
df = read_csv(upload)

df.columns = [c.strip().lower() for c in df.columns]
missing = REQUIRED - set(df.columns)
if missing:
    st.error(f"Missing column(s): {', '.join(sorted(missing))}")
    st.stop()

model = get_model()
preds = categorizer.predict(model, df["description"])
df["category"] = preds["category"].values
df["confidence"] = preds["confidence"].values

labels, _, silhouette = clusters.fit_clusters(df, n_clusters=None if auto_k else n_clusters)
df["cluster"] = labels
summary = clusters.describe_clusters(df, labels)
cluster_names = dict(zip(summary["cluster"], summary["label"]))
df["cluster_label"] = df["cluster"].map(cluster_names)

spend = pd.to_numeric(df["amount"], errors="coerce").abs()
c1, c2, c3 = st.columns(3)
c1.metric("Transactions", len(df))
c2.metric("Total spend", f"{spend.sum():,.0f}")
c3.metric("Low-confidence rows", int((df["confidence"] < categorizer.LOW_CONFIDENCE).sum()))

tab_cat, tab_clust, tab_rows = st.tabs(["Categories", "Clusters", "Transactions"])

with tab_cat:
    by_cat = (
        df.assign(_amt=spend)
        .groupby("category", as_index=False)["_amt"]
        .sum()
        .rename(columns={"_amt": "total"})
        .sort_values("total", ascending=False)
    )
    st.altair_chart(
        alt.Chart(by_cat)
        .mark_bar()
        .encode(
            x=alt.X("total:Q", title="Total spend"),
            y=alt.Y("category:N", sort="-x", title=None),
            tooltip=["category", "total"],
        )
        .properties(height=260),
        width="stretch",
    )
    st.dataframe(by_cat, width="stretch", hide_index=True)

with tab_clust:
    if silhouette is not None:
        st.caption(f"Silhouette score: {silhouette:.3f} (higher means better separated clusters)")
    st.dataframe(summary, width="stretch", hide_index=True)
    st.altair_chart(
        alt.Chart(df.assign(_amt=spend))
        .mark_circle(size=70, opacity=0.6)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("_amt:Q", title="Amount", scale=alt.Scale(type="log")),
            color=alt.Color("cluster_label:N", title="Cluster"),
            tooltip=["date", "description", "_amt", "category", "cluster_label"],
        )
        .properties(height=340),
        width="stretch",
    )

with tab_rows:
    low_only = st.checkbox("Show only rows the model is unsure about")
    view = df[df["confidence"] < categorizer.LOW_CONFIDENCE] if low_only else df
    st.dataframe(
        view[["date", "description", "amount", "category", "confidence", "cluster_label"]],
        width="stretch",
        hide_index=True,
    )
    st.download_button(
        "Download categorized CSV",
        df.to_csv(index=False).encode(),
        "categorized_transactions.csv",
        "text/csv",
    )
