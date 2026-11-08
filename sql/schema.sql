-- Raw tables intentionally retain only fields used in this analysis.
-- Money uses integer Brazilian-real cents to avoid floating-point drift.
PRAGMA foreign_keys = ON;
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT NOT NULL,
    state TEXT NOT NULL
);
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    status TEXT NOT NULL,
    purchased_at TEXT NOT NULL,
    delivered_at TEXT,
    estimated_at TEXT
);
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    category TEXT NOT NULL
);
CREATE TABLE category_translation (
    category TEXT PRIMARY KEY,
    category_en TEXT NOT NULL
);
CREATE TABLE order_items (
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    item_number INTEGER NOT NULL,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
    freight_cents INTEGER NOT NULL CHECK(freight_cents >= 0),
    PRIMARY KEY(order_id, item_number)
);
-- An order can have multiple reviews. Rank them before joining to orders.
CREATE TABLE reviews (
    review_id TEXT NOT NULL,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
    created_at TEXT,
    answered_at TEXT
);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_reviews_order ON reviews(order_id);
CREATE INDEX idx_orders_purchase ON orders(purchased_at);
