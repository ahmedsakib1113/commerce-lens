# Architecture

```mermaid
flowchart LR
    A[Olist public ZIP] --> B[Python CSV validation]
    B --> C[Decimal amounts to integer cents]
    C --> D[(Normalized SQLite warehouse)]
    D --> E[SQL order and category marts]
    E --> F[Integrity and reconciliation checks]
    F --> G[Compressed CSV snapshots + SHA-256 manifest]
    G --> H[Shared pandas analytics]
    H --> I[Interactive Streamlit dashboard]
    H --> J[HTML and Markdown analyst report]
    H --> K[CSV and JSON evidence]
```

The dashboard reads portable, verified snapshots instead of maintaining a live database connection. A fresh clone can display the historical dataset without a source download or paid service. The separately rebuilt SQLite warehouse exposes the full SQL analysis for review.

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--o{ ORDER_ITEMS : contains
    PRODUCTS ||--o{ ORDER_ITEMS : identifies
    ORDERS ||--o{ REVIEWS : receives
    ORDERS ||--|| ORDER_FACTS : preserves
    ORDER_FACTS ||--o{ CATEGORY_FACTS : contributes
```

Foreign keys enforce normalized relationships. `order_facts` combines pre-aggregated items and a single latest review. `category_facts` retains item-level sales by category without allocating whole-order totals repeatedly.

The pipeline validates before replacing the generated warehouse. Raw source data, the generated SQLite database, virtual environments, and temporary artifacts are ignored by Git. Derived snapshots retain the original source's data license; code has a separate MIT license.

The app has no authentication, payment integration, external AI API, or cloud database. Its local server binds to loopback. Streamlit usage telemetry is disabled. A Google Fonts stylesheet is optional presentation only; system fonts provide a fallback.
