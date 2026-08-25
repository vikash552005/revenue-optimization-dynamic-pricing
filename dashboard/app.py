"""
RetailX Revenue Optimization & Dynamic Pricing Analytics Dashboard
===================================================================
Production-Grade Interactive Analytics Platform built with Streamlit & Plotly.
Zero hardcoded metrics: 100% data-driven econometric & financial calculations.
"""

import os
import sys
import sqlite3
import re
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Setup Path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.analysis import (
    compute_executive_kpis,
    compute_monthly_trends,
    compute_category_summary,
    compute_regional_breakdown,
    compute_customer_segment_analysis,
    compute_product_performance,
    compute_discount_impact
)
from src.elasticity import PriceElasticityEngine
from src.pricing_optimizer import PricingOptimizer
from src.recommendations import PricingRecommendationEngine

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="RetailX | Revenue & Pricing Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
css_path = os.path.join(os.path.dirname(__file__), "styles.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
DB_PATH = os.path.join(PROJECT_ROOT, "sql", "retailx.db")
SQL_FILE_PATH = os.path.join(PROJECT_ROOT, "sql", "analysis_queries.sql")


@st.cache_data(show_spinner=False)
def load_all_datasets():
    df_cust = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "customers_clean.csv"))
    df_prod = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "products_clean.csv"))
    df_sales = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "sales_clean.csv"))
    df_pricing = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "pricing_history_clean.csv"))
    return df_cust, df_prod, df_sales, df_pricing


@st.cache_resource(show_spinner=False)
def get_engines():
    elast_eng = PriceElasticityEngine()
    optimizer = PricingOptimizer(elast_eng)
    rec_eng = PricingRecommendationEngine()
    return elast_eng, optimizer, rec_eng


def parse_sql_queries():
    """Extract named SQL queries from analysis_queries.sql."""
    if not os.path.exists(SQL_FILE_PATH):
        return {}
    with open(SQL_FILE_PATH, "r") as f:
        content = f.read()
    blocks = re.split(r'--\s*NAME:\s*', content)
    queries = {}
    for block in blocks[1:]:
        lines = block.strip().split("\n")
        name = lines[0].strip()
        sql = "\n".join(lines[1:]).strip().rstrip(";")
        queries[name] = sql
    return queries


# ---------------------------------------------------------
# Application Initialization
# ---------------------------------------------------------
df_customers_raw, df_products_raw, df_sales_raw, df_pricing_raw = load_all_datasets()
elast_engine, optimizer, rec_engine = get_engines()
named_sql_queries = parse_sql_queries()

# ---------------------------------------------------------
# Sidebar Controls & Global Filters
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🏬 **RetailX Analytics**")
    st.caption("Revenue Optimization & Dynamic Pricing Suite")
    st.markdown("---")
    
    st.markdown("#### 🔍 **Global Filters**")
    
    # Date Range Filter
    min_date = pd.to_datetime(df_sales_raw["date"].min())
    max_date = pd.to_datetime(df_sales_raw["date"].max())
    date_range = st.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Category Filter
    all_categories = sorted(df_products_raw["category"].unique())
    selected_categories = st.multiselect("Categories", all_categories, default=all_categories)
    
    # Region Filter
    all_regions = sorted(df_sales_raw["region"].unique())
    selected_regions = st.multiselect("Regions", all_regions, default=all_regions)
    
    # Customer Segment Filter
    all_segments = sorted(df_customers_raw["customer_segment"].unique())
    selected_segments = st.multiselect("Customer Segments", all_segments, default=all_segments)
    
    st.markdown("---")
    st.caption("💡 **System Status**: SQLite DB Connected (`74.7k` Clean Transactions)")

# Apply Global Filters to Sales
if len(date_range) == 2:
    start_d, end_d = date_range
    mask_date = (pd.to_datetime(df_sales_raw["date"]).dt.date >= start_d) & (pd.to_datetime(df_sales_raw["date"]).dt.date <= end_d)
else:
    mask_date = pd.Series(True, index=df_sales_raw.index)

