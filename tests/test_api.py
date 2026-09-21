import json

import pandas as pd
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from api.index import app  # noqa: E402

client = TestClient(app)

# A realistic six-month statement, uploaded the way a user would (no answer key).
STATEMENT = pd.read_csv("data/holdout_statement.csv").drop(columns=["category"]).to_csv(index=False)


def post_csv(text: str, **data):
    return client.post("/api/analyze", files={"file": ("s.csv", text.encode(), "text/csv")}, data=data)


def test_uploaded_statement_is_analyzed_end_to_end():
    r = post_csv(STATEMENT)
    assert r.status_code == 200
    j = r.json()
    assert j["metrics"]["transactions"] == 204
    assert j["clusters"]["auto"] and 3 <= j["clusters"]["k"] <= 6
    assert len(j["recurring"]) >= 8
    assert len(j["monthly"]) == 6
    assert abs(sum(c["share"] for c in j["categories"]) - 1) < 1e-6
    assert {"low_confidence", "recurring", "cluster_label"} <= set(j["rows"][0])
    assert "evaluation" not in j  # there is no answer key for an upload


def test_the_analyzer_has_no_built_in_sample():
    # No file means nothing to analyze; the old `use_sample` switch is gone.
    for data in ({}, {"use_sample": "true"}):
        r = client.post("/api/analyze", data=data)
        assert r.status_code == 400
        assert "Upload a statement CSV" in r.json()["error"]


def test_manual_cluster_count_is_respected_and_clamped():
    assert post_csv(STATEMENT, n_clusters="5").json()["clusters"]["k"] == 5
    assert post_csv(STATEMENT, n_clusters="99").json()["clusters"]["k"] == 8


def test_corrections_teach_the_model_a_brand_it_misread():
    stmt = "date,description,amount\n" + "\n".join(f"2025-0{m}-1{m},UPI/RAPIDO/{m}12345,{90 + m}" for m in range(1, 6))
    before = post_csv(stmt).json()
    fix = [{"description": "UPI/RAPIDO/112345", "category": "travel"}]
    after = post_csv(stmt, corrections=json.dumps(fix)).json()
    assert before["corrections_applied"] == 0
    assert after["corrections_applied"] == 1
    assert {r["category"] for r in after["rows"]} == {"travel"}
    assert next(r for r in after["rows"] if r["description"] == "UPI/RAPIDO/112345")["corrected"]


@pytest.mark.parametrize(
    "csv,fragment",
    [
        ("date,description,amount\n2024-03-14,X,abc\n", "non-numeric amount (first at CSV line 2)"),
        ("a,b\n1,2\n", "Missing column"),
        ("date,description,amount\n", "no rows"),
        ("", "Could not read CSV"),
    ],
)
def test_bad_statements_get_a_readable_400(csv, fragment):
    r = post_csv(csv)
    assert r.status_code == 400 and fragment in r.json()["error"]


def test_bad_corrections_are_rejected():
    for raw in ('[{"description":"x","category":"nope"}]', "oops"):
        assert post_csv(STATEMENT, corrections=raw).status_code == 400


def test_day_first_dates_and_blank_cells_do_not_crash():
    r = post_csv("Date,Description,Amount\n14/03/2024,UPI/SWIGGY/1,300\n03/04/2024,,649\n25/12/2024,IRCTC,900\n")
    assert r.status_code == 200
    assert [x["date"] for x in r.json()["rows"]] == ["2024-03-14", "2024-04-03", "2024-12-25"]
