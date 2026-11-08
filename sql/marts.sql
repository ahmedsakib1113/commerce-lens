-- Grain: exactly one row per source order. Aggregate each many-side first.
CREATE TABLE order_facts AS
WITH item_totals AS (
    SELECT order_id, SUM(price_cents) AS sales_cents,
           SUM(freight_cents) AS freight_cents, COUNT(*) AS item_count
    FROM order_items GROUP BY order_id
), ranked_reviews AS (
    SELECT order_id, score,
           ROW_NUMBER() OVER (
               PARTITION BY order_id
               ORDER BY COALESCE(answered_at, created_at, '') DESC,
                        COALESCE(created_at, '') DESC, review_id DESC, rowid DESC
           ) AS review_rank
    FROM reviews
)
SELECT o.order_id, c.customer_unique_id AS customer_key, c.state,
       o.status, DATE(o.purchased_at) AS purchase_date,
       COALESCE(i.sales_cents, 0) AS sales_cents,
       COALESCE(i.freight_cents, 0) AS freight_cents,
       COALESCE(i.item_count, 0) AS item_count,
       DATE(o.delivered_at) AS delivered_date,
       DATE(o.estimated_at) AS estimated_date,
       CASE WHEN o.status = 'delivered' AND DATE(o.delivered_at) IS NOT NULL
                 AND DATE(o.estimated_at) IS NOT NULL
            THEN CAST(DATE(o.delivered_at) > DATE(o.estimated_at) AS INTEGER)
       END AS is_late,
       CASE WHEN o.status = 'delivered' AND DATE(o.delivered_at) >= DATE(o.purchased_at)
            THEN CAST(JULIANDAY(DATE(o.delivered_at)) - JULIANDAY(DATE(o.purchased_at)) AS INTEGER)
       END AS delivery_days,
       r.score AS review_score
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN item_totals i ON i.order_id = o.order_id
LEFT JOIN ranked_reviews r ON r.order_id = o.order_id AND r.review_rank = 1;
CREATE UNIQUE INDEX idx_fact_order ON order_facts(order_id);

-- Grain: one order-category pair. Product charts use item sales, never
-- duplicated order totals. Orders containing several categories appear once
-- in each category, so category order counts must not be summed.
CREATE TABLE category_facts AS
SELECT i.order_id,
       COALESCE(t.category_en, NULLIF(p.category, ''), 'uncategorized') AS category,
       SUM(i.price_cents) AS sales_cents,
       SUM(i.freight_cents) AS freight_cents, COUNT(*) AS item_count
FROM order_items i
JOIN products p ON p.product_id = i.product_id
LEFT JOIN category_translation t ON t.category = p.category
GROUP BY i.order_id, COALESCE(t.category_en, NULLIF(p.category, ''), 'uncategorized');
CREATE UNIQUE INDEX idx_category_order ON category_facts(order_id, category);
