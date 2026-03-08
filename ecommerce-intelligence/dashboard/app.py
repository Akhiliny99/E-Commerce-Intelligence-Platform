

import os
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()


st.set_page_config(
    page_title="E-Commerce Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

from database.models import get_engine

logger = logging.getLogger(__name__)


@st.cache_resource
def get_db_engine():
    return get_engine()


def run_query(sql: str, params: dict = None) -> pd.DataFrame:
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    except Exception as e:
        st.error(f"DB Error: {e}")
        return pd.DataFrame()


# ── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.image("https://em-content.zobj.net/source/google/387/shopping-cart_1f6d2.png", width=60)
st.sidebar.title("🛒 E-Commerce Intelligence")
st.sidebar.markdown("---")

pages = ["📊 Overview", "📈 Price Trends", "🏆 Top Products", "🔔 Alerts", "🕷️ Scrape Runs"]
page = st.sidebar.radio("Navigate", pages)

days_filter = st.sidebar.slider("Data Window (days)", 1, 90, 30)
source_filter = st.sidebar.multiselect(
    "Sources",
    options=["books.toscrape.com", "quotes.toscrape.com"],
    default=["books.toscrape.com", "quotes.toscrape.com"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Last Refresh**")
st.sidebar.caption(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()


# ── Helper: KPI card ──────────────────────────────────────────────────────
def kpi(label, value, delta=None, prefix="", suffix=""):
    st.metric(label=label, value=f"{prefix}{value}{suffix}", delta=delta)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 1: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════
if page == "📊 Overview":
    st.title("📊 Overview Dashboard")
    st.markdown(f"Showing data for the last **{days_filter} days**")
    st.markdown("---")

    # KPIs
    total_products = run_query("SELECT COUNT(*) as cnt FROM products").iloc[0]["cnt"] if not run_query("SELECT COUNT(*) as cnt FROM products").empty else 0
    total_scrapes = run_query("SELECT COUNT(*) as cnt FROM price_history").iloc[0]["cnt"] if not run_query("SELECT COUNT(*) as cnt FROM price_history").empty else 0
    total_alerts = run_query("SELECT COUNT(*) as cnt FROM price_alerts").iloc[0]["cnt"] if not run_query("SELECT COUNT(*) as cnt FROM price_alerts").empty else 0
    categories = run_query("SELECT COUNT(DISTINCT category) as cnt FROM products").iloc[0]["cnt"] if not run_query("SELECT COUNT(DISTINCT category) as cnt FROM products").empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Total Products", int(total_products))
    with c2: kpi("Price Records", int(total_scrapes))
    with c3: kpi("Active Alerts", int(total_alerts))
    with c4: kpi("Categories", int(categories))

    st.markdown("---")

    # Products by Category
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🗂️ Products by Category")
        df_cat = run_query("""
            SELECT category, COUNT(*) as count
            FROM products
            GROUP BY category
            ORDER BY count DESC
            LIMIT 15
        """)
        if not df_cat.empty:
            fig = px.bar(df_cat, x="count", y="category", orientation="h",
                         color="count", color_continuous_scale="Blues",
                         labels={"count": "Products", "category": "Category"})
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🌐 Products by Source")
        df_src = run_query("SELECT source, COUNT(*) as count FROM products GROUP BY source")
        if not df_src.empty:
            fig = px.pie(df_src, values="count", names="source", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

    # Availability breakdown
    st.subheader("📦 Stock Availability")
    df_avail = run_query("""
        SELECT lp.availability, COUNT(*) as count
        FROM latest_prices lp
        GROUP BY lp.availability
        ORDER BY count DESC
    """)
    if not df_avail.empty:
        color_map = {"In Stock": "#2ecc71", "Low Stock": "#f39c12", "Out of Stock": "#e74c3c"}
        fig = px.bar(df_avail, x="availability", y="count",
                     color="availability", color_discrete_map=color_map)
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 2: PRICE TRENDS
# ══════════════════════════════════════════════════════════════════════════
elif page == "📈 Price Trends":
    st.title("📈 Price Trends")

    # Search product
    search_term = st.text_input("🔍 Search product", placeholder="e.g. Python, Fiction...")

    if search_term:
        df_products = run_query("""
            SELECT product_id, title, category, source
            FROM products
            WHERE LOWER(title) LIKE :term
            LIMIT 20
        """, {"term": f"%{search_term.lower()}%"})

        if df_products.empty:
            st.warning("No products found.")
        else:
            selected = st.selectbox("Select Product", df_products["title"].tolist())
            product_id = df_products[df_products["title"] == selected]["product_id"].values[0]

            df_history = run_query("""
                SELECT price, original_price, discount_pct, rating, review_count, availability, scraped_at
                FROM price_history
                WHERE product_id = :pid
                ORDER BY scraped_at ASC
            """, {"pid": product_id})

            if not df_history.empty:
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("💰 Price Over Time")
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df_history["scraped_at"], y=df_history["original_price"].astype(float),
                        name="Original Price", line=dict(color="#e74c3c", dash="dash")
                    ))
                    fig.add_trace(go.Scatter(
                        x=df_history["scraped_at"], y=df_history["price"].astype(float),
                        name="Current Price", line=dict(color="#2ecc71"), fill="tozeroy"
                    ))
                    fig.update_layout(height=350, xaxis_title="Date", yaxis_title="Price (£)")
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    st.subheader("⭐ Rating Over Time")
                    fig2 = px.line(df_history, x="scraped_at", y="rating",
                                   markers=True, color_discrete_sequence=["#f39c12"])
                    fig2.update_layout(height=350)
                    st.plotly_chart(fig2, use_container_width=True)

                # Stats
                latest = df_history.iloc[-1]
                st.subheader("📋 Latest Snapshot")
                s1, s2, s3, s4 = st.columns(4)
                with s1: st.metric("Current Price", f"£{float(latest['price']):.2f}")
                with s2: st.metric("Rating", f"⭐ {float(latest['rating']):.1f}")
                with s3: st.metric("Reviews", int(latest["review_count"]))
                with s4: st.metric("Availability", latest["availability"])
    else:
        # Overall price distribution
        st.subheader("💰 Price Distribution Across All Products")
        df_all = run_query("SELECT price::float as price, category FROM latest_prices LIMIT 1000")
        if not df_all.empty:
            fig = px.histogram(df_all, x="price", nbins=50, color="category",
                               labels={"price": "Price (£)"})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📊 Average Price by Category")
        df_avg = run_query("""
            SELECT category, ROUND(AVG(price::numeric), 2) as avg_price,
                   ROUND(MIN(price::numeric), 2) as min_price,
                   ROUND(MAX(price::numeric), 2) as max_price
            FROM latest_prices
            GROUP BY category
            ORDER BY avg_price DESC
        """)
        if not df_avg.empty:
            st.dataframe(df_avg, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 3: TOP PRODUCTS
# ══════════════════════════════════════════════════════════════════════════
elif page == "🏆 Top Products":
    st.title("🏆 Top Products")

    tab1, tab2, tab3 = st.tabs(["Best Deals", "Highest Rated", "Most Reviewed"])

    with tab1:
        st.subheader("🔥 Best Deals (Highest Discount %)")
        df = run_query("""
            SELECT title, category, source,
                   price::float, original_price::float, discount_pct::float,
                   rating::float, availability
            FROM latest_prices
            WHERE discount_pct > 0
            ORDER BY discount_pct DESC
            LIMIT 20
        """)
        if not df.empty:
            fig = px.bar(df.head(10), x="discount_pct", y="title", orientation="h",
                         color="discount_pct", color_continuous_scale="RdYlGn",
                         labels={"discount_pct": "Discount %", "title": ""})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df[["title", "category", "price", "original_price", "discount_pct", "availability"]],
                         use_container_width=True)

    with tab2:
        st.subheader("⭐ Highest Rated Products")
        df = run_query("""
            SELECT title, category, price::float, rating::float, review_count, availability
            FROM latest_prices
            WHERE rating > 0
            ORDER BY rating DESC, review_count DESC
            LIMIT 20
        """)
        if not df.empty:
            st.dataframe(df, use_container_width=True)

    with tab3:
        st.subheader("💬 Most Reviewed Products")
        df = run_query("""
            SELECT title, category, price::float, rating::float, review_count
            FROM latest_prices
            WHERE review_count > 0
            ORDER BY review_count DESC
            LIMIT 20
        """)
        if not df.empty:
            fig = px.bar(df.head(10), x="review_count", y="title", orientation="h",
                         color="review_count", color_continuous_scale="Blues")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 4: ALERTS
# ══════════════════════════════════════════════════════════════════════════
elif page == "🔔 Alerts":
    st.title("🔔 Price Alerts")

    df_alerts = run_query("""
        SELECT pa.alert_type, pa.old_price::float, pa.new_price::float,
               pa.change_pct::float, pa.triggered_at, p.title, p.category, p.source
        FROM price_alerts pa
        JOIN products p ON p.product_id = pa.product_id
        ORDER BY pa.triggered_at DESC
        LIMIT 100
    """)

    if df_alerts.empty:
        st.info("No alerts yet. Run the scraper multiple times to generate price change alerts.")
    else:
        a1, a2, a3, a4 = st.columns(4)
        with a1: st.metric("Total Alerts", len(df_alerts))
        with a2: st.metric("Price Drops 📉", len(df_alerts[df_alerts["alert_type"] == "PRICE_DROP"]))
        with a3: st.metric("Price Rises 📈", len(df_alerts[df_alerts["alert_type"] == "PRICE_RISE"]))
        with a4: st.metric("Stock Changes", len(df_alerts[df_alerts["alert_type"].isin(["OUT_OF_STOCK", "BACK_IN_STOCK"])]))

        st.markdown("---")

        color_map = {
            "PRICE_DROP": "🟢",
            "PRICE_RISE": "🔴",
            "OUT_OF_STOCK": "⚫",
            "BACK_IN_STOCK": "🟡",
        }
        df_alerts["emoji"] = df_alerts["alert_type"].map(color_map)
        st.subheader("Recent Alerts")

        # Alert type filter
        alert_type_filter = st.multiselect(
            "Filter by type",
            options=df_alerts["alert_type"].unique().tolist(),
            default=df_alerts["alert_type"].unique().tolist(),
        )
        filtered = df_alerts[df_alerts["alert_type"].isin(alert_type_filter)]
        st.dataframe(
            filtered[["emoji", "alert_type", "title", "category", "old_price", "new_price", "change_pct", "triggered_at"]],
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("📊 Alert Distribution")
        fig = px.pie(df_alerts, names="alert_type", hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 5: SCRAPE RUNS
# ══════════════════════════════════════════════════════════════════════════
elif page == "🕷️ Scrape Runs":
    st.title("🕷️ Scrape Run History")

    df_runs = run_query("""
        SELECT spider_name, status, items_scraped, items_failed,
               duration_seconds, started_at, ended_at
        FROM scrape_runs
        ORDER BY started_at DESC
        LIMIT 50
    """)

    if df_runs.empty:
        st.info("No scrape runs recorded yet.")
    else:
        r1, r2, r3 = st.columns(3)
        with r1: st.metric("Total Runs", len(df_runs))
        with r2: st.metric("Total Items Scraped", int(df_runs["items_scraped"].sum()))
        with r3: st.metric("Success Rate", f"{len(df_runs[df_runs['status']=='SUCCESS'])/len(df_runs)*100:.0f}%")

        st.markdown("---")
        st.subheader("Run Log")

        def status_emoji(s):
            return {"SUCCESS": "✅", "FAILED": "❌", "PARTIAL": "⚠️", "RUNNING": "🔄"}.get(s, s)

        df_runs["status_display"] = df_runs["status"].apply(status_emoji)
        st.dataframe(
            df_runs[["status_display", "spider_name", "items_scraped", "items_failed", "duration_seconds", "started_at"]],
            use_container_width=True, hide_index=True,
        )

        st.subheader("📈 Items Scraped Over Time")
        fig = px.bar(df_runs.sort_values("started_at"), x="started_at", y="items_scraped",
                     color="spider_name", labels={"items_scraped": "Items", "started_at": "Run Time"})
        st.plotly_chart(fig, use_container_width=True)
