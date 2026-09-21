"""Transaction classifier: TF-IDF (words + characters) -> soft-voting ensemble.

Words carry the merchant ("swiggy", "pharmacy"); character n-grams catch the
spelling drift statements are full of ("NETFLIX COM", "PG*ZOMATO*"). Logistic
regression, ComplementNB and a calibrated linear SVM vote on the label, and the
averaged probability is the confidence shown in the UI.
"""
from __future__ import annotations

import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import VotingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GroupKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

MODEL_PATH = Path("models/categorizer.joblib")

# Predictions below this confidence are surfaced for a human check.
LOW_CONFIDENCE = 0.5

# Bank statements are full of reference numbers; they carry no signal and just
# blow up the vocabulary, so strip long digit runs before vectorizing.
_DIGITS = re.compile(r"\d{3,}")
_NOISE = re.compile(r"[^a-z\s]+")


def clean_description(text: str) -> str:
    text = str(text).lower()
    text = _DIGITS.sub(" ", text)
    text = _NOISE.sub(" ", text)
    return " ".join(text.split())


def build_pipeline(min_class_count: int = 3) -> Pipeline:
    """Build the (unfitted) pipeline.

    `min_class_count` is the size of the rarest class; the calibrated SVM needs
    at least 2 rows per class, so it drops out of the vote on tiny datasets.
    """
    voters = [
        ("lr", LogisticRegression(C=30, max_iter=2000)),
        ("cnb", ComplementNB(alpha=0.3)),
    ]
    if min_class_count >= 2:
        voters.append(("svc", CalibratedClassifierCV(LinearSVC(C=1), cv=min(3, min_class_count))))
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(preprocessor=clean_description, ngram_range=(1, 2), sublinear_tf=True),
            ),
            (
                "char",
                TfidfVectorizer(
                    preprocessor=clean_description, analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True
                ),
            ),
        ]
    )
    return Pipeline([("tfidf", features), ("clf", VotingClassifier(voters, voting="soft"))])


def fit(df: pd.DataFrame) -> Pipeline:
    """Fit on a labeled frame with `description` and `category` columns."""
    y = df["category"]
    return build_pipeline(int(y.value_counts().min())).fit(df["description"], y)


def _groups(df: pd.DataFrame) -> pd.Series:
    """Fold groups: the `merchant` column if present, else the cleaned description.

    Keeping a merchant's rows together in one fold is what makes the CV score
    honest: a random split lets the model see the same merchant in train and
    test, which flatters a text classifier a lot.
    """
    if "merchant" in df.columns:
        return df["merchant"].astype(str)
    return df["description"].map(clean_description)


def cross_validate(df: pd.DataFrame, n_splits: int = 5) -> pd.DataFrame:
    """Out-of-fold predictions with whole merchants held out per fold."""
    groups = _groups(df)
    n_splits = max(2, min(n_splits, groups.nunique()))
    out = pd.DataFrame(index=df.index, columns=["category", "confidence"], dtype=object)
    for tr, te in GroupKFold(n_splits).split(df, groups=groups):
        pipe = fit(df.iloc[tr])
        out.iloc[te] = predict(pipe, df["description"].iloc[te]).values
    out["confidence"] = out["confidence"].astype(float)
    return out


def score(pipe: Pipeline, df: pd.DataFrame) -> dict:
    """Accuracy/F1 on a labeled frame, plus how well low confidence flags mistakes."""
    preds = predict(pipe, df["description"])
    return _score(df["category"].values, preds["category"].values, preds["confidence"].values)


def _score(y, pred, conf) -> dict:
    wrong = pred != y
    low = conf < LOW_CONFIDENCE
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro", zero_division=0)),
        "errors_flagged": float(low[wrong].mean()) if wrong.any() else float("nan"),
        "correct_flagged": float(low[~wrong].mean()) if (~wrong).any() else float("nan"),
    }


def train(df: pd.DataFrame):
    """Fit on all rows and report honest, merchant-grouped cross-validation.

    Returns (pipeline, report_text, cv_accuracy). The report and score come from
    out-of-fold predictions on merchants the fold's model never saw.
    """
    oof = cross_validate(df)
    y = df["category"].values
    report = classification_report(y, oof["category"].values, zero_division=0)
    cv = float(accuracy_score(y, oof["category"].values))
    return fit(df), report, cv


def predict(pipe: Pipeline, descriptions) -> pd.DataFrame:
    """Predict categories plus the model's confidence in each one."""
    probs = pipe.predict_proba(descriptions)
    classes = np.asarray(pipe.classes_)
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
