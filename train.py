"""Train the category classifier from a labeled CSV and save it to models/.

Reports merchant-grouped cross-validation (whole merchants held out per fold, so
the score reflects brands the model has never seen) and, when a labeled
statement is supplied, accuracy on that separate held-out set.
"""
import argparse
from pathlib import Path

import pandas as pd

from src import categorizer


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data/seed_labeled.csv")
    ap.add_argument("--holdout", default="data/sample_statement.csv", help="labeled statement to score (skipped if missing)")
    ap.add_argument("--out", default=str(categorizer.MODEL_PATH))
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    missing = {"description", "category"} - set(df.columns)
    if missing:
        raise SystemExit(f"{args.data} is missing column(s): {', '.join(sorted(missing))}")

    pipe, report, cv = categorizer.train(df)
    print(report)
    print(f"Merchant-grouped CV accuracy: {cv:.3f}")

    holdout = Path(args.holdout)
    if holdout.exists():
        test = pd.read_csv(holdout)
        if {"description", "category"} <= set(test.columns):
            s = categorizer.score(pipe, test)
            print(
                f"Held-out statement ({len(test)} rows): accuracy {s['accuracy']:.3f}, macro-F1 {s['macro_f1']:.3f}; "
                f"low confidence (<{categorizer.LOW_CONFIDENCE}) flags {s['errors_flagged']:.0%} of mistakes "
                f"and {s['correct_flagged']:.0%} of correct rows"
            )

    print(f"saved -> {categorizer.save(pipe, Path(args.out))}")


if __name__ == "__main__":
    main()
