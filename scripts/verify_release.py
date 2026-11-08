"""Check shipped evidence and, when available, reconcile it to warehouse SQL."""
import json
import sqlite3
import sys
from contextlib import closing
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from commercelens.analytics import filter_orders, load_data, metrics


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.local = []

    def handle_starttag(self, tag, attributes):
        for name, value in attributes:
            if name == "href" and value and not value.startswith(("http:", "https:", "#", "mailto:")):
                self.local.append(value)


def main():
    orders, _, manifest = load_data()
    scoped = filter_orders(orders, date(2017, 1, 1), date(2018, 8, 31))
    actual = metrics(scoped)
    evidence = json.loads((ROOT/"docs/evidence/metrics.json").read_text())
    assert actual == evidence, "Report metric evidence does not match shipped snapshots"
    for name in ["monthly", "categories", "states"]:
        frame = pd.read_csv(ROOT/f"docs/evidence/{name}.csv")
        assert int(frame.sales_cents.sum()) == actual["sales_cents"], f"{name} does not reconcile"
    page = (ROOT/"docs/index.html").read_text(encoding="utf-8")
    parser = Links()
    parser.feed(page)
    for link in parser.local:
        assert (ROOT/"docs"/link).is_file(), f"Broken report download: {link}"
    assert f"{actual['delivered_orders']:,}" in page
    database = ROOT/"data/warehouse.sqlite"
    if database.exists():
        with closing(sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)) as connection:
            row = connection.execute("""
                SELECT COUNT(*), SUM(sales_cents), SUM(is_late), COUNT(is_late)
                FROM order_facts WHERE status = 'delivered'
                AND purchase_date BETWEEN ? AND ?
            """, ("2017-01-01", "2018-08-31")).fetchone()
            assert row == (actual["delivered_orders"], actual["sales_cents"],
                           actual["late_orders"], actual["delivery_eligible"])
            print("Independent SQLite query reconciles to dashboard and report:", row)
    else:
        print("Source warehouse not present; shipped snapshots and evidence were verified.")
    assert all(manifest["quality"]["checks"].values())
    print(f"Verified {len(orders):,} orders, report metrics, three evidence exports, and {len(parser.local)} report links.")


if __name__ == "__main__":
    main()
