"""Train the category classifier from a labeled CSV and save it to models/."""
import argparse

import pandas as pd

from src import categorizer


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data/seed_labeled.csv")
    ap.add_argument("--out", default=str(categorizer.MODEL_PATH))
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    missing = {"description", "category"} - set(df.columns)
    if missing:
        raise SystemExit(f"{args.data} is missing column(s): {', '.join(sorted(missing))}")

    pipe, report, cv = categorizer.train(df)
    print(report)
    print(f"5-fold CV accuracy: {cv:.3f}")
    print(f"saved -> {categorizer.save(pipe, __import__('pathlib').Path(args.out))}")


if __name__ == "__main__":
    main()
