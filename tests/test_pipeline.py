import pandas as pd
import pytest

from src import categorizer, clusters


@pytest.fixture(scope="module")
def seed():
    return pd.read_csv("data/seed_labeled.csv")


def test_clean_description_strips_reference_numbers():
    assert categorizer.clean_description("UPI/SWIGGY/ORDER123456/YESB") == "upi swiggy order yesb"


def test_classifier_learns_the_obvious_merchants(seed):
    pipe, _, cv = categorizer.train(seed)
    assert cv > 0.8
    preds = categorizer.predict(pipe, pd.Series(["UPI/SWIGGY/ORDER99/YESB", "NEFT/LANDLORD RENT MAY/SBIN"]))
    assert list(preds["category"]) == ["food", "rent"]
    assert (preds["confidence"] > 0).all()


def test_features_flag_weekends_and_repeats():
    df = pd.DataFrame(
        {
            "date": ["2024-01-06", "2024-01-08", "2024-01-08"],
            "description": ["NETFLIX", "NETFLIX", "POS/CROMA"],
            "amount": [199, 199, 40000],
        }
    )
    feats = clusters.build_features(df)
    assert list(feats["is_weekend"]) == [1, 0, 0]
    assert list(feats["is_recurring"]) == [1, 1, 0]


def test_clustering_summarizes_every_cluster(seed):
    labels, _, score = clusters.fit_clusters(seed, n_clusters=4)
    summary = clusters.describe_clusters(seed, labels)
    assert len(summary) == len(set(labels))
    assert summary["transactions"].sum() == len(seed)
    assert score is None or -1 <= score <= 1


def test_clustering_handles_tiny_inputs():
    df = pd.DataFrame({"date": ["2024-01-01"], "description": ["X"], "amount": [10]})
    labels, model, score = clusters.fit_clusters(df)
    assert len(labels) == 1 and model is None and score is None
