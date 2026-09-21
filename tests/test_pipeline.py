import pandas as pd
import pytest

from src import categorizer, clusters


@pytest.fixture(scope="module")
def seed():
    return pd.read_csv("data/seed_labeled.csv")


@pytest.fixture(scope="module")
def holdout():
    return pd.read_csv("data/holdout_statement.csv")


@pytest.fixture(scope="module")
def model(seed):
    return categorizer.fit(seed)


def test_clean_description_strips_reference_numbers():
    assert categorizer.clean_description("UPI/SWIGGY/ORDER123456/YESB") == "upi swiggy order yesb"


def test_classifier_learns_the_obvious_merchants(model):
    preds = categorizer.predict(model, pd.Series(["UPI/SWIGGY/ORDER99/YESB", "NEFT/LANDLORD RENT MAY/SBIN"]))
    assert list(preds["category"]) == ["food", "rent"]
    assert (preds["confidence"] > 0).all()


def test_grouped_cv_holds_out_whole_merchants(seed):
    # Merchant-grouped CV is the honest number; a random split scores far higher
    # because the same merchant lands in both train and test.
    _, report, cv = categorizer.train(seed)
    assert cv > 0.55
    assert "accuracy" in report


def test_generalises_to_a_statement_with_unseen_merchants(model, holdout):
    s = categorizer.score(model, holdout)
    assert s["accuracy"] > 0.8
    assert s["macro_f1"] > 0.8
    # Low confidence should catch most mistakes while rarely flagging correct rows.
    assert s["errors_flagged"] > 0.5
    assert s["correct_flagged"] < 0.2


def test_descriptors_generalise_to_brands_it_has_never_seen(model):
    # None of these brand names appear in training; only the descriptor word does.
    preds = categorizer.predict(
        model,
        pd.Series(["UPI/ZANTRIX PHARMACY/123456", "POS QUORVA PETROL PUMP PUNE", "UPI/KELVIRO CINEMAS/7788"]),
    )
    assert list(preds["category"]) == ["health", "travel", "entertainment"]


def test_fit_survives_tiny_training_sets():
    tiny = pd.DataFrame({"description": ["swiggy", "zomato", "uber", "ola"], "category": ["food", "food", "travel", "travel"]})
    pipe = categorizer.fit(tiny)
    assert set(categorizer.predict(pipe, pd.Series(["swiggy"]))["category"]) <= {"food", "travel"}


def test_features_flag_weekends():
    df = pd.DataFrame(
        {
            "date": ["2024-01-06", "2024-01-08", "2024-01-09"],
            "description": ["A", "B", "C"],
            "amount": [199, 199, 40000],
        }
    )
    assert list(clusters.build_features(df)["is_weekend"]) == [1, 0, 0]


def test_recurring_needs_a_steady_rhythm_not_just_repeats():
    rows = []
    for m, day in enumerate([2, 3, 2, 3, 2], start=1):  # rent: same amount, monthly
        rows.append((f"2024-{m:02d}-{day:02d}", "NEFT/LANDLORD RENT/SBIN", 20000))
    for m, amt in enumerate([310, 780, 145, 990, 420], start=1):  # takeaway: varying amounts, erratic dates
        rows.append((f"2024-{m:02d}-{(m * 7) % 27 + 1:02d}", "UPI/SWIGGY/12345", amt))
        rows.append((f"2024-{m:02d}-{(m * 11) % 27 + 1:02d}", "UPI/SWIGGY/67890", amt + 5))
    df = pd.DataFrame(rows, columns=["date", "description", "amount"])
    rec = clusters.recurring_payments(df)
    assert list(rec["merchant"]) == ["Landlord Rent"]
    flags = clusters.build_features(df)["is_recurring"]
    assert flags[df["description"].str.contains("LANDLORD")].all()
    assert not flags[df["description"].str.contains("SWIGGY")].any()


def test_merchant_key_ignores_channel_and_city():
    assert clusters.merchant_key("UPI/NETFLIX/123456/HDFC") == clusters.merchant_key("POS 1234 NETFLIX MUMBAI")


def test_dates_prefer_day_first_when_month_first_fails():
    parsed = clusters.parse_dates(pd.Series(["14/03/2024", "03/04/2024"]))
    assert parsed.dt.strftime("%Y-%m-%d").tolist() == ["2024-03-14", "2024-04-03"]


def test_clustering_summarizes_every_cluster_with_unique_labels(holdout):
    for k in (3, 6, 8):
        labels, _, score = clusters.fit_clusters(holdout, n_clusters=k)
        summary = clusters.describe_clusters(holdout, labels)
        assert len(summary) == len(set(labels))
        assert summary["label"].is_unique
        assert summary["transactions"].sum() == len(holdout)
        assert score is None or -1 <= score <= 1


def test_auto_k_picks_a_reasonable_number_of_clusters(holdout):
    labels, _, score = clusters.fit_clusters(holdout, n_clusters=None)
    assert 3 <= len(set(labels)) <= 6
    assert score > 0.1


def test_clustering_handles_tiny_inputs():
    df = pd.DataFrame({"date": ["2024-01-01"], "description": ["X"], "amount": [10]})
    labels, model, score = clusters.fit_clusters(df)
    assert len(labels) == 1 and model is None and score is None
