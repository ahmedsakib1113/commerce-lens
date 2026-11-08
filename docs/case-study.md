# CommerceLens: e-commerce business insights

## Business question

Where should an e-commerce team investigate sales concentration and delivery performance?

## Scope

Historical Olist orders purchased from **1 January 2017 to 31 August 2018**, all Brazilian destination states. The source archive contains 99,441 orders across 2016–2018. The default scope avoids sparse launch and closing months. Results describe this dataset and period.

## Results

| Metric | Verified result |
| --- | ---: |
| All order statuses in scope | 99,092 |
| Delivered orders | 96,211 |
| Delivered merchandise sales | R$ 13,181,027.13 |
| Average delivered order value | R$ 137.00 |
| Late deliveries / eligible deliveries | 6,531 / 96,203 |
| Late delivery rate | 6.79% |
| Average latest review on delivered orders | 4.16 / 5 |
| Repeat customers within scope | 2,789 / 93,104 (3.00%) |

## 1. Protect the leading category

Health Beauty contributes 9.3% of delivered merchandise sales.

**Recommended next step:** Review availability and supplier coverage before expanding promotion. Sales alone do not establish margin.

## 2. Investigate delivery reliability

AL has 21.5% late deliveries across 396 eligible orders (minimum 100 per state).

**Recommended next step:** Audit carrier routes and promised delivery windows in this state before changing service commitments.

## 3. Connect service to customer experience

Late orders average 2.27/5 from 6,378 reviews; on-time orders average 4.29/5 from 89,182.

**Recommended next step:** Investigate the review gap and test proactive delivery updates. This observed association does not prove causation.

## Method and limits

Each order is counted once after aggregating line items and choosing its latest review. Sales are item prices on delivered orders, excluding freight. Money is stored in integer BRL cents. Lateness compares calendar dates and excludes missing actual/estimated dates. Repeat purchasing is measured only within the selected window, using the stable customer identifier.

The data has no product costs, refund ledger, campaign spend, or inventory history. It cannot establish profit, return rates, advertising ROI, or stock availability. Customer review differences are observational and may reflect confounding factors. Historical results do not describe current market conditions.

## Reproduce and review

Run `python scripts/build_report.py` to regenerate this report and the CSV evidence. Read the SQL in `sql/business_questions.sql`, metric definitions in `docs/methodology.md`, and the checksum/quality manifest in `data/processed/manifest.json`.

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Data and derived snapshots: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
