# Metric definitions and data quality

## Scope and time

The original dataset contains orders purchased from 4 September 2016 to 17 October 2018. The default dashboard and generated report cover **1 January 2017–31 August 2018**. This avoids sparse launch/closing months while retaining 20 calendar months. Custom dates and all-history selections remain available.

Filters always use the **purchase calendar date** and **customer destination state**. Source timestamps are treated as recorded local dates, without assigning an undocumented time zone or converting them to UTC. Monthly charts use purchase month; custom start/end dates can create partial months.

Prior-period deltas compare the same number of inclusive calendar days immediately before the selection, with the same state filter. They are hidden when the full prior window falls outside source coverage. Comparable dates do not guarantee equal seasonality or business maturity.

## Warehouse grains

| Table | Grain |
| --- | --- |
| customers | One source customer_id (source order-specific customer record) |
| orders | One order_id |
| order_items | One order_id + item_number |
| products | One product_id |
| category_translation | One source category |
| reviews | One source review row; repeated order IDs intentionally allowed |
| order_facts | Exactly one source order, including orders with no item rows |
| category_facts | One order + normalized category |

`customer_unique_id` is the stable customer identifier for repeat purchasing. Using the order-specific `customer_id` would undercount repeat buyers.

Item totals are grouped before joining orders. Reviews use `ROW_NUMBER()` by answered timestamp descending, then creation timestamp, review ID, and source row as deterministic tie-breakers. Only rank 1 joins the order fact. This prevents a multi-item, multi-review order from multiplying merchandise sales.

## Metrics

| Metric | Numerator | Denominator / eligibility |
| --- | --- | --- |
| Delivered merchandise sales | Sum of delivered-order item prices | Delivered orders within purchase-date/state scope; freight excluded |
| Average order value | Delivered merchandise sales | Count of delivered orders |
| Delivered orders | Distinct delivered order IDs | One-row order mart |
| Late delivery rate | Delivered orders with actual date later than estimated date | Delivered orders with both calendar dates |
| Median delivery days | Calendar-day difference: delivery minus purchase | Delivered orders with valid, nonnegative duration |
| Average review | Latest review scores | Delivered orders with a valid latest review |
| On-time vs late reviews | Latest review scores in each group | Delivered orders with known lateness and a valid review |
| Purchasing customers | Distinct customer_unique_id | Delivered orders inside selected scope |
| Repeat customer rate | Customers with >=2 delivered orders in scope | Distinct delivered-order customers in scope |
| Freight-to-sales ratio | Recorded freight charges on delivered orders | Delivered merchandise sales; not freight cost or margin |
| Category sales share | Delivered line-item sales in the category | All delivered line-item sales in scope |

Money is read with `Decimal`, converted to integer cents with half-up rounding, and aggregated exactly in SQLite. Display division by 100 converts cents to BRL. Category order counts overlap across multi-category orders; sum item sales, not category order counts, to reconcile totals.

The `canceled` source status is not inferred to be a refund or a returned product. Revenue-recognition timing and refund adjustments are outside the available data. Orders delivered after the selected purchase-date window are included if their purchase date is inside it; status reflects the dataset's final recorded outcome, not an as-of historical snapshot.

## Source quality observations

The build manifest records actual counts and eight enforced checks. At the recorded build:

- 99,441 source orders and 112,650 line items; every order is preserved in the order mart.
- 99,224 review rows represent 98,673 reviewed order IDs, leaving **551 extra review rows** that must not multiply orders.
- **8 delivered orders** lack one or both delivery dates and are excluded from late-rate eligibility.
- **646 delivered orders** lack an available review; they remain in sales and delivery analysis.
- **2 nonempty source product categories** lack an English translation and retain their original names. Empty categories are labeled `uncategorized`.

Checks cover SQLite integrity, foreign keys, one fact per source order, unique order IDs, reconciliation of item and category sales, valid purchase dates, and lateness only on delivered orders. The app also verifies snapshot checksums, order counts, category grain, and category order references.

## Limits and recommended follow-up

This dataset has no complete cost ledger, refunds/returns ledger, inventory history, or marketing spend. Profit, ROAS, stockouts, and return rates cannot be calculated reliably. Repeat purchasing is a descriptive window metric; customer acquisition timing and observation length affect it.

Review/lateness comparisons are observational. Product mix, geography, order value, seller, and carrier could confound the association. Recommended next steps should be tested with operational records and controlled changes where practical. Sparse groups are unstable; delivery recommendations require at least 100 eligible orders per state.

The data describes a historical marketplace in Brazil. It does not establish today's performance, the entire Brazilian market, or causal business effects.
