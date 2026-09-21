"""TF-IDF + Multinomial Naive Bayes classifier for transaction descriptions."""
from __future__ import annotations

import re
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

MODEL_PATH = Path("models/categorizer.joblib")

# Bank statements are full of reference numbers; they carry no signal and just
# blow up the vocabulary, so strip long digit runs before vectorizing.
_DIGITS = re.compile(r"\d{3,}")
_NOISE = re.compile(r"[^a-z\s]+")


def clean_description(text: str) -> str:
    text = str(text).lower()
    text = _DIGITS.sub(" ", text)
    text = _NOISE.sub(" ", text)
    return " ".join(text.split())


def build_pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    preprocessor=clean_description,
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    min_df=1,
                ),
            ),
            ("nb", MultinomialNB(alpha=0.2)),
        ]
    )


def train(df: pd.DataFrame, test_size: float = 0.25, seed: int = 42):
    """Fit on a labeled frame with `description` and `category` columns.

    Returns (pipeline, report_text, cv_mean_accuracy).
    """
    X, y = df["description"], df["category"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )
    pipe = build_pipeline()
    pipe.fit(X_train, y_train)
    report = classification_report(y_test, pipe.predict(X_test), zero_division=0)
    cv = cross_val_score(build_pipeline(), X, y, cv=5).mean()

    # Refit on everything so the shipped model uses all the labels we have.
    final = build_pipeline().fit(X, y)
    return final, report, cv


def predict(pipe: Pipeline, descriptions) -> pd.DataFrame:
    """Predict categories plus the model's confidence in each one."""
    probs = pipe.predict_proba(descriptions)
    classes = pipe.classes_
    return pd.DataFrame(
        {
            "category": classes[probs.argmax(axis=1)],
            "confidence": probs.max(axis=1),
        },
        index=getattr(descriptions, "index", None),
    )


def save(pipe: Pipeline, path: Path = MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, path)
    return path


def load(path: Path = MODEL_PATH) -> Pipeline:
    return joblib.load(path)
