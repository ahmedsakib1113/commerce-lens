"""Download the public source and build auditable SQLite and CSV data marts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import urllib.request
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"
DOWNLOAD = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "order_items": "olist_order_items_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
}


def cents(value: str) -> int:
    amount = Decimal(value)
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"Invalid nonnegative monetary amount: {value!r}")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def download(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".download")
    request = urllib.request.Request(DOWNLOAD, headers={"User-Agent": "CommerceLens/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    if not zipfile.is_zipfile(temporary):
        temporary.unlink(missing_ok=True)
        raise ValueError("Source did not return a ZIP. Download the dataset manually from Kaggle.")
    temporary.replace(destination)
    print(f"Downloaded {destination.stat().st_size:,} bytes to {destination}")


def source_table(archive: zipfile.ZipFile, filename: str) -> pd.DataFrame:
    matches = [name for name in archive.namelist() if Path(name).name == filename]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {filename} in archive")
    with archive.open(matches[0]) as source:
        return pd.read_csv(source, dtype=str, keep_default_na=False)


def prepare_tables(archive: zipfile.ZipFile) -> dict[str, pd.DataFrame]:
    raw = {name: source_table(archive, filename) for name, filename in FILES.items()}
    customers = raw["customers"][["customer_id", "customer_unique_id", "customer_state"]].rename(
        columns={"customer_state": "state"})
    orders = raw["orders"][["order_id", "customer_id", "order_status", "order_purchase_timestamp",
                            "order_delivered_customer_date", "order_estimated_delivery_date"]].rename(columns={
        "order_status": "status", "order_purchase_timestamp": "purchased_at",
        "order_delivered_customer_date": "delivered_at", "order_estimated_delivery_date": "estimated_at"})
    for name in ["purchased_at", "delivered_at", "estimated_at"]:
        values = orders[name]
        invalid = values.ne("") & pd.to_datetime(values, errors="coerce").isna()
        if invalid.any() or (name == "purchased_at" and values.eq("").any()):
            raise ValueError(f"Unparseable or missing required order timestamp: {name}")
        orders[name] = values.replace("", None)
    products = raw["products"][["product_id", "product_category_name"]].rename(
        columns={"product_category_name": "category"})
    translation = raw["category_translation"].rename(columns={
        "product_category_name": "category", "product_category_name_english": "category_en"})
    items = raw["order_items"][["order_id", "order_item_id", "product_id", "price", "freight_value"]].rename(
        columns={"order_item_id": "item_number", "price": "price_cents", "freight_value": "freight_cents"})
    items["item_number"] = items["item_number"].astype(int)
    for name in ["price_cents", "freight_cents"]:
        items[name] = items[name].map(cents)
    reviews = raw["reviews"][["review_id", "order_id", "review_score", "review_creation_date",
                              "review_answer_timestamp"]].rename(columns={
        "review_score": "score", "review_creation_date": "created_at", "review_answer_timestamp": "answered_at"})
    reviews["score"] = reviews["score"].astype(int)
    for name in ["created_at", "answered_at"]:
        invalid = reviews[name].ne("") & pd.to_datetime(reviews[name], errors="coerce").isna()
        if invalid.any():
            raise ValueError(f"Unparseable review timestamp: {name}")
        reviews[name] = reviews[name].replace("", None)
    return {"customers": customers, "orders": orders, "products": products,
            "category_translation": translation, "order_items": items, "reviews": reviews}


def validate_database(connection: sqlite3.Connection) -> dict:
    def scalar(sql: str):
        return connection.execute(sql).fetchone()[0]

    checks = {
        "integrity": scalar("PRAGMA integrity_check") == "ok",
        "foreign_keys": not connection.execute("PRAGMA foreign_key_check").fetchall(),
        "one_fact_per_order": scalar("SELECT COUNT(*) FROM orders") == scalar("SELECT COUNT(*) FROM order_facts"),
        "unique_orders": scalar("SELECT COUNT(*) = COUNT(DISTINCT order_id) FROM order_facts") == 1,
        "item_sales_reconcile": scalar("SELECT SUM(price_cents) FROM order_items") == scalar("SELECT SUM(sales_cents) FROM order_facts"),
        "category_sales_reconcile": scalar("SELECT SUM(price_cents) FROM order_items") == scalar("SELECT SUM(sales_cents) FROM category_facts"),
        "valid_dates": scalar("SELECT COUNT(*) FROM order_facts WHERE purchase_date IS NULL") == 0,
        "late_only_delivered": scalar("SELECT COUNT(*) FROM order_facts WHERE is_late IS NOT NULL AND status <> 'delivered'") == 0,
    }
    if not all(checks.values()):
        raise ValueError(f"Data quality checks failed: {checks}")
    counts = {table: scalar(f'SELECT COUNT(*) FROM "{table}"') for table in [*FILES, "order_facts", "category_facts"]}
    return {"checks": checks, "rows": counts,
            "date_range": connection.execute("SELECT MIN(purchase_date), MAX(purchase_date) FROM order_facts").fetchone(),
            "missing_delivery_dates": scalar("SELECT COUNT(*) FROM order_facts WHERE status='delivered' AND is_late IS NULL"),
            "missing_reviews_delivered": scalar("SELECT COUNT(*) FROM order_facts WHERE status='delivered' AND review_score IS NULL"),
            "extra_reviews": scalar("SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM reviews"),
            "untranslated_categories": scalar("SELECT COUNT(DISTINCT p.category) FROM products p LEFT JOIN category_translation t USING(category) WHERE t.category IS NULL AND p.category <> ''")}


def build(archive_path: Path, root: Path = ROOT) -> dict:
    if not archive_path.is_file():
        raise FileNotFoundError("Run python scripts/build_data.py download first, or supply --archive.")
    data = root / "data"
    data.mkdir(exist_ok=True)
    temporary = data / "warehouse.build.sqlite"
    temporary.unlink(missing_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        tables = prepare_tables(archive)
    try:
        with closing(sqlite3.connect(temporary)) as connection, connection:
            connection.executescript((root / "sql/schema.sql").read_text(encoding="utf-8"))
            for name, frame in tables.items():
                frame.to_sql(name, connection, if_exists="append", index=False)
            connection.executescript((root / "sql/marts.sql").read_text(encoding="utf-8"))
            quality = validate_database(connection)
            output = data / "processed"
            output.mkdir(exist_ok=True)
            # mtime=0 makes gzip exports byte-for-byte stable across rebuilds.
            for table, filename in [("order_facts", "orders.csv.gz"), ("category_facts", "categories.csv.gz")]:
                frame = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY order_id", connection)
                for column in ["is_late", "delivery_days", "review_score"]:
                    if column in frame:
                        frame[column] = frame[column].astype("Int64")
                frame.to_csv(output / filename, index=False, compression={"method": "gzip", "mtime": 0})
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    temporary.replace(data / "warehouse.sqlite")
    with archive_path.open("rb") as source_file:
        source_sha256 = hashlib.file_digest(source_file, "sha256").hexdigest()
    manifest = {
        "dataset": "Brazilian E-Commerce Public Dataset by Olist",
        "source_url": SOURCE, "download_url": DOWNLOAD,
        "source_sha256": source_sha256,
        "license": "CC BY-NC-SA 4.0", "currency": "BRL",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "quality": quality,
        "exports": {name: hashlib.sha256((data / "processed" / name).read_bytes()).hexdigest()
                    for name in ["orders.csv.gz", "categories.csv.gz"]},
    }
    (data / "processed/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["download", "build", "validate"])
    parser.add_argument("--archive", type=Path, default=ROOT / "data/raw/olist.zip")
    arguments = parser.parse_args()
    if arguments.command == "download":
        download(arguments.archive)
    elif arguments.command == "build":
        build(arguments.archive)
    else:
        database = ROOT / "data/warehouse.sqlite"
        if not database.exists():
            raise FileNotFoundError("Build the warehouse before validating it.")
        with closing(sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)) as connection:
            print(json.dumps(validate_database(connection), indent=2))


if __name__ == "__main__":
    main()
