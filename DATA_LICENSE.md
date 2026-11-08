# Dataset attribution and license

**Original dataset:** Brazilian E-Commerce Public Dataset by Olist.

**Source:** https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

**Dataset license:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International.

- License summary: https://creativecommons.org/licenses/by-nc-sa/4.0/
- Full legal text: https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode

The dataset, `data/processed/` snapshots, and data-derived report evidence are distributed under that same license. The MIT code license does not override the dataset's non-commercial or share-alike conditions.

## Changes made for this project

- Selected fields used in the analysis; excluded review text, exact timestamp times, city names, and geolocation fields from the published snapshots.
- Converted monetary amounts to integer BRL cents.
- Aggregated order items to one order row and separate order-category rows.
- Selected the latest review per order.
- Derived calendar-date lateness, delivery duration, and business metrics.
- Generated reports, charts, and CSV evidence from those derived records.

Published source identifiers are pseudonymous dataset IDs, not new personal information collected by this project. The raw archive is not checked in. Its SHA-256 and provenance are recorded in `data/processed/manifest.json`.

This project is a non-commercial educational portfolio case study. No endorsement by or affiliation with Olist is implied. Retain this attribution and the applicable license when sharing the data or derived evidence.
