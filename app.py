"""CommerceLens business insights dashboard. Run: streamlit run app.py"""
from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from commercelens.analytics import (
    category_performance, delivered, filter_orders, insight_cards, load_data,
    metrics, monthly, previous_window, review_comparison, state_performance,
)

st.set_page_config(page_title="CommerceLens · Business Insights", page_icon="◈", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp{font-family:'DM Sans',sans-serif}
h1,h2,h3{font-family:'Manrope',sans-serif!important;letter-spacing:-.045em}
.block-container{max-width:1440px;padding-top:2.7rem;padding-bottom:3rem}
[data-testid="stSidebar"]{border-right:1px solid #e2e7eb;background:#fff}
[data-testid="stSidebar"] .block-container{padding-top:2rem}
[data-testid="stHeader"]{background:transparent}
[data-testid="stMetric"]{background:#fff;border:1px solid #e3e8ed;border-radius:13px;padding:19px 19px 15px;min-height:135px}
[data-testid="stMetricLabel"]{color:#607180;font-size:13px}
[data-testid="stMetricValue"]{font-family:'Manrope',sans-serif;font-size:28px;font-weight:800;letter-spacing:-1px}
[data-testid="stMetricDelta"]{font-size:12px}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:14px}
.eyebrow{color:#6b7f8b;letter-spacing:2px;font-size:10px;font-weight:700;text-transform:uppercase;margin:0 0 10px}
.brand{font-family:'Manrope',sans-serif;font-size:25px;font-weight:800;letter-spacing:-1px;color:#173c34}
.brand-icon{color:#147d64;font-size:30px;vertical-align:middle;margin-right:7px}
.brand-sub{font-size:10px;letter-spacing:2px;color:#83918f;margin:3px 0 30px 39px}
.hero-title{font-size:35px;font-weight:800;margin:0;color:#192b39;line-height:1.25}
.hero-sub{color:#6c7d8a;font-size:14px;line-height:1.7;margin:9px 0 25px}
.badge{display:inline-block;color:#16745e;background:#e6f3ed;border:1px solid #cfe8db;padding:6px 11px;border-radius:30px;font-size:11px;font-weight:600}
.section-note{font-size:12px;color:#788894;line-height:1.6;margin-bottom:13px}
.insight{background:#fff;border:1px solid #e0e7e8;border-left:3px solid #147d64;border-radius:10px;padding:20px 22px;margin:12px 0}
.insight-title{font-size:16px;font-weight:700;color:#234637;margin-bottom:8px}
.insight-evidence{font-size:14px;line-height:1.7;color:#354c5a;margin-bottom:9px}
.insight-action{font-size:13px;line-height:1.6;color:#6b7d86}
.source-note{font-size:11px;color:#7a8c95;line-height:1.7;border-top:1px solid #e1e7eb;padding-top:17px;margin-top:28px}
.sidebar-note{font-size:11px;line-height:1.75;color:#80918f;background:#f3f7f5;padding:14px;border-radius:9px;margin-top:24px}
button[kind="secondary"]{border-radius:8px}
@media(max-width:700px){.block-container{padding:1.6rem 1rem}.hero-title{font-size:28px}[data-testid="stMetricValue"]{font-size:24px}}
</style>""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def cached_data():
    return load_data()


def brl(cents):
    return "—" if cents is None else f"R$ {cents / 100:,.0f}"


def pct(value):
    return "—" if value is None else f"{value:.1f}%"


def style_chart(chart):
    return chart.configure_view(strokeWidth=0).configure_axis(
        gridColor="#edf0f3", domain=False, labelColor="#70808e", titleColor="#70808e",
        labelFont="sans-serif", titleFont="sans-serif", labelFontSize=11,
    ).configure_legend(labelColor="#607180", title=None)


def delta(current, previous, enabled=True):
    if not enabled or current is None or previous is None or previous == 0:
        return None
    return f"{(current / previous - 1) * 100:+.1f}% vs prior period"


try:
    orders, categories, manifest = cached_data()
except (OSError, ValueError, KeyError) as error:
    st.error(f"The verified data snapshot could not be loaded: {error}")
    st.code("python scripts/build_data.py download\npython scripts/build_data.py build")
    st.stop()

with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-icon">◈</span>CommerceLens</div><div class="brand-sub">BUSINESS INTELLIGENCE</div>', unsafe_allow_html=True)
    st.caption("WORKSPACE")
    page = st.radio("Explore", ["Overview", "Products & customers", "Delivery & experience", "Insights & methodology"], label_visibility="collapsed")
    st.divider()
    st.caption("ANALYSIS SCOPE")
    period = st.selectbox("Purchase period", ["Core trading period", "All available history", "Custom dates"],
        help="Core period is January 2017–August 2018. Sparse launch and closing months are excluded by default.")
    min_date, max_date = orders["purchase_date"].min().date(), orders["purchase_date"].max().date()
    if period == "Core trading period":
        start, end = date(2017, 1, 1), date(2018, 8, 31)
    elif period == "All available history":
        start, end = min_date, max_date
    else:
        dates = st.date_input("Purchase dates", value=(date(2018, 1, 1), date(2018, 8, 31)),
                              min_value=min_date, max_value=max_date, format="DD MMM YYYY")
        if len(dates) != 2:
            st.info("Choose both a start and an end date.")
            st.stop()
        start, end = dates
    states = st.multiselect("Destination states", sorted(orders["state"].unique()), placeholder="All Brazilian states",
                           help="Leave empty to include every destination state.")
    st.caption(f"{start:%d %b %Y} → {end:%d %b %Y}")
    st.markdown('<div class="sidebar-note"><b>REAL DATA. HISTORICAL VIEW.</b><br>Olist marketplace orders, 2016–2018.<br>Currency: Brazilian real (BRL).<br>No simulated business results.</div>', unsafe_allow_html=True)
    st.link_button("View project on GitHub ↗", "https://github.com/ahmedsakib1113/commerce-lens", use_container_width=True)

selected = filter_orders(orders, start, end, states)
current = metrics(selected)
prev_start, prev_end = previous_window(start, end)
previous = metrics(filter_orders(orders, prev_start, prev_end, states))
comparison_available = prev_start >= min_date and prev_end <= max_date
scope = ", ".join(states) if states else "All states"
titles = {"Overview": ("The business, at a glance.", "Track sales performance, understand demand, and find the next question worth asking."),
          "Products & customers": ("Understand what drives demand.", "Explore category contribution, regional concentration, and repeat purchasing."),
          "Delivery & experience": ("See the story after checkout.", "Examine delivery reliability and its association with customer experience."),
          "Insights & methodology": ("Turn evidence into action.", "Trace each recommendation to the data, the definitions, and the limitations.")}
left, right = st.columns([4, 1])
with left:
    st.markdown(f'<div class="eyebrow">COMMERCE ANALYTICS / {html.escape(page.upper())}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero-title">{titles[page][0]}</div><div class="hero-sub">{titles[page][1]}</div>', unsafe_allow_html=True)
with right:
    st.markdown('<div style="text-align:right;padding-top:8px"><span class="badge">● Verified public dataset</span></div>', unsafe_allow_html=True)
st.caption(f"{start:%d %b %Y} – {end:%d %b %Y}  ·  {scope}  ·  {len(selected):,} source orders in scope")

if selected.empty:
    st.info("No orders match this date and state selection. Expand the period or clear the state filter.")
    st.stop()

if page == "Overview":
    columns = st.columns(4)
    columns[0].metric("Delivered merchandise sales", brl(current["sales_cents"]), delta(current["sales_cents"], previous["sales_cents"], comparison_available), help="Sum of item prices for delivered orders. Excludes freight; not profit or accounting-recognized revenue.")
    columns[1].metric("Delivered orders", f'{current["delivered_orders"]:,}', delta(current["delivered_orders"], previous["delivered_orders"], comparison_available))
    columns[2].metric("Average order value", brl(current["aov_cents"]), delta(current["aov_cents"], previous["aov_cents"], comparison_available))
    columns[3].metric("Late delivery rate", pct(current["late_pct"]), help=f'{current["late_orders"]:,} late / {current["delivery_eligible"]:,} delivered orders with both dates. Delivery on the estimated calendar date counts as on time.')
    if comparison_available:
        st.caption(f"Sales/order deltas use the preceding {(end-start).days+1:,}-day period: {prev_start:%d %b %Y}–{prev_end:%d %b %Y}, with the same state filter.")
    else:
        st.caption("Prior-period deltas are hidden because the full preceding comparison window is outside the source history.")
    st.write("")
    chart_column, side_column = st.columns([1.8, 1])
    with chart_column, st.container(border=True):
        st.subheader("Sales over time")
        st.markdown('<div class="section-note">Delivered merchandise sales · BRL · grouped by purchase month</div>', unsafe_allow_html=True)
        trend = monthly(selected)
        if not trend.empty:
            area = alt.Chart(trend).mark_area(line={"color": "#147d64", "strokeWidth": 2.5}, color=alt.Gradient(
                gradient="linear", stops=[alt.GradientStop(color="#cbe9de", offset=0), alt.GradientStop(color="#f9fcfa", offset=1)], x1=1,x2=1,y1=1,y2=0)).encode(
                x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %y", tickCount=7)),
                y=alt.Y("sales_brl:Q", title=None, axis=alt.Axis(format="~s")),
                tooltip=[alt.Tooltip("month:T", title="Purchase month", format="%b %Y"), alt.Tooltip("sales_brl:Q", title="Sales (BRL)", format=",.2f"), alt.Tooltip("orders:Q", title="Delivered orders", format=",")]).properties(height=285)
            st.altair_chart(style_chart(area), use_container_width=True)
        else:
            st.info("No delivered orders in this selection.")
        st.caption("Edge months can be partial when custom dates are selected.")
    with side_column, st.container(border=True):
        st.subheader("Where sales come from")
        region = state_performance(selected).head(7)
        chart = alt.Chart(region).mark_bar(color="#91b8ac", cornerRadiusEnd=4).encode(
            y=alt.Y("state:N", sort="-x", title=None), x=alt.X("sales_brl:Q", title=None, axis=alt.Axis(format="~s")),
            tooltip=["state", alt.Tooltip("sales_brl:Q", title="Sales (BRL)", format=",.2f"), "orders"]).properties(height=285)
        st.altair_chart(style_chart(chart), use_container_width=True)
        st.caption("Top seven destination states by item sales.")
    a, b = st.columns([1.6, 1])
    with a, st.container(border=True):
        st.subheader("A closer look")
        for card in insight_cards(selected, categories)[:2]:
            st.markdown(f"**{card['title']}**")
            st.write(card["evidence"])
    with b, st.container(border=True):
        st.subheader("Order outcomes")
        statuses = selected["status"].value_counts().rename_axis("Status").reset_index(name="Orders")
        st.dataframe(statuses, hide_index=True, use_container_width=True)
        st.caption("Outcome counts include every order status in scope; sales metrics use delivered orders only.")

elif page == "Products & customers":
    a,b,c,d = st.columns(4)
    a.metric("Purchasing customers", f'{current["customers"]:,}', help="Distinct customer_unique_id values among delivered orders in the selected scope.")
    b.metric("Repeat customers", f'{current["repeat_customers"]:,}', help="Customers with at least two delivered orders within the selected dates and states.")
    c.metric("Observed repeat rate", pct(current["repeat_pct"]), help="Repeat customers / distinct delivered-order customers in this selection. This is not a churn or lifetime retention estimate.")
    d.metric("Freight / item sales", pct(100*current["freight_cents"]/current["sales_cents"] if current["sales_cents"] else None), help="Recorded freight charges / delivered merchandise sales. These are charges, not shipping costs or margin.")
    st.write("")
    performance = category_performance(selected, categories)
    with st.container(border=True):
        st.subheader("Category contribution")
        count = st.slider("Categories to display", 5, 20, 10)
        chart = alt.Chart(performance.head(count)).mark_bar(color="#147d64", cornerRadiusEnd=4).encode(
            y=alt.Y("category:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
            x=alt.X("sales_brl:Q", title="Delivered merchandise sales (BRL)", axis=alt.Axis(format="~s")),
            tooltip=["category", alt.Tooltip("sales_brl:Q", title="Sales (BRL)", format=",.2f"), alt.Tooltip("share_pct:Q", title="Share (%)", format=".1f"), "orders", "items"]).properties(height=max(240, count*29))
        st.altair_chart(style_chart(chart), use_container_width=True)
        st.caption("Category order counts can overlap because an order may contain several categories. Item sales reconcile to the overall delivered total.")
    st.subheader("Category detail")
    query = st.text_input("Find a category", placeholder="Try health, furniture, or sports")
    shown = performance.loc[performance["category"].str.contains(query, case=False, regex=False)]
    st.dataframe(shown[["category", "sales_brl", "share_pct", "orders", "items"]], hide_index=True, use_container_width=True,
        column_config={"sales_brl": st.column_config.NumberColumn("Sales (BRL)", format="%.2f"), "share_pct": st.column_config.NumberColumn("Sales share (%)", format="%.1f")})
    st.download_button("Download category analysis ↓", shown.to_csv(index=False).encode(), "commercelens-categories.csv", "text/csv")

elif page == "Delivery & experience":
    a,b,c,d = st.columns(4)
    a.metric("Late delivery rate", pct(current["late_pct"]))
    b.metric("Median delivery time", "—" if current["median_delivery_days"] is None else f'{current["median_delivery_days"]:.0f} days', help="Calendar days from purchase to delivery, for valid nonnegative durations.")
    c.metric("Average review", "—" if current["review_mean"] is None else f'{current["review_mean"]:.2f} / 5')
    d.metric("Reviewed delivered orders", f'{current["reviewed_orders"]:,}')
    st.caption(f'Delivery eligibility: {current["delivery_eligible"]:,} of {current["delivered_orders"]:,} delivered orders have both actual and estimated dates.')
    left,right = st.columns([1.5,1])
    with left, st.container(border=True):
        st.subheader("Reliability by destination")
        minimum = st.select_slider("Minimum eligible orders per state", options=[1, 25, 50, 100, 250, 500], value=100)
        by_state = state_performance(selected)
        eligible = by_state.loc[by_state["delivery_eligible"].ge(minimum)].sort_values("late_pct", ascending=False)
        if eligible.empty:
            st.info("No states meet this sample threshold. Lower it or widen the scope.")
        else:
            chart = alt.Chart(eligible).mark_bar(color="#ca9867", cornerRadiusEnd=3).encode(
                y=alt.Y("state:N", sort="-x", title=None), x=alt.X("late_pct:Q", title="Late deliveries (%)"),
                tooltip=["state", alt.Tooltip("late_pct:Q", format=".1f"), "delivery_eligible", "late_orders"]).properties(height=max(240,len(eligible)*21))
            st.altair_chart(style_chart(chart), use_container_width=True)
    with right, st.container(border=True):
        st.subheader("Delivery & review scores")
        comparison = review_comparison(selected)
        if comparison.empty:
            st.info("No orders have both a known delivery outcome and a review.")
        else:
            chart = alt.Chart(comparison).mark_bar(cornerRadiusEnd=5, size=55).encode(
                x=alt.X("delivery:N", title=None), y=alt.Y("mean_review:Q", title="Average review / 5", scale=alt.Scale(domain=[0,5])),
                color=alt.Color("delivery:N", scale=alt.Scale(domain=["On time","Late"], range=["#147d64","#ca9867"]), legend=None),
                tooltip=["delivery", alt.Tooltip("mean_review:Q", format=".2f"), "reviewed_orders"]).properties(height=290)
            st.altair_chart(style_chart(chart), use_container_width=True)
            st.dataframe(comparison, hide_index=True, use_container_width=True)
        st.caption("Latest review per order. An association can reflect other factors; this comparison does not establish causation.")
    with st.expander("Explore state-level evidence"):
        st.dataframe(by_state.drop(columns="sales_cents"), hide_index=True, use_container_width=True)
        st.download_button("Download delivery analysis ↓", by_state.to_csv(index=False).encode(), "commercelens-delivery.csv", "text/csv")

else:
    st.subheader("Evidence → recommendation")
    cards = insight_cards(selected, categories)
    if not cards:
        st.info("This selection does not contain enough delivered-order evidence for an insight card.")
    for index, card in enumerate(cards,1):
        st.markdown(f'<div class="insight"><div class="eyebrow">OBSERVATION {index:02d}</div><div class="insight-title">{html.escape(card["title"])}</div><div class="insight-evidence">{html.escape(card["evidence"])}</div><div class="insight-action"><b>Suggested action:</b> {html.escape(card["action"])}</div></div>', unsafe_allow_html=True)
    st.subheader("Definitions you can audit")
    definitions = pd.DataFrame([
        ["Merchandise sales", "Sum of item prices on delivered orders; freight excluded. Not profit or accounting-recognized revenue."],
        ["Order value", "Delivered merchandise sales divided by distinct delivered orders."],
        ["Late delivery", "Actual delivery calendar date > estimated calendar date. Same-day delivery is on time."],
        ["Late rate denominator", "Delivered orders with both actual and estimated dates; missing dates excluded."],
        ["Review", "Latest answered review per order; creation time and review ID break ties."],
        ["Repeat customer", "At least two delivered orders by customer_unique_id inside the current date/state selection."],
        ["Time basis", "Purchase date defines every filter. Source timestamps are treated as recorded local dates; no UTC conversion."],
    ], columns=["Metric", "Definition"])
    st.dataframe(definitions, hide_index=True, use_container_width=True)
    with st.expander("Source provenance & data quality", expanded=False):
        st.write(f'Source orders: **{manifest["quality"]["rows"]["orders"]:,}** · Source line items: **{manifest["quality"]["rows"]["order_items"]:,}**')
        st.json(manifest)
    st.info("Historical Olist marketplace data (2016–2018) supports a case study, not a statement about today's market. Missing cost, returns/refund, marketing-spend, and inventory fields prevent profit, ROAS, stockout, and return-rate estimates. All recommendations require further business validation.")
    st.download_button("Download source manifest ↓", json.dumps(manifest,indent=2).encode(), "commercelens-manifest.json", "application/json")

with st.expander("Export the current order analysis"):
    st.caption("CSV contains derived order-level analysis with anonymized source identifiers. Filters match the current page.")
    st.download_button("Download filtered orders ↓", selected.to_csv(index=False).encode(), "commercelens-orders.csv", "text/csv")

st.markdown('<div class="source-note">CommerceLens · A reproducible business analytics case study<br>Source: <a href="https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce">Brazilian E-Commerce Public Dataset by Olist</a> · 2016–2018 · Dataset & derived snapshots: <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a> · Currency: BRL<br>Python + SQLite + Streamlit · Calculations run on verified historical records.</div>', unsafe_allow_html=True)
