from datetime import date

import pandas as pd
import pytest

from commercelens.analytics import (
    category_performance, filter_orders, load_data, metrics, previous_window,
)


@pytest.fixture
def orders():
    return pd.DataFrame({
        "order_id": ["a", "b", "c", "d"],
        "customer_key": ["u1", "u1", "u2", "u3"],
        "purchase_date": pd.to_datetime(["2018-01-01", "2018-01-31", "2018-02-01", "2018-01-15"]),
        "state": ["SP", "SP", "RJ", "SP"],
        "status": ["delivered", "delivered", "delivered", "canceled"],
        "sales_cents": [10000, 20000, 5000, 99999],
        "freight_cents": [1000, 1500, 1000, 0],
        "is_late": pd.array([0, None, 1, None], dtype="Int64"),
        "review_score": pd.array([5, None, 1, 1], dtype="Int64"),
        "delivery_days": pd.array([2, None, 12, None], dtype="Int64"),
    })


def test_date_boundaries_state_scope_and_cancelled_sales(orders):
    filtered = filter_orders(orders, date(2018, 1, 1), date(2018, 1, 31), ["SP"])
    assert set(filtered.order_id) == {"a", "b", "d"}
    result = metrics(filtered)
    assert result["sales_cents"] == 30000
    assert result["aov_cents"] == 15000
    assert result["all_orders"] == 3
    assert result["delivered_orders"] == 2
    assert result["customers"] == 1
    assert result["repeat_customers"] == 1
    assert result["repeat_pct"] == 100


def test_missing_dates_are_not_counted_as_on_time(orders):
    result = metrics(orders)
    assert result["delivery_eligible"] == 2
    assert result["late_pct"] == 50
    assert result["reviewed_orders"] == 2
    assert result["review_mean"] == 3


def test_empty_and_no_review_selections_are_explicit(orders):
    empty = metrics(orders.iloc[:0])
    assert empty["sales_cents"] == 0
    assert empty["late_pct"] is None
    assert empty["aov_cents"] is None
    assert empty["repeat_pct"] is None
    missing = metrics(orders.loc[orders.order_id.eq("b")])
    assert missing["late_pct"] is None
    assert missing["review_mean"] is None


def test_category_uses_item_sales_not_repeated_order_total(orders):
    categories = pd.DataFrame({"order_id": ["a", "a", "b", "d"],
        "category": ["books", "gifts", "books", "gifts"],
        "sales_cents": [4000, 6000, 20000, 99999], "item_count": [1, 1, 2, 1]})
    scoped = orders.loc[orders.purchase_date.dt.month.eq(1)]
    result = category_performance(scoped, categories)
    assert result.sales_cents.sum() == 30000
    assert result.set_index("category").loc["books", "orders"] == 2


def test_equal_length_prior_window_and_invalid_dates(orders):
    start, end = previous_window(date(2018, 3, 1), date(2018, 3, 31))
    assert (end-start).days + 1 == 31
    assert end == date(2018, 2, 28)
    with pytest.raises(ValueError, match="Start date"):
        filter_orders(orders, date(2018, 3, 1), date(2018, 1, 1))


def test_shipped_real_snapshots_reconcile():
    orders, categories, manifest = load_data()
    assert len(orders) == 99441
    assert all(manifest["quality"]["checks"].values())
    assert orders.sales_cents.sum() == categories.sales_cents.sum()
    assert category_performance(orders, categories).sales_cents.sum() == metrics(orders)["sales_cents"]


def test_edited_snapshot_is_rejected(tmp_path):
    import json
    (tmp_path/"manifest.json").write_text(json.dumps({"exports": {"orders.csv.gz": "wrong"}}))
    (tmp_path/"orders.csv.gz").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_data(tmp_path)
