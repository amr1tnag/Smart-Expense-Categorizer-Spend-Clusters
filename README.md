# Smart Expense Categorizer + Spend Clusters

Drop in a bank or UPI statement CSV. A text model labels every transaction
(food, travel, shopping, entertainment, health, bills, rent, other), finds the
payments that repeat on a schedule, and groups the rest into spending patterns:
weekend splurges, routine weekday spends, big-ticket buys. When it is unsure it
says so, and it learns from the labels you fix.

There are two front ends over the same model code in `src/`:

- **Web app** (Next.js + a FastAPI function), deployed on Vercel.
- **Streamlit app**, for running everything locally in Python.

## Web app (Next.js + FastAPI)

You start with an empty page and upload your own statement CSV; nothing is
pre-loaded, and the file is analyzed in memory and not saved. Then the page
shows, top to bottom: a sentence-led summary with the whole statement as
one strip (click a category to filter), month-by-month spend, fixed monthly
commitments, spending patterns, and a transactions table. Rows the model is
unsure about are marked **Check** and collected under "Needs a look". Change a
category and the page re-runs the model with your correction added, so similar
merchants update too. Figures use Indian digit grouping (₹4,86,961), and there is
a light and a dark theme.

The page posts the CSV to `POST /api/analyze`, served by the FastAPI app in
`api/index.py`. That function fits the classifier from `data/seed_labeled.csv`
(about half a second), caches it in memory for warm instances, and returns
category totals, monthly totals, recurring payments, pattern summaries and every
categorized row as JSON.

| form field | meaning |
| --- | --- |
| `file` | the statement CSV (required: there is no built-in sample) |
| `n_clusters` | `0` (default) picks 3 to 6 patterns automatically, or 2 to 8 to choose |
| `corrections` | JSON list of `{description, category}`; the model is refit with them |

Bad input comes back as a 400 with a readable `error` (missing columns, an empty
file, a non-numeric amount with its CSV line number, an unknown category).

`vercel.json` rewrites `/api/*` to the function and bundles `src/` and the
training data (`data/seed_labeled.csv`) with it. Deploying is a normal Vercel git import: it detects Next.js and the
Python function on its own.

### Running it locally

`next dev` doesn't run the Python function, so run the API yourself and point the
frontend at it:

```bash
pip install -r api/requirements.txt uvicorn
uvicorn api.index:app --port 8000

npm install
API_ORIGIN=http://127.0.0.1:8000 npm run dev      # PowerShell: $env:API_ORIGIN="http://127.0.0.1:8000"; npm run dev
```

`API_ORIGIN` only adds a local `/api/*` rewrite; on Vercel it is unset. On Windows
the default Turbopack build can fail with a PostCSS worker error (`0xc0000142`);
use `npx next build --webpack`. Vercel's Linux builds are unaffected.

## Streamlit app

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app fits the model in memory at launch, so there is no saved model to go
stale. `python train.py` is still there when you want the numbers:

```bash
python train.py     # merchant-grouped CV + score on data/holdout_statement.csv; saves models/categorizer.joblib
```

## Input format

A CSV with these columns (extra columns are ignored, header case doesn't matter):

| column | example |
| --- | --- |
| `date` | `2024-03-14` or `14/03/2024` |
| `description` | `UPI/SWIGGY/ORDER482913/YESB` |
| `amount` | `412.50` |

Amounts are treated as absolute values, so a debit column of either sign works.
`DD/MM/YYYY` dates are read day-first whenever month-first can't parse them all.

## How accurate is it?

The training data is **synthetic**: real brand names with random amounts, dates
and reference numbers, in several statement formats (`data/generate.py`). So the
numbers below say how well the model handles brands and formats it has not seen,
not how it will do on your bank's exact export.

| measure | before | now |
| --- | --- | --- |
| Accuracy on a 204-row held-out statement with brands the model never saw | 0.544 | **0.877** (macro-F1 0.904) |
| Merchant-grouped cross-validation (whole merchants held out per fold) | not measured | 0.662 |
| Share of mistakes that carry a low-confidence flag | n/a (no rows were ever flagged) | 64%, flagging only 5% of correct rows |
| Cluster separation (silhouette) on the held-out statement | about 0.07 | 0.18 |
| Accuracy after fixing one row per misread brand (6 fixes) | n/a | 1.000 |

"Before" is the old TF-IDF + Naive Bayes model trained on the old 252-row seed
set, which had no `other` class. Two caveats: the held-out statement was used to
choose among the top few ensemble variants, so 0.877 is slightly optimistic, and
the remaining mistakes are all wholly unfamiliar brand names with no descriptor
word (Rapido, Dunzo, Cleartrip). Nothing in the text can fix those; the low
confidence flag and your corrections do.

Random train/test splits flatter a text classifier because the same merchant
lands on both sides. The old README's 0.94 and 0.988 were of that kind.

### Training on your own transactions

Your own statement beats the synthetic set: merchant strings differ per bank.

1. Export your statement and keep the `date`, `description`, `amount` columns.
2. Add a `category` column with one of the eight categories and label ~200 rows.
3. Optionally add a `merchant` column so cross-validation can hold merchants out
   (without it, identical descriptions are grouped instead).
4. `python train.py --data data/my_labeled.csv`

Regenerate the synthetic files with `python data/generate.py`.

## How it works

**Categorizer** (`src/categorizer.py`). Descriptions are lowercased and stripped
of reference numbers (`UPI/SWIGGY/ORDER482913` becomes `upi swiggy order`). Word
1-2 grams carry the merchant, and character 2-5 grams catch spelling drift
(`NETFLIX COM`, `PG*ZOMATO*`). Logistic regression, ComplementNB and a calibrated
linear SVM vote, and the averaged probability is the confidence. Training also
pairs made-up brand names with generic descriptors (`... PHARMACY`, `... PETROL
PUMP`) so an unknown brand with a telling word still lands in the right category.

**Recurring payments** (`src/clusters.py`). A merchant counts as recurring when it
is paid on a steady monthly rhythm (3+ payments, gaps near a month and not
erratic, which catches variable bills like electricity) or repeats at a fixed
amount at least three weeks apart. Appearing often is not enough: restaurants and
petrol pumps do, and they are not commitments.

**Patterns** (`src/clusters.py`). Each transaction becomes six features:
`log_amount`, `is_weekend`, a circular day of month (`day_sin`, `day_cos`),
`hour_bucket`, and `is_recurring`. Standard-scaled, then K-Means, with k chosen
by silhouette score from 3 to 6 unless you choose it. Each cluster is named from
its own statistics, and duplicate names are told apart by top category.

## Layout

```
app/                    Next.js page, layout and styles (App Router)
components/             spend strip, month chart, commitments, patterns, table
lib/                    shared TS types, category colors, Indian-format helpers
api/index.py            FastAPI function behind /api/analyze
api/requirements.txt    Python deps for the API
vercel.json             /api/* rewrite + files bundled with the function
app.py                  Streamlit UI
train.py                CLI trainer and scorer
src/categorizer.py      TF-IDF + voting ensemble, grouped CV, scoring
src/clusters.py         recurring detection, features, K-Means, cluster naming
data/generate.py        deterministic generator for the synthetic data
data/seed_labeled.csv   training set: about 1,400 rows, 8 categories, merchant column
data/holdout_statement.csv  6-month statement with answer key, for measuring accuracy only
tests/                  pytest suite for the model, clustering and API
```

Run the tests with `python -m pytest tests -q` (the API tests need `fastapi` and
`httpx` and are skipped without them).