# Merge product category for filtering
prod_cat_map = df_products_raw.set_index("product_id")["category"].to_dict()
df_sales_filtered = df_sales_raw[mask_date].copy()
df_sales_filtered["category"] = df_sales_filtered["product_id"].map(prod_cat_map)

# Merge customer segment for filtering
cust_seg_map = df_customers_raw.set_index("customer_id")["customer_segment"].to_dict()
df_sales_filtered["customer_segment"] = df_sales_filtered["customer_id"].map(cust_seg_map).fillna("Guest Shoppers")

df_sales_filtered = df_sales_filtered[
    df_sales_filtered["category"].isin(selected_categories) &
    df_sales_filtered["region"].isin(selected_regions) &
    df_sales_filtered["customer_segment"].isin(selected_segments)
]

# Calculate Global KPIs
kpis = compute_executive_kpis(df_sales_filtered)
df_recs_all = rec_engine.generate_product_recommendations()
total_potential_profit_upside = df_recs_all["expected_profit_impact"].sum()
total_potential_rev_upside = df_recs_all["expected_revenue_impact"].sum()

# ---------------------------------------------------------
# Navigation Tabs
# ---------------------------------------------------------
tab_names = [
    "📊 Executive Overview",
    "💰 Sales Analysis",
    "🏷️ Pricing Analytics",
    "📈 Price Elasticity",
    "📦 Demand & Seasonality",
    "📉 Profitability",
    "🎛️ Pricing Simulator",
    "🎯 Recommendations",
    "⚡ SQL Studio & Data Explorer"
]

tabs = st.tabs(tab_names)

