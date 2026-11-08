# CommerceLens — E-commerce Business Insights

A complete business analytics case study using **99,441 real Olist orders**: a reproducible Python/SQLite pipeline, an interactive Streamlit dashboard, SQL business analysis, and an evidence-backed analyst report.

**[Read the hosted analyst report](https://ahmedsakib1113.github.io/commerce-lens/)** · **[Browse the case study](docs/case-study.md)** · **[Explore the SQL](sql/business_questions.sql)**

## The business problem

An e-commerce team needs to understand what drives sales, where delivery reliability needs investigation, and how delivery outcomes relate to customer experience. CommerceLens turns transaction-level records into auditable metrics and proposed business actions.

The default analysis covers **January 2017–August 2018**, avoiding sparse launch and closing months. It contains **96,211 delivered orders**, **R$13,181,027.13 in delivered merchandise sales**, and a **6.79% late-delivery rate** among eligible deliveries. These are historical dataset results, not current market estimates.

## What you can explore

| Dashboard page | Analysis |
| --- | --- |
| Overview | Delivered sales, orders, average order value, late rate, monthly trend, state contribution, order outcomes |
| Products & customers | Category contribution, category search, distinct purchasing customers, repeat purchasing within the selected window, freight-to-sales ratio |
| Delivery & experience | Delivery time, state lateness with adjustable sample thresholds, review differences between late and on-time deliveries |
| Insights & methodology | Calculated insight cards, recommended next steps, metric definitions, provenance, limitations |

Date and destination-state filters apply across pages. Category, delivery, and filtered order analyses can be exported as CSV. Missing values are explicit; no simulated measurements or invented financial results are used.

## Run the interactive dashboard

Requires **Python 3.12+**. The checked-in, compressed derived snapshots make the dashboard work immediately after dependency installation; a Kaggle account and a warehouse rebuild are not required to explore it.

```powershell
git clone https://github.com/ahmedsakib1113/commerce-lens.git
cd commerce-lens
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open **http://127.0.0.1:8501**. Windows users can also run `setup.cmd` once, then `start-dashboard.cmd`. On macOS/Linux, use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

The [hosted report](https://ahmedsakib1113.github.io/commerce-lens/) is a fixed-scope HTML report with downloadable evidence. The Streamlit app is the interactive dashboard and runs locally; the two have the same default analysis scope.

## Reproduce the source → SQL → report pipeline

```powershell
# Download the public source archive (approximately 42 MB; no paid API).
.\.venv\Scripts\python.exe scripts/build_data.py download

# Build the normalized SQLite warehouse, derived snapshots, checksums, and quality manifest.
.\.venv\Scripts\python.exe scripts/build_data.py build

# Recheck SQLite integrity, foreign keys, grain, dates, and monetary reconciliations.
.\.venv\Scripts\python.exe scripts/build_data.py validate

# Regenerate the case study, hosted report, and CSV evidence.
.\.venv\Scripts\python.exe scripts/build_report.py
```

The source endpoint can change or require Kaggle sign-in. If downloading fails, obtain the archive from the [original dataset page](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), save it as `data/raw/olist.zip`, and run the build command. Never put account credentials into project files.

The warehouse is written to **`data/warehouse.sqlite`** and is ignored by Git. You can open it in a SQLite client and run [these five business queries](sql/business_questions.sql). Raw source files and Python environments are also ignored. SHA-256 checksums verify the shipped snapshots before the dashboard loads them.

Restart the dashboard after rebuilding snapshots to clear its in-memory data cache. Run `python scripts/verify_release.py` to reconcile report evidence against the snapshots and the warehouse when present.

## Analytical care

- **No inflated joins:** item totals and the latest review are reduced to one row per order before joining. Product-category analysis has its own documented grain.
- **Exact money:** original decimal amounts become integer BRL cents before aggregation. Sales exclude freight and use delivered orders only.
- **Explicit delivery eligibility:** lateness compares actual and estimated calendar dates; missing dates stay unknown. Delivery on the promised date counts as on time.
- **Honest customer metrics:** stable customer identifiers distinguish customers from orders. Repeat purchasing is measured within the selected window, not presented as churn or lifetime retention.
- **Measured recommendations:** review differences show association, not causation. State recommendations require at least 100 eligible orders.
- **Clear limits:** the source cannot establish profit, refunds, ROAS, inventory availability, or today's market conditions.

See [metric definitions and data quality](docs/methodology.md), [architecture](docs/architecture.md), and [validation](docs/validation.md).

## Project structure

```text
app.py                         Interactive dashboard
src/commercelens/analytics.py   Shared business calculations
src/commercelens/pipeline.py    Source loading, cleaning, SQLite build, validation
sql/schema.sql                 Normalized warehouse schema
sql/marts.sql                  Order and category fact tables
sql/business_questions.sql     Five analyst queries
scripts/build_data.py          Download/build/validate entry point
scripts/build_report.py        Reproducible report and evidence generation
data/processed/                Verified derived snapshots and source manifest
docs/index.html                Static analyst report for GitHub Pages
docs/evidence/                 CSV/JSON results behind the report
tests/                         SQL, metric, data-integrity, and app checks
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests exercise join fan-out, exact money, late-date boundaries, unknown denominators, state/date filtering, cancellation exclusions, overlapping category orders, snapshot tampering, real-data reconciliations, and all four dashboard pages. GitHub Actions runs the suite on Windows and Linux for pushes and pull requests.

## Cost and deployment

The project requires no paid API, subscription, cloud database, domain, or API key. The public report uses GitHub Pages; the interactive app uses your local computer. [GitHub Pages is available for public repositories on GitHub Free](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).

GitHub Pages can serve the report from `main` → `/docs`. It cannot execute the Python dashboard. Updating the report means regenerating `docs/` and pushing the changes.

## Credits and licenses

Source: **Brazilian E-Commerce Public Dataset by Olist**, [Kaggle dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), covering 2016–2018. Dataset, derived snapshots, and data-derived report evidence retain **[CC BY-NC-SA 4.0](DATA_LICENSE.md)**. This is a non-commercial portfolio case study with no Olist affiliation or endorsement.

Original project code is **[MIT licensed](LICENSE)**. The data license is separate and governs data reuse. Python, SQLite, pandas, Streamlit, and Altair power the analysis and dashboard.
