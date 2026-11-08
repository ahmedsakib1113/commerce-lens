"""Shared calculations. Every dashboard page uses the same filtered order grain."""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def load_data(directory: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    directory = directory or ROOT / "data/processed"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["exports"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Snapshot checksum mismatch: {name}. Rebuild the data.")
    orders = pd.read_csv(directory / "orders.csv.gz", dtype={"order_id": str, "customer_key": str})
    categories = pd.read_csv(directory / "categories.csv.gz", dtype={"order_id": str})
    orders["purchase_date"] = pd.to_datetime(orders["purchase_date"])
    for column in ["delivered_date", "estimated_date"]:
        orders[column] = pd.to_datetime(orders[column], errors="coerce")
    for column in ["is_late", "delivery_days", "review_score"]:
        orders[column] = orders[column].astype("Int64")
    if not orders["order_id"].is_unique:
        raise ValueError("Order snapshot must have exactly one row per order.")
    if len(orders) != manifest["quality"]["rows"]["order_facts"]:
        raise ValueError("Snapshot row count does not match the source manifest.")
    if categories.duplicated(["order_id", "category"]).any():
        raise ValueError("Category snapshot must have one row per order-category pair.")
    if not categories["order_id"].isin(orders["order_id"]).all():
        raise ValueError("Category snapshot contains unknown orders.")
    return orders, categories, manifest


def filter_orders(orders: pd.DataFrame, start: date, end: date,
                  states: list[str] | None = None) -> pd.DataFrame:
    if start > end:
        raise ValueError("Start date must be on or before end date.")
    mask = orders["purchase_date"].between(pd.Timestamp(start), pd.Timestamp(end))
    if states:
        mask &= orders["state"].isin(states)
    return orders.loc[mask].copy()


def previous_window(start: date, end: date) -> tuple[date, date]:
    length = (end - start).days + 1
    return start - timedelta(days=length), start - timedelta(days=1)


def delivered(orders: pd.DataFrame) -> pd.DataFrame:
    return orders.loc[orders["status"].eq("delivered")].copy()


def metrics(orders: pd.DataFrame) -> dict:
    complete = delivered(orders)
    customer_counts = complete.groupby("customer_key").size()
    known_delivery = complete["is_late"].dropna()
    reviewed = complete["review_score"].dropna()
    count = len(complete)
    customers = len(customer_counts)
    return {
        "all_orders": len(orders), "delivered_orders": count,
        "sales_cents": int(complete["sales_cents"].sum()),
        "freight_cents": int(complete["freight_cents"].sum()),
        "aov_cents": float(complete["sales_cents"].sum()) / count if count else None,
        "customers": customers,
        "repeat_customers": int(customer_counts.gt(1).sum()),
        "repeat_pct": 100.0 * customer_counts.gt(1).mean() if customers else None,
        "late_orders": int(known_delivery.sum()), "delivery_eligible": len(known_delivery),
        "late_pct": 100.0 * known_delivery.mean() if len(known_delivery) else None,
        "review_mean": float(reviewed.mean()) if len(reviewed) else None,
        "reviewed_orders": len(reviewed),
        "median_delivery_days": float(complete["delivery_days"].median()) if complete["delivery_days"].notna().any() else None,
        "cancelled_orders": int(orders["status"].eq("canceled").sum()),
    }


def monthly(orders: pd.DataFrame) -> pd.DataFrame:
    complete = delivered(orders)
    if complete.empty:
        return pd.DataFrame(columns=["month", "sales_brl", "orders", "aov_brl"])
    complete["month"] = complete["purchase_date"].dt.to_period("M").dt.to_timestamp()
    result = complete.groupby("month").agg(sales_cents=("sales_cents", "sum"), orders=("order_id", "size")).reset_index()
    result["sales_brl"] = result["sales_cents"] / 100
    result["aov_brl"] = result["sales_brl"] / result["orders"]
    return result


def category_performance(orders: pd.DataFrame, categories: pd.DataFrame) -> pd.DataFrame:
    selected = categories.loc[categories["order_id"].isin(delivered(orders)["order_id"])]
    result = selected.groupby("category").agg(sales_cents=("sales_cents", "sum"),
        items=("item_count", "sum"), orders=("order_id", "nunique")).reset_index()
    result["sales_brl"] = result["sales_cents"] / 100
    total = result["sales_cents"].sum()
    result["share_pct"] = 100 * result["sales_cents"] / total if total else 0.0
    return result.sort_values("sales_cents", ascending=False).reset_index(drop=True)


def state_performance(orders: pd.DataFrame) -> pd.DataFrame:
    result = delivered(orders).groupby("state").agg(sales_cents=("sales_cents", "sum"),
        orders=("order_id", "size"), delivery_eligible=("is_late", "count"),
        late_orders=("is_late", "sum"), review_mean=("review_score", "mean"),
        reviewed_orders=("review_score", "count"), median_days=("delivery_days", "median")).reset_index()
    result["sales_brl"] = result["sales_cents"] / 100
    result["late_pct"] = 100 * result["late_orders"] / result["delivery_eligible"].replace(0, float("nan"))
    return result.sort_values("sales_cents", ascending=False).reset_index(drop=True)


def review_comparison(orders: pd.DataFrame) -> pd.DataFrame:
    complete = delivered(orders).dropna(subset=["is_late", "review_score"]).copy()
    complete["delivery"] = complete["is_late"].map({0: "On time", 1: "Late"})
    return complete.groupby("delivery").agg(mean_review=("review_score", "mean"),
        reviewed_orders=("order_id", "size")).reset_index()


def insight_cards(orders: pd.DataFrame, categories: pd.DataFrame) -> list[dict]:
    result = []
    by_category = category_performance(orders, categories)
    if not by_category.empty:
        lead = by_category.iloc[0]
        result.append({"title": "Protect the leading category", "evidence":
            f"{lead['category'].replace('_', ' ').title()} contributes {lead['share_pct']:.1f}% of delivered merchandise sales.",
            "action": "Review availability and supplier coverage before expanding promotion. Sales alone do not establish margin."})
    by_state = state_performance(orders)
    eligible = by_state.loc[by_state["delivery_eligible"].ge(100)]
    if not eligible.empty:
        slow = eligible.sort_values("late_pct", ascending=False).iloc[0]
        result.append({"title": "Investigate delivery reliability", "evidence":
            f"{slow['state']} has {slow['late_pct']:.1f}% late deliveries across {int(slow['delivery_eligible']):,} eligible orders (minimum 100 per state).",
            "action": "Audit carrier routes and promised delivery windows in this state before changing service commitments."})
    comparison = review_comparison(orders).set_index("delivery")
    if {"Late", "On time"}.issubset(comparison.index):
        late, ontime = comparison.loc["Late"], comparison.loc["On time"]
        result.append({"title": "Connect service to customer experience", "evidence":
            f"Late orders average {late['mean_review']:.2f}/5 from {int(late['reviewed_orders']):,} reviews; on-time orders average {ontime['mean_review']:.2f}/5 from {int(ontime['reviewed_orders']):,}.",
            "action": "Investigate the review gap and test proactive delivery updates. This observed association does not prove causation."})
    return result
