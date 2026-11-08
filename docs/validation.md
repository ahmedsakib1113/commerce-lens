# Validation evidence

Verified locally on **8 November 2026**, using Windows and Python 3.12.7. Versions used for verification are recorded in `requirements-lock.txt`.

## Source and warehouse

The public Olist ZIP was downloaded from Kaggle and hashed. Its SHA-256 is recorded in `data/processed/manifest.json`. The normalized warehouse was built from the source, with all eight enforced quality checks passing:

1. SQLite integrity is `ok`.
2. No foreign-key violations.
3. Every source order produces one order fact.
4. Order fact IDs are unique.
5. Source line-item sales reconcile exactly to order fact sales.
6. Source line-item sales reconcile exactly to category fact sales.
7. Purchase dates are valid.
8. Only delivered orders have a known lateness outcome.

Source rows: **99,441 orders**, **112,650 items**, **32,951 products**, **99,224 review rows**. Published snapshots retain all source orders and carry SHA-256 checksums checked by the app.

## Independent SQL → snapshot → report check

`python scripts/verify_release.py` executes an independent SQLite query for the default date window and checks the result against the shipped snapshot and report metrics:

```text
Delivered orders:       96,211
Item sales (BRL cents): 1,318,102,713
Late deliveries:        6,531
Eligible deliveries:    96,203
```

Monthly, category, and state evidence exports each reconcile to the same sales total. The HTML report's four local download links resolve to existing files.

## Automated application and analytical checks

`python -m pytest -q` passes **12 tests** covering exact monetary conversion, join fan-out, latest-review selection, same-day delivery, unknown delivery dates, preserved orders with no items, date/state filters, cancelled-order exclusion, repeat customers, overlapping category counts, empty selections, snapshot tampering, real-data reconciliations, and all dashboard pages.

The final suite completed in the project's freshly created independent environment: **12 passed in 36.70s**. `python -m pip check` reported **No broken requirements found**. The release verification also passed in that environment.

Streamlit AppTest verifies the default metric cards, changes the destination filter to SP, navigates all four pages, and checks category search without application exceptions. The default dashboard shows **R$13,181,027** in merchandise sales and **96,211** delivered orders.

## HTTP and visual boundaries

The local dashboard returned **HTTP 200** for its main page and **HTTP 200 `ok`** for `/_stcore/health`.

Visual browser verification could not be completed. The in-app browser access host was unavailable, and the native computer-use tool stopped because it could not confidently determine the browser URL. No browser screenshot, mobile screenshot, or browser-console pass is claimed. The app and report include responsive layouts; those layouts still need visual review on actual desktop/mobile browsers.

GitHub publication and CI status should be checked on the repository's Actions page. Local tests do not prove that hosted CI has run.
