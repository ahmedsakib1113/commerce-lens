import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from commercelens.pipeline import cents

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def warehouse():
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.executescript((ROOT/"sql/schema.sql").read_text())
        connection.executescript("""
        INSERT INTO customers VALUES ('c1','u1','SP'),('c2','u1','SP'),('c3','u3','RJ');
        INSERT INTO orders VALUES
          ('a','c1','delivered','2018-01-01 10:00:00','2018-01-05 20:00:00','2018-01-05 00:00:00'),
          ('b','c2','delivered','2018-01-02 10:00:00','2018-01-08 10:00:00','2018-01-07 00:00:00'),
          ('c','c3','delivered','2018-01-03 10:00:00',NULL,'2018-01-07 00:00:00');
        INSERT INTO products VALUES ('p1','books'),('p2','gifts');
        INSERT INTO category_translation VALUES ('books','books');
        INSERT INTO order_items VALUES ('a',1,'p1',1000,100),('a',2,'p2',2000,200),('b',1,'p1',5000,500);
        INSERT INTO reviews VALUES
          ('r1','a',1,'2018-01-06','2018-01-07'),
          ('r2','a',5,'2018-01-06','2018-01-08'),
          ('r3','b',2,'2018-01-09','2018-01-10');
        """)
        connection.executescript((ROOT/"sql/marts.sql").read_text())
        yield connection


def test_many_items_and_reviews_do_not_fan_out_order_totals(warehouse):
    assert warehouse.execute("SELECT COUNT(*), SUM(sales_cents) FROM order_facts").fetchone() == (3,8000)
    assert warehouse.execute("SELECT sales_cents, review_score FROM order_facts WHERE order_id='a'").fetchone() == (3000,5)
    assert warehouse.execute("SELECT SUM(sales_cents) FROM category_facts").fetchone()[0] == 8000


def test_estimated_day_is_inclusive_and_missing_is_unknown(warehouse):
    rows = dict(warehouse.execute("SELECT order_id,is_late FROM order_facts"))
    assert rows == {"a": 0, "b": 1, "c": None}


def test_missing_items_preserve_source_orders(warehouse):
    assert warehouse.execute("SELECT sales_cents,item_count FROM order_facts WHERE order_id='c'").fetchone() == (0,0)


def test_money_is_exact_and_invalid_amounts_rejected():
    assert cents("19.99") == 1999
    assert cents("0.10") + cents("0.20") == 30
    assert cents("12.345") == 1235
    for value in ["-1", "NaN", "Infinity"]:
        with pytest.raises(ValueError):
            cents(value)
