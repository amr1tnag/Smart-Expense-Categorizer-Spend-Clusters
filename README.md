# Smart Expense Categorizer + Spend Clusters

Upload a bank/UPI statement CSV. A TF-IDF + Multinomial Naive Bayes model labels
every transaction (food, travel, rent, shopping, bills, entertainment, health),
then K-Means groups the transactions into spending patterns — weekend splurges,
recurring bills, big-ticket buys — and a Streamlit UI shows the result.

## Quick start

```bash
pip install -r requirements.txt
python train.py          # trains from data/seed_labeled.csv -> models/categorizer.joblib
streamlit run app.py
```

The app trains the model on first launch if `models/` is empty, so you can skip
`train.py` if you just want to look around.

## Input format

A CSV with these columns (extra columns are ignored, header case doesn't matter):

| column | example |
| --- | --- |
| `date` | `2024-03-14` |
| `description` | `UPI/SWIGGY/ORDER482913/YESB` |
| `amount` | `412.50` |

Amounts are treated as absolute values, so a debit column of either sign works.

## Training on your own transactions

The shipped `data/seed_labeled.csv` is 252 synthetic Indian UPI/card rows. It
works, but your own statement is better — merchant strings differ per bank.

1. Export your statement and keep the `date`, `description`, `amount` columns.
2. Add a `category` column and hand-label ~200 rows (30 minutes, and you only
   do it once).
3. `python train.py --data data/my_labeled.csv`

Sort by description before labeling — identical merchants cluster together and
you can fill a whole block at a time.

## How it works

**Categorizer** (`src/categorizer.py`). Descriptions are lowercased and stripped
of reference numbers (`UPI/SWIGGY/ORDER482913` → `upi swiggy order`), which
keeps the vocabulary to real merchant tokens. TF-IDF over word 1–2 grams feeds a
`MultinomialNB(alpha=0.2)`. `predict()` returns the label plus the model's
confidence, and the UI can filter to low-confidence rows — those are the ones
worth hand-checking and adding to your training set.

**Clusters** (`src/clusters.py`). Each transaction becomes five features:
`log_amount`, `is_weekend`, `day_of_month`, `hour_bucket`, and `is_recurring`
(a description that appears more than once in the statement — subscriptions,
EMIs, rent). Standard-scaled, then K-Means. `describe_clusters()` names each
cluster from its own statistics rather than a fixed cluster id, so the labels
stay meaningful when you change `k`.

Current seed-data scores: 0.94 accuracy on a held-out 25%, 0.988 5-fold CV.

## Layout

```
app.py                  Streamlit UI
train.py                CLI trainer
src/categorizer.py      TF-IDF + MultinomialNB
src/clusters.py         feature engineering + K-Means
data/seed_labeled.csv   252 labeled sample transactions
tests/test_pipeline.py  pytest suite
```

Run the tests with `python -m pytest tests -q`.
