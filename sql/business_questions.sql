-- Run against data/warehouse.sqlite after: python scripts/build_data.py build
-- 1. Monthly delivered merchandise sales. Freight is separate; this is not profit.
SELECT SUBSTR(purchase_date, 1, 7) AS month,
       COUNT(*) AS delivered_orders,
       ROUND(SUM(sales_cents) / 100.0, 2) AS merchandise_sales_brl,
       ROUND(AVG(sales_cents) / 100.0, 2) AS average_order_value_brl
FROM order_facts WHERE status = 'delivered'
GROUP BY month ORDER BY month;

-- 2. Which categories contribute the most delivered merchandise sales?
SELECT c.category, ROUND(SUM(c.sales_cents) / 100.0, 2) AS sales_brl,
       COUNT(DISTINCT c.order_id) AS orders_containing_category
FROM category_facts c JOIN order_facts o USING(order_id)
WHERE o.status = 'delivered'
GROUP BY c.category ORDER BY SUM(c.sales_cents) DESC LIMIT 10;

-- 3. On-time performance by destination state; require 100 known-date orders.
SELECT state, COUNT(is_late) AS eligible_orders,
       ROUND(100.0 * SUM(is_late) / NULLIF(COUNT(is_late), 0), 2) AS late_pct,
       ROUND(AVG(delivery_days), 1) AS mean_calendar_delivery_days
FROM order_facts WHERE status = 'delivered'
GROUP BY state HAVING COUNT(is_late) >= 100 ORDER BY late_pct DESC;

-- 4. Association between delivery lateness and latest review, not causation.
SELECT CASE is_late WHEN 1 THEN 'Late' ELSE 'On time' END AS delivery_group,
       COUNT(review_score) AS reviewed_orders, ROUND(AVG(review_score), 2) AS mean_review
FROM order_facts
WHERE status = 'delivered' AND is_late IS NOT NULL AND review_score IS NOT NULL
GROUP BY is_late;

-- 5. Customers with multiple delivered orders in this historical observation window.
WITH customer_orders AS (
    SELECT customer_key, COUNT(*) AS delivered_orders
    FROM order_facts WHERE status = 'delivered'
    GROUP BY customer_key
)
SELECT COUNT(*) AS customers,
       SUM(delivered_orders > 1) AS repeat_customers,
       ROUND(100.0 * SUM(delivered_orders > 1) / NULLIF(COUNT(*), 0), 2) AS repeat_pct
FROM customer_orders;
