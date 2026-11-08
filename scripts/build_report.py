"""Generate a shareable analyst report and CSV evidence from the shipped marts."""
from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from commercelens.analytics import (category_performance, filter_orders, insight_cards,
    load_data, metrics, monthly, review_comparison, state_performance)


def main():
    orders, categories, manifest = load_data()
    scope = filter_orders(orders, date(2017,1,1), date(2018,8,31))
    values = metrics(scope)
    trend = monthly(scope)
    products = category_performance(scope,categories)
    states = state_performance(scope)
    reviews = review_comparison(scope)
    insights = insight_cards(scope,categories)
    target = ROOT/"docs/evidence"
    target.mkdir(parents=True,exist_ok=True)
    for name,frame in [("monthly",trend),("categories",products),("states",states),("delivery-reviews",reviews)]:
        frame.to_csv(target/f"{name}.csv",index=False)
    (target/"metrics.json").write_text(json.dumps(values,indent=2)+"\n",encoding="utf-8")

    def bars(frame, label, amount, formatter):
        maximum = frame[amount].max()
        return "".join(f'<div class="bar-row"><span>{html.escape(str(row[label]).replace("_"," ").title())}</span><div class="track"><div class="fill" style="width:{row[amount]/maximum*100:.2f}%"></div></div><b>{formatter(row[amount])}</b></div>' for _,row in frame.iterrows())

    monthly_bars = bars(trend.assign(period=trend["month"].dt.strftime("%b %Y")),"period","sales_brl",lambda n:f"R$ {n:,.0f}")
    product_bars = bars(products.head(8),"category","sales_brl",lambda n:f"R$ {n:,.0f}")
    cards = "".join(f'<article class="insight"><small>OBSERVATION {i:02d}</small><h3>{html.escape(card["title"])}</h3><p>{html.escape(card["evidence"])}</p><p class="action"><b>Suggested action.</b> {html.escape(card["action"])}</p></article>' for i,card in enumerate(insights,1))
    (ROOT/"docs/case-study.md").write_text(f'''# CommerceLens: e-commerce business insights

## Business question

Where should an e-commerce team investigate sales concentration and delivery performance?

## Scope

Historical Olist orders purchased from **1 January 2017 to 31 August 2018**, all Brazilian destination states. The source archive contains {len(orders):,} orders across 2016–2018. The default scope avoids sparse launch and closing months. Results describe this dataset and period.

## Results

| Metric | Verified result |
| --- | ---: |
| All order statuses in scope | {values['all_orders']:,} |
| Delivered orders | {values['delivered_orders']:,} |
| Delivered merchandise sales | R$ {values['sales_cents']/100:,.2f} |
| Average delivered order value | R$ {values['aov_cents']/100:,.2f} |
| Late deliveries / eligible deliveries | {values['late_orders']:,} / {values['delivery_eligible']:,} |
| Late delivery rate | {values['late_pct']:.2f}% |
| Average latest review on delivered orders | {values['review_mean']:.2f} / 5 |
| Repeat customers within scope | {values['repeat_customers']:,} / {values['customers']:,} ({values['repeat_pct']:.2f}%) |

''' + "\n\n".join(f"## {i}. {card['title']}\n\n{card['evidence']}\n\n**Recommended next step:** {card['action']}" for i,card in enumerate(insights,1)) + '''

## Method and limits

Each order is counted once after aggregating line items and choosing its latest review. Sales are item prices on delivered orders, excluding freight. Money is stored in integer BRL cents. Lateness compares calendar dates and excludes missing actual/estimated dates. Repeat purchasing is measured only within the selected window, using the stable customer identifier.

The data has no product costs, refund ledger, campaign spend, or inventory history. It cannot establish profit, return rates, advertising ROI, or stock availability. Customer review differences are observational and may reflect confounding factors. Historical results do not describe current market conditions.

## Reproduce and review

Run `python scripts/build_report.py` to regenerate this report and the CSV evidence. Read the SQL in `sql/business_questions.sql`, metric definitions in `docs/methodology.md`, and the checksum/quality manifest in `data/processed/manifest.json`.

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Data and derived snapshots: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
''',encoding="utf-8")

    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="CommerceLens: a reproducible business insights case study using 99,441 real Olist e-commerce orders."><title>CommerceLens | Business Insights Case Study</title>