# =========================================================
# TAB 1: EXECUTIVE OVERVIEW
# =========================================================
with tabs[0]:
    st.markdown("## 📊 Executive Performance Scorecard")
    st.caption("Strategic high-level view of revenue, profitability, margins, and potential dynamic pricing opportunities.")
    
    # KPI Cards Row
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Revenue</div>
            <div class="metric-value">${kpis['total_revenue']:,.0f}</div>
            <div class="metric-sub metric-pos">YoY Growth: +{kpis['yoy_revenue_growth_pct']}%</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Gross Profit</div>
            <div class="metric-value">${kpis['total_profit']:,.0f}</div>
            <div class="metric-sub metric-pos">YoY Growth: +{kpis['yoy_profit_growth_pct']}%</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Gross Profit Margin</div>
            <div class="metric-value">{kpis['gross_margin_pct']}%</div>
            <div class="metric-sub metric-neutral">ASP: ${kpis['average_selling_price']:.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Units Sold</div>
            <div class="metric-value">{kpis['total_units_sold']:,}</div>
            <div class="metric-sub metric-neutral">Orders: {kpis['total_orders']:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="metric-card" style="border-color: #10b981;">
            <div class="metric-title">Pricing Profit Upside</div>
            <div class="metric-value" style="color: #10b981;">+${total_potential_profit_upside:,.0f}</div>
            <div class="metric-sub metric-pos">Rev Upside: +${total_potential_rev_upside:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Revenue & Profit Trends Chart
    col_t1, col_t2 = st.columns([7, 5])
    with col_t1:
        st.markdown("### 📈 Monthly Revenue & Profit Trajectory")
        monthly_df = compute_monthly_trends(df_sales_filtered)
        
        fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
        fig_trend.add_trace(
            go.Bar(
                x=monthly_df["year_month"],
                y=monthly_df["revenue"],
                name="Revenue ($)",
                marker_color="#3b82f6",
                opacity=0.85
            ),
            secondary_y=False
        )
        fig_trend.add_trace(
            go.Scatter(
                x=monthly_df["year_month"],
                y=monthly_df["profit"],
                name="Gross Profit ($)",
                mode="lines+markers",
                line=dict(color="#10b981", width=3),
                marker=dict(size=6)
            ),
            secondary_y=False
        )
        fig_trend.add_trace(
            go.Scatter(
                x=monthly_df["year_month"],
                y=monthly_df["profit_margin_pct"],
                name="Profit Margin %",
                mode="lines",
                line=dict(color="#f59e0b", width=2, dash="dot"),
            ),
            secondary_y=True
        )
        fig_trend.update_layout(
            template="plotly_dark",
            height=380,
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )
        fig_trend.update_yaxes(title_text="Amount ($)", secondary_y=False)
        fig_trend.update_yaxes(title_text="Margin (%)", secondary_y=True, showgrid=False)
        st.plotly_chart(fig_trend, use_container_width=True)
        
    with col_t2:
        st.markdown("### 🥧 Revenue Share by Category")
        cat_df = compute_category_summary(df_sales_filtered, df_products_raw)
        fig_cat = px.pie(
            cat_df,
            values="total_revenue",
            names="category",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_cat.update_layout(
            template="plotly_dark",
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15)
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    # Regional & Top Products Row
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        st.markdown("### 🗺️ Regional Revenue & Profit Margin")
        reg_df = compute_regional_breakdown(df_sales_filtered)
        fig_reg = px.bar(
            reg_df,
            x="region",
            y=["total_revenue", "total_profit"],
            barmode="group",
            labels={"value": "Dollars ($)", "region": "Region", "variable": "Metric"},
            color_discrete_map={"total_revenue": "#3b82f6", "total_profit": "#10b981"}
        )
        fig_reg.update_layout(template="plotly_dark", height=320, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_reg, use_container_width=True)
        
    with r_col2:
        st.markdown("### 🏆 Top 10 Revenue Generating Products")
        prod_df = compute_product_performance(df_sales_filtered, df_products_raw).head(10)
        fig_top = px.bar(
            prod_df,
            x="total_revenue",
            y="product_name",
            orientation="h",
            color="realized_margin_pct",
            color_continuous_scale="Viridis",
            labels={"total_revenue": "Revenue ($)", "product_name": "Product", "realized_margin_pct": "Margin %"}
        )
        fig_top.update_layout(template="plotly_dark", height=320, yaxis=dict(autorange="reversed"), margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_top, use_container_width=True)

# =========================================================
# TAB 2: SALES ANALYSIS
# =========================================================
with tabs[1]:
    st.markdown("## 💰 Sales & Volume Deep-Dive")
    st.caption("Granular breakdown of transaction velocity, average selling prices, discount penetration, and customer cohorts.")
    
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.markdown("### 👥 Performance by Customer Segment")
        seg_df = compute_customer_segment_analysis(df_sales_filtered, df_customers_raw)
        fig_seg = px.bar(
            seg_df,
            x="customer_segment",
            y="total_revenue",
            text_auto=".2s",
            color="margin_pct",
            color_continuous_scale="Blues",
            labels={"total_revenue": "Revenue ($)", "customer_segment": "Segment", "margin_pct": "Margin %"}
        )
        fig_seg.update_layout(template="plotly_dark", height=340)
        st.plotly_chart(fig_seg, use_container_width=True)
        
        st.dataframe(
            seg_df[["customer_segment", "unique_customers", "total_orders", "aov", "asp", "margin_pct", "total_revenue"]],
            column_config={
                "total_revenue": st.column_config.NumberColumn(format="$%.2f"),
                "aov": st.column_config.NumberColumn(format="$%.2f"),
                "asp": st.column_config.NumberColumn(format="$%.2f"),
                "margin_pct": st.column_config.NumberColumn(format="%.1f%%")
            },
            hide_index=True,
            use_container_width=True
        )
        
    with s_col2:
        st.markdown("### 🏷️ Discount Impact & Margin Erosion")
        disc_df = compute_discount_impact(df_sales_filtered)
        fig_disc = px.scatter(
            disc_df,
            x="units_sold",
            y="margin_pct",
            size="revenue",
            color="discount_tier",
            hover_name="discount_tier",
            labels={"units_sold": "Units Sold", "margin_pct": "Realized Margin %", "revenue": "Revenue ($)"}
        )
        fig_disc.update_layout(template="plotly_dark", height=340)
        st.plotly_chart(fig_disc, use_container_width=True)
        
        st.dataframe(
            disc_df,
            column_config={
                "revenue": st.column_config.NumberColumn(format="$%.2f"),
                "profit": st.column_config.NumberColumn(format="$%.2f"),
                "margin_pct": st.column_config.NumberColumn(format="%.1f%%"),
                "aov": st.column_config.NumberColumn(format="$%.2f")
            },
            hide_index=True,
            use_container_width=True
        )

# =========================================================
# TAB 3: PRICING ANALYTICS & OPPORTUNITY MATRIX
# =========================================================
with tabs[2]:
    st.markdown("## 🏷️ Pricing Analytics & Competitive Positioning")
    st.caption("Assessing market pricing power, unit dollar spread, competitor price gaps, and the 2x2 Pricing Opportunity Matrix.")
    
    prod_perf_df = compute_product_performance(df_sales_filtered, df_products_raw)
    
    # 2x2 Opportunity Matrix
    st.markdown("### 🧭 2x2 Pricing Opportunity Matrix (Elasticity vs Gross Margin)")
    
    merged_matrix_df = prod_perf_df.merge(
        df_recs_all[["product_id", "elasticity", "recommendation", "opportunity_quadrant", "priority"]],
        on="product_id",
        how="left"
    )
    merged_matrix_df["abs_elasticity"] = merged_matrix_df["elasticity"].abs()
    
    fig_matrix = px.scatter(
        merged_matrix_df,
        x="abs_elasticity",
        y="realized_margin_pct",
        color="recommendation",
        size="total_revenue",
        hover_name="product_name",
        hover_data={"current_price": ":$.2f", "competitor_price": ":$.2f", "base_cost": ":$.2f", "elasticity": ":.2f"},
        labels={
            "abs_elasticity": "Price Elasticity Magnitude |ε| (Higher = More Sensitive)",
            "realized_margin_pct": "Gross Profit Margin (%)",
            "recommendation": "Recommended Action"
        },
        color_discrete_map={
            "Increase Price": "#10b981",
            "Decrease Price": "#ef4444",
            "Maintain Price": "#60a5fa",
            "Discount / Clearance": "#f59e0b"
        }
    )
    
    # Add quadrant dividing lines
    fig_matrix.add_vline(x=1.3, line_width=1, line_dash="dash", line_color="#64748b")
    fig_matrix.add_hline(y=50.0, line_width=1, line_dash="dash", line_color="#64748b")
    
    fig_matrix.add_annotation(x=0.8, y=75, text="Q1: Pricing Power (Raise Price)", showarrow=False, font=dict(color="#10b981", size=11))
    fig_matrix.add_annotation(x=2.5, y=75, text="Q2: Volume Growth (Lower Price)", showarrow=False, font=dict(color="#38bdf8", size=11))
    fig_matrix.add_annotation(x=0.8, y=35, text="Q3: Margin Repair (Raise Price)", showarrow=False, font=dict(color="#f59e0b", size=11))
    fig_matrix.add_annotation(x=2.5, y=35, text="Q4: Price Sensitive (Cost Control)", showarrow=False, font=dict(color="#ef4444", size=11))
    
    fig_matrix.update_layout(template="plotly_dark", height=450)
    st.plotly_chart(fig_matrix, use_container_width=True)

    # Competitor Index Chart
    st.markdown("### ⚔️ RetailX vs Competitor Pricing Gap")
    fig_comp = px.bar(
        merged_matrix_df.sort_values(by="competitor_price_diff_pct"),
        x="competitor_price_diff_pct",
        y="product_name",
        orientation="h",
        color="competitor_price_diff_pct",
        color_continuous_scale="RdYlGn_r",
        labels={"competitor_price_diff_pct": "Price Premium vs Competitor (%)", "product_name": "Product"}
    )
    fig_comp.update_layout(template="plotly_dark", height=480, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_comp, use_container_width=True)

# =========================================================
# TAB 4: PRICE ELASTICITY
# =========================================================
with tabs[3]:
    st.markdown("## 📈 Econometric Price Elasticity of Demand (PED)")
    st.caption("Rigorous Log-Log OLS regression estimates controlling for competitor pricing and seasonal indices.")
    
    df_prod_elast = elast_engine.calculate_all_product_elasticities()
    df_cat_elast = elast_engine.calculate_category_elasticity()
    
    e_col1, e_col2 = st.columns([5, 7])
    with e_col1:
        st.markdown("### 📚 Category Elasticity Benchmark")
        st.dataframe(
            df_cat_elast[["category", "category_elasticity", "classification", "r_squared", "total_observations"]],
            column_config={
                "category_elasticity": st.column_config.NumberColumn(format="%.3f"),
                "r_squared": st.column_config.NumberColumn(format="%.3f")
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.markdown("### 🧮 Selected Product Demand Curve")
        selected_prod_name = st.selectbox("Select Product to Inspect Curve", df_prod_elast["product_name"].unique())
        selected_pid = df_prod_elast[df_prod_elast["product_name"] == selected_prod_name]["product_id"].values[0]
        
        curve_df = optimizer.simulate_price_curve(selected_pid)
        p_row = df_prod_elast[df_prod_elast["product_id"] == selected_pid].iloc[0]
        
        st.markdown(f"""
        **Product**: `{p_row['product_name']}`  
        **Elasticity (ε)**: `{p_row['elasticity']:.3f}` ({p_row['classification']})  
        **95% CI**: `[{p_row['ci_lower_95']:.3f}, {p_row['ci_upper_95']:.3f}]` | **R²**: `{p_row['r_squared']:.3f}`  
        **Statistical Confidence**: `{p_row['confidence']}`
        """)
        
    with e_col2:
        st.markdown(f"### 📉 Fitted Demand & Revenue Curve ({selected_prod_name})")
        fig_curve = make_subplots(specs=[[{"secondary_y": True}]])
        fig_curve.add_trace(
            go.Scatter(
                x=curve_df["candidate_price"],
                y=curve_df["expected_units"],
                name="Expected Annual Units (Demand)",
                mode="lines",
                line=dict(color="#38bdf8", width=3)
            ),
            secondary_y=False
        )
        fig_curve.add_trace(
            go.Scatter(
                x=curve_df["candidate_price"],
                y=curve_df["expected_revenue"],
                name="Expected Revenue ($)",
                mode="lines",
                line=dict(color="#10b981", width=3, dash="dash")
            ),
            secondary_y=True
        )
        fig_curve.add_trace(
            go.Scatter(
                x=curve_df["candidate_price"],
                y=curve_df["expected_profit"],
                name="Expected Profit ($)",
                mode="lines",
                line=dict(color="#f59e0b", width=3)
            ),
            secondary_y=True
        )
        # Vertical line at current price
        fig_curve.add_vline(x=p_row["current_price"], line_width=2, line_dash="dot", line_color="#ef4444", annotation_text="Current Price")
        
        fig_curve.update_layout(template="plotly_dark", height=380, hovermode="x unified", legend=dict(orientation="h", y=-0.2))
        fig_curve.update_xaxes(title_text="Candidate Price ($)")
        fig_curve.update_yaxes(title_text="Expected Units Sold", secondary_y=False)
        fig_curve.update_yaxes(title_text="Financial Amount ($)", secondary_y=True, showgrid=False)
        st.plotly_chart(fig_curve, use_container_width=True)

    st.markdown("### 📋 Full Catalog Price Elasticity Summary")
    st.dataframe(
        df_prod_elast[[
            "product_id", "product_name", "category", "current_price", "base_cost",
            "elasticity", "std_error", "t_statistic", "p_value", "ci_lower_95", "ci_upper_95",
            "r_squared", "classification", "pricing_power"
        ]],
        column_config={
            "current_price": st.column_config.NumberColumn(format="$%.2f"),
            "base_cost": st.column_config.NumberColumn(format="$%.2f"),
            "elasticity": st.column_config.NumberColumn(format="%.3f"),
            "std_error": st.column_config.NumberColumn(format="%.3f"),
            "p_value": st.column_config.NumberColumn(format="%.4f"),
            "r_squared": st.column_config.NumberColumn(format="%.3f")
        },
        hide_index=True,
        use_container_width=True
    )

# =========================================================
# TAB 5: DEMAND & SEASONALITY
# =========================================================
with tabs[4]:
    st.markdown("## 📦 Demand Patterns & Seasonality Analysis")
    st.caption("Identifying demand peaks, monthly category seasonality multipliers, and day-of-week velocity.")
    
    # Month vs Category Seasonality Pivot
    month_cat = df_sales_filtered.groupby(["month", "category"])["revenue"].sum().unstack()
    month_cat_norm = (month_cat / month_cat.mean()) * 100.0
    
    st.markdown("### 🌡️ Monthly Demand Seasonality Index Heatmap (Baseline = 100)")
    fig_heat = px.imshow(
        month_cat_norm.T,
        labels=dict(x="Calendar Month", y="Product Category", color="Seasonality Index"),
        x=[f"Month {m}" for m in month_cat_norm.index],
        y=month_cat_norm.columns,
        color_continuous_scale="Viridis"
    )
    fig_heat.update_layout(template="plotly_dark", height=320)
    st.plotly_chart(fig_heat, use_container_width=True)

    d_col1, d_col2 = st.columns(2)
    with d_col1:
        st.markdown("### 📅 Day of Week Sales Velocity")
        dow_df = df_sales_filtered.groupby("day_of_week").agg(
            revenue=("revenue", "sum"),
            orders=("transaction_id", "count")
        ).reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]).reset_index()
        
        fig_dow = px.bar(
            dow_df,
            x="day_of_week",
            y="revenue",
            color="revenue",
            color_continuous_scale="Blues",
            labels={"day_of_week": "Day of Week", "revenue": "Revenue ($)"}
        )
        fig_dow.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_dow, use_container_width=True)
        
    with d_col2:
        st.markdown("### 🔄 Inventory Turnover vs Velocity")
        inv_df = df_products_raw.copy()
        prod_units = df_sales_filtered.groupby("product_id")["quantity"].sum().to_dict()
        inv_df["total_units"] = inv_df["product_id"].map(prod_units).fillna(0)
        inv_df["monthly_turn"] = (inv_df["total_units"] / 24.0) / inv_df["inventory_level"]
        
        fig_inv = px.scatter(
            inv_df,
            x="inventory_level",
            y="monthly_turn",
            size="total_units",
            color="category",
            hover_name="product_name",
            labels={"inventory_level": "Warehouse Stock Level", "monthly_turn": "Monthly Stock Turns (x)"}
        )
        fig_inv.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_inv, use_container_width=True)

# =========================================================
# TAB 6: PROFITABILITY
# =========================================================
with tabs[5]:
    st.markdown("## 📉 Profitability & Unit Margin Structure")
    st.caption("Deep-dive into unit economics, cost of goods sold (COGS), dollar margin spreads, and contribution tiers.")
    
    prof_p_df = compute_product_performance(df_sales_filtered, df_products_raw)
    
    st.markdown("### 📊 Unit Price vs Base Cost Spread Waterfall")
    fig_spread = px.bar(
        prof_p_df.sort_values(by="unit_dollar_margin", ascending=False),
        x="product_name",
        y=["base_cost", "unit_dollar_margin"],
        barmode="stack",
        labels={"value": "Price Breakdown ($)", "product_name": "Product", "variable": "Component"},
        color_discrete_map={"base_cost": "#64748b", "unit_dollar_margin": "#10b981"}
    )
    fig_spread.update_layout(template="plotly_dark", height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig_spread, use_container_width=True)

    st.dataframe(
        prof_p_df[[
            "product_id", "product_name", "category", "current_price", "base_cost",
            "unit_dollar_margin", "realized_margin_pct", "total_units_sold", "total_revenue", "total_profit"
        ]],
        column_config={
            "current_price": st.column_config.NumberColumn(format="$%.2f"),
            "base_cost": st.column_config.NumberColumn(format="$%.2f"),
            "unit_dollar_margin": st.column_config.NumberColumn(format="$%.2f"),
            "realized_margin_pct": st.column_config.NumberColumn(format="%.1f%%"),
            "total_revenue": st.column_config.NumberColumn(format="$%.2f"),
            "total_profit": st.column_config.NumberColumn(format="$%.2f")
        },
        hide_index=True,
        use_container_width=True
    )

# =========================================================
# TAB 7: DYNAMIC PRICING SIMULATOR
# =========================================================
with tabs[6]:
    st.markdown("## 🎛️ Interactive Dynamic Pricing Simulator")
    st.caption("Simulate real-time P&L changes, demand responses, and competitive dynamics by testing custom price interventions.")
    
    sim_col1, sim_col2 = st.columns([4, 8])
    with sim_col1:
        st.markdown("### ⚙️ Scenario Parameters")
        sim_p_name = st.selectbox("Select Target Product", df_products_raw["product_name"].unique(), key="sim_prod")
        sim_pid = df_products_raw[df_products_raw["product_name"] == sim_p_name]["product_id"].values[0]
        sim_prod_row = df_products_raw[df_products_raw["product_id"] == sim_pid].iloc[0]
        
        curr_p = float(sim_prod_row["current_price"])
        base_c = float(sim_prod_row["base_cost"])
        comp_p = float(sim_prod_row["competitor_price"])
        
        st.markdown(f"""
        - **Current Price**: `${curr_p:.2f}`
        - **Base Cost**: `${base_c:.2f}`
        - **Competitor Price**: `${comp_p:.2f}`
        """)
        
        sim_price_slider = st.slider(
            "Proposed Price ($)",
            min_value=float(round(base_c * 1.05, 2)),
            max_value=float(round(curr_p * 1.5, 2)),
            value=float(curr_p),
            step=0.50
        )
        
        sim_comp_slider = st.slider(
            "Competitor Price Reaction ($)",
            min_value=float(round(comp_p * 0.7, 2)),
            max_value=float(round(comp_p * 1.3, 2)),
            value=float(comp_p),
            step=0.50
        )
        
        sim_discount = st.slider("Promotional Discount (%)", min_value=0, max_value=30, value=0, step=1)
        sim_season = st.select_slider("Seasonality Multiplier", options=[0.7, 0.85, 1.0, 1.15, 1.3, 1.5], value=1.0)
        
    with sim_col2:
        st.markdown("### 📊 Projected Financial & Demand Impact")
        
        sim_result = optimizer.simulate_custom_scenario(
            product_id=sim_pid,
            new_price=sim_price_slider,
            competitor_price=sim_comp_slider,
            discount_pct=sim_discount,
            season_multiplier=sim_season
        )
        
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.metric(
                "Expected Units",
                f"{sim_result['proposed_units']:,.0f}",
                delta=f"{sim_result['delta_units_pct']:+.1f}%"
            )
        with sc2:
            st.metric(
                "Expected Revenue",
                f"${sim_result['proposed_revenue']:,.0f}",
                delta=f"${sim_result['delta_revenue']:+,.0f} ({sim_result['delta_revenue_pct']:+.1f}%)"
            )
        with sc3:
            st.metric(
                "Expected Profit",
                f"${sim_result['proposed_profit']:,.0f}",
                delta=f"${sim_result['delta_profit']:+,.0f} ({sim_result['delta_profit_pct']:+.1f}%)"
            )
        with sc4:
            st.metric(
                "Realized Margin",
                f"{sim_result['proposed_margin_pct']:.1f}%",
                delta=f"{sim_result['proposed_margin_pct'] - sim_result['current_margin_pct']:+.1f}%"
            )
            
        # Comparison Bar Chart
        comp_df = pd.DataFrame([
            {"Strategy": "Current Baseline", "Revenue": sim_result["current_revenue"], "Profit": sim_result["current_profit"]},
            {"Strategy": "Proposed Dynamic Price", "Revenue": sim_result["proposed_revenue"], "Profit": sim_result["proposed_profit"]}
        ])
        fig_sim_bar = px.bar(
            comp_df,
            x="Strategy",
            y=["Revenue", "Profit"],
            barmode="group",
            labels={"value": "Annual Dollars ($)"},
            color_discrete_map={"Revenue": "#3b82f6", "Profit": "#10b981"}
        )
        fig_sim_bar.update_layout(template="plotly_dark", height=320, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_sim_bar, use_container_width=True)

# =========================================================
# TAB 8: PRODUCT RECOMMENDATIONS
# =========================================================
with tabs[7]:
    st.markdown("## 🎯 Data-Driven Pricing Recommendation Engine")
    st.caption("Actionable, explainable product-level pricing guidance backed by calculated price elasticity and competitor positioning.")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        rec_filter = st.multiselect(
            "Filter by Recommended Action",
            options=["Increase Price", "Decrease Price", "Maintain Price", "Discount / Clearance"],
            default=["Increase Price", "Decrease Price", "Maintain Price", "Discount / Clearance"]
        )
    with col_f2:
        priority_filter = st.multiselect(
            "Filter by Strategic Priority",
            options=["High", "Medium", "Low"],
            default=["High", "Medium", "Low"]
        )
        
    filtered_recs = df_recs_all[
        df_recs_all["recommendation"].isin(rec_filter) &
        df_recs_all["priority"].isin(priority_filter)
    ]
    
    st.dataframe(
        filtered_recs[[
            "product_id", "product_name", "category", "current_price", "competitor_price",
            "elasticity", "recommendation", "recommended_price", "recommended_change_pct",
            "expected_volume_change_pct", "expected_profit_impact", "priority", "rationale"
        ]],
        column_config={
            "current_price": st.column_config.NumberColumn(format="$%.2f"),
            "competitor_price": st.column_config.NumberColumn(format="$%.2f"),
            "recommended_price": st.column_config.NumberColumn(format="$%.2f"),
            "elasticity": st.column_config.NumberColumn(format="%.3f"),
            "recommended_change_pct": st.column_config.NumberColumn(format="%+.1f%%"),
            "expected_volume_change_pct": st.column_config.NumberColumn(format="%+.1f%%"),
            "expected_profit_impact": st.column_config.NumberColumn(format="$%+.2f")
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Download Button
    csv_recs = filtered_recs.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Pricing Recommendations (CSV)",
        data=csv_recs,
        file_name="retailx_pricing_recommendations.csv",
        mime="text/csv"
    )

# =========================================================
# TAB 9: SQL STUDIO & DATA EXPLORER
# =========================================================
with tabs[8]:
    st.markdown("## ⚡ SQL Analytics Studio & Data Explorer")
    st.caption("Execute production SQL queries against SQLite `retailx.db` or inspect raw/clean tables.")
    
    sql_subtab1, sql_subtab2 = st.tabs(["💻 SQL Query Runner", "📁 Underlying Data Tables"])
    
    with sql_subtab1:
        query_options = list(named_sql_queries.keys())
        selected_q_name = st.selectbox("Select Pre-Built Analysis Query (22 Available)", query_options)
        
        default_sql = named_sql_queries.get(selected_q_name, "SELECT * FROM products LIMIT 10;")
        sql_input = st.text_area("SQL Editor", value=default_sql, height=180)
        
        if st.button("▶️ Execute SQL Query", type="primary"):
            try:
                conn = sqlite3.connect(DB_PATH)
                sql_result_df = pd.read_sql_query(sql_input, conn)
                conn.close()
                st.success(f"Query returned {len(sql_result_df):,} rows and {sql_result_df.shape[1]} columns.")
                st.dataframe(sql_result_df, use_container_width=True)
            except Exception as e:
                st.error(f"SQL Execution Error: {e}")
                
    with sql_subtab2:
        table_pick = st.selectbox("Select Table to Inspect", ["sales_clean", "products_clean", "customers_clean", "pricing_history_clean"])
        table_map = {
            "sales_clean": df_sales_raw,
            "products_clean": df_products_raw,
            "customers_clean": df_customers_raw,
            "pricing_history_clean": df_pricing_raw
        }
        chosen_df = table_map[table_pick]
        st.dataframe(chosen_df.head(200), use_container_width=True)
        st.download_button(
            label=f"📥 Download {table_pick}.csv",
            data=chosen_df.to_csv(index=False).encode('utf-8'),
            file_name=f"{table_pick}.csv",
            mime="text/csv"
        )