<style>
:root{{--green:#15785f;--ink:#1d303c;--muted:#6a7c86;--line:#dfe6e9}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:#f5f7f8;color:var(--ink);font:15px/1.7 system-ui,sans-serif}}a{{color:var(--green)}}header{{background:white;border-bottom:1px solid var(--line)}}nav{{max-width:1200px;padding:20px 28px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}}.brand{{font-size:23px;font-weight:800;letter-spacing:-1px}}.brand i{{font-style:normal;color:var(--green);margin-right:9px}}nav a{{font-size:13px;text-decoration:none;margin-left:16px}}main{{max-width:1200px;padding:55px 28px;margin:auto}}.eyebrow,small{{font-size:10px;font-weight:700;letter-spacing:2px;color:var(--green)}}h1{{font-size:clamp(32px,5vw,52px);line-height:1.18;letter-spacing:-2px;margin:13px 0}}.intro{{max-width:730px;color:var(--muted);font-size:17px}}.pill{{display:inline-block;background:#e6f1eb;color:#22654f;padding:5px 11px;border-radius:20px;font-size:11px;margin-top:13px}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin:32px 0}}.metric,.panel,.insight{{background:white;border:1px solid var(--line);border-radius:13px;padding:24px}}.metric span{{display:block;color:var(--muted);font-size:12px}}.metric strong{{font-size:27px;letter-spacing:-1px}}.metric small{{display:block;letter-spacing:0;font-size:11px;color:var(--muted);font-weight:400}}.columns{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}h2{{font-size:23px;letter-spacing:-.7px;margin:0 0 6px}}h3{{font-size:19px;letter-spacing:-.5px;margin:7px 0}}.note{{font-size:12px;color:var(--muted);margin:0 0 22px}}.bar-row{{display:grid;grid-template-columns:125px 1fr 85px;align-items:center;gap:8px;margin:10px 0;font-size:11px}}.bar-row span{{line-height:1.3}}.bar-row b{{font-size:10px;text-align:right;white-space:nowrap}}.track{{background:#eef3f1;height:13px;border-radius:3px;overflow:hidden}}.fill{{height:100%;background:#75aa94;border-radius:3px}}section{{margin-top:32px;scroll-margin-top:25px}}.insight{{margin:15px 0;border-left:3px solid var(--green)}}.insight p{{font-size:14px;margin:9px 0}}.action{{color:var(--muted)}}.downloads{{display:flex;gap:12px;flex-wrap:wrap;margin-top:20px}}.button{{text-decoration:none;background:var(--green);color:white;padding:10px 17px;border-radius:7px;font-size:12px;font-weight:600}}.button.secondary{{background:white;color:var(--green);border:1px solid var(--line)}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid var(--line)}}.table-scroll{{overflow-x:auto}}footer{{color:var(--muted);font-size:11px;border-top:1px solid var(--line);padding-top:23px;margin-top:40px}}.method{{font-size:13px;color:var(--muted)}}@media(max-width:760px){{main{{padding:32px 18px}}nav{{padding:15px 18px}}.metrics{{grid-template-columns:1fr 1fr;gap:10px}}.metric{{padding:17px}}.metric strong{{font-size:22px}}.columns{{grid-template-columns:1fr}}.panel{{padding:18px}}.bar-row{{grid-template-columns:105px 1fr 75px}}nav a{{margin-left:0;margin-right:10px}}}}@media print{{body{{background:white}}main{{padding:10px}}nav a,.downloads{{display:none}}.insight,.panel,.metric{{break-inside:avoid}}}}
</style></head><body><header><nav><div class="brand"><i>◈</i>CommerceLens</div><div><a href="#performance">Performance</a><a href="#insights">Business insights</a><a href="#methodology">Methodology</a><a href="https://github.com/ahmedsakib1113/commerce-lens">GitHub ↗</a></div></nav></header>
<main><div class="eyebrow">BUSINESS INTELLIGENCE · E-COMMERCE CASE STUDY</div><h1>From orders to decisions.</h1><p class="intro">An evidence-led look at sales concentration, delivery reliability, and customer experience across real Olist marketplace orders.</p><span class="pill">● Historical data · Jan 2017–Aug 2018 · All states · BRL</span>
<div class="metrics"><div class="metric"><span>Delivered merchandise sales</span><strong>R$ {values['sales_cents']/100:,.0f}</strong><small>Item prices · freight excluded</small></div><div class="metric"><span>Delivered orders</span><strong>{values['delivered_orders']:,}</strong><small>One row per order</small></div><div class="metric"><span>Average order value</span><strong>R$ {values['aov_cents']/100:,.2f}</strong><small>Delivered merchandise only</small></div><div class="metric"><span>Late delivery rate</span><strong>{values['late_pct']:.1f}%</strong><small>{values['late_orders']:,} / {values['delivery_eligible']:,} eligible deliveries</small></div></div>
<section id="performance" class="columns"><div class="panel"><h2>The sales trajectory</h2><p class="note">Delivered merchandise sales by purchase month. All 20 core trading months.</p>{monthly_bars}<a href="evidence/monthly.csv">Download monthly evidence ↓</a></div><div class="panel"><h2>What drives the basket?</h2><p class="note">Eight leading categories by delivered merchandise sales.</p>{product_bars}<p class="method">Item-level sales avoid double counting multi-category orders. Category order counts can overlap.</p><a href="evidence/categories.csv">Download category evidence ↓</a><h3 style="margin-top:35px">Customer experience</h3><p class="method">The latest available review is selected once per order. Only orders with known delivery outcomes and a review enter this comparison.</p><div class="table-scroll">{reviews.round(2).to_html(index=False,border=0)}</div></div></section>
<section id="insights"><div class="eyebrow">EVIDENCE → ACTION</div><h2>Three questions for the business.</h2><p class="note">Observations are calculated from the same scope as the figures above. Recommendations are proposed next steps.</p>{cards}</section>
<section id="methodology" class="panel"><h2>Built to be checked.</h2><p class="method">Python cleans the public source into a normalized SQLite warehouse. SQL creates one order fact per order and a separate order-category mart. Integer cents preserve monetary totals; eight automated quality checks reconcile the result. The Streamlit app provides date and state filters, category search, delivery sample thresholds, and CSV exports.</p><p class="method">Source coverage: {manifest['quality']['date_range'][0]}–{manifest['quality']['date_range'][1]}; {len(orders):,} source orders and {manifest['quality']['rows']['order_items']:,} line items. This report uses 1 Jan 2017–31 Aug 2018 to avoid sparse launch/closing months. All figures are historical.</p><p class="method"><b>Limits:</b> Sales exclude freight and are not profit. Missing delivery dates are excluded from lateness. Review comparisons show association, not causation. Costs, refunds, ad spend, and stock history are unavailable. Repeat purchases within a window are not lifetime retention.</p><div class="downloads"><a class="button" href="https://github.com/ahmedsakib1113/commerce-lens">Explore code & run the dashboard ↗</a><a class="button secondary" href="evidence/states.csv">State-level evidence ↓</a><a class="button secondary" href="evidence/metrics.json">Metric results ↓</a></div><p class="note" style="margin-top:18px;margin-bottom:0">This hosted page is the fixed-scope analyst report. Run the Streamlit dashboard from the repository for interactive date and state analysis.</p></section>
<footer>Source: <a href="https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce">Brazilian E-Commerce Public Dataset by Olist</a> · Data and derived evidence: <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a>. Analysis and charts are derived from the source; no Olist endorsement is implied.<br>CommerceLens · Python / SQLite / Streamlit · <a href="https://github.com/ahmedsakib1113/commerce-lens">Reproduce this analysis</a></footer></main></body></html>'''
    (ROOT/"docs/index.html").write_text(page,encoding="utf-8")
    (ROOT/"docs/.nojekyll").touch()
    print(json.dumps(values,indent=2))
    print("Generated docs/case-study.md, docs/index.html, and docs/evidence/")


if __name__ == "__main__":
    main()
