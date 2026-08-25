"""
Script to generate reproducible, clean Jupyter Notebooks (.ipynb)
for the RetailX portfolio project.
"""

import os
import json

NOTEBOOKS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "notebooks"))
os.makedirs(NOTEBOOKS_DIR, exist_ok=True)


def make_notebook(cells):
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.11.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }


def md_cell(source):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in source.split("\n")]
    }


def code_cell(source):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in source.split("\n")]
    }


# ---------------------------------------------------------
# 1. 01_data_cleaning.ipynb
# ---------------------------------------------------------
nb1_cells = [
    md_cell("""# RetailX Portfolio Project: Data Cleaning & ETL Pipeline
### Module 01: Raw Data Ingestion, Audit, Cleaning, and Validation

**Objective**: Ingest dirty raw transactional and catalog data, identify anomalies (duplicates, missing values, extreme outliers, invalid transactions), execute systematic remediation rules, and export standardized datasets to SQLite and CSV.
"""),
    code_cell("""import os
import sys
import json
import sqlite3
import pandas as pd
import numpy as np

# Set project paths
PROJECT_ROOT = os.path.abspath("..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.data_cleaning import run_pipeline

print("Environment initialized successfully.")
"""),
    md_cell("""## 1. Raw Data Audit
Let's inspect the raw datasets before cleaning to examine injected real-world imperfections.
"""),
    code_cell("""raw_sales = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "raw", "sales.csv"))
raw_cust = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "raw", "customers.csv"))
raw_prod = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "raw", "products.csv"))

print(f"Raw Sales Shape: {raw_sales.shape}")
print(f"Duplicate Transactions: {raw_sales.duplicated(subset=['transaction_id']).sum()}")
print(f"Missing Customer IDs: {raw_sales['customer_id'].isna().sum()}")
print(f"Missing Discounts: {raw_sales['discount'].isna().sum()}")
print(f"Negative Quantities: {(raw_sales['quantity'] <= 0).sum()}")
print(f"Negative Prices: {(raw_sales['unit_price'] <= 0).sum()}")
"""),
    md_cell("""## 2. Execute Data Cleaning Pipeline
We run the production ETL pipeline from `src/data_cleaning.py`.
"""),
    code_cell("""audit_log = run_pipeline()
print(json.dumps(audit_log, indent=2))
"""),
    md_cell("""## 3. Verify Cleaned Data & Accounting Identities
We confirm that all accounting identities hold true:
- $\\text{Revenue} = \\text{Quantity} \\times \\text{Unit Price} \\times (1 - \\text{Discount})$
- $\\text{Profit} = \\text{Revenue} - (\\text{Quantity} \\times \\text{Base Cost})$
"""),
    code_cell("""clean_sales = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "processed", "sales_clean.csv"))
clean_products = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "processed", "products_clean.csv"))

# Verify zero nulls in critical fields
print("Null count check:")
print(clean_sales[["transaction_id", "date", "quantity", "unit_price", "revenue", "profit"]].isna().sum())

# Verify mathematical accuracy
expected_rev = (clean_sales["quantity"] * clean_sales["unit_price"] * (1 - clean_sales["discount"])).round(2)
diff = (clean_sales["revenue"] - expected_rev).abs().max()
print(f"Max Accounting Discrepancy: ${diff:.4f}")
assert diff < 0.05, "Accounting identity violated!"
print("Accounting verification: PASSED")
""")
]

# ---------------------------------------------------------
# 2. 02_eda.ipynb
# ---------------------------------------------------------
nb2_cells = [
    md_cell("""# RetailX Portfolio Project: Exploratory Data Analysis (EDA)
### Module 02: Business KPIs, Trends, Customer Segments, and Performance Analysis

**Objective**: Uncover key performance drivers, regional growth trends, category margin contributions, customer purchase frequency, and discount impact on profitability.
"""),
    code_cell("""import os
import sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

PROJECT_ROOT = os.path.abspath("..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.analysis import (
    load_clean_data,
    compute_executive_kpis,
    compute_monthly_trends,
    compute_category_summary,
    compute_regional_breakdown,
    compute_customer_segment_analysis,
    compute_product_performance,
    compute_discount_impact
)

df_cust, df_prod, df_sales, df_pricing = load_clean_data()
print(f"Loaded {len(df_sales):,} clean transactions.")
"""),
    md_cell("""## 1. Executive Performance Scorecard
Calculate overall business metrics.
"""),
    code_cell("""kpis = compute_executive_kpis(df_sales)
for k, v in kpis.items():
    print(f"{k.replace('_', ' ').title()}: {v}")
"""),
    md_cell("""## 2. Monthly Revenue and Gross Profit Trajectory
Analyze seasonality and growth over the 24-month period.
"""),
    code_cell("""monthly_df = compute_monthly_trends(df_sales)

fig = go.Figure()
fig.add_trace(go.Bar(x=monthly_df["year_month"], y=monthly_df["revenue"], name="Revenue ($)", marker_color="#3b82f6"))
fig.add_trace(go.Scatter(x=monthly_df["year_month"], y=monthly_df["profit"], name="Gross Profit ($)", line=dict(color="#10b981", width=3)))
fig.update_layout(title="Monthly Revenue and Gross Profit", template="plotly_dark", height=400)
fig.show()
"""),
    md_cell("""## 3. Product Category Breakdown
Evaluate category revenue share, margin percentages, and average selling price.
"""),
    code_cell("""cat_df = compute_category_summary(df_sales, df_prod)
display(cat_df)

fig_pie = px.pie(cat_df, values="total_revenue", names="category", title="Revenue Share by Category", hole=0.4)
fig_pie.update_layout(template="plotly_dark")
fig_pie.show()
"""),
    md_cell("""## 4. Customer Segment Purchasing Behaviors
Compare spending, order sizes, and discount sensitivity across customer cohorts.
"""),
    code_cell("""seg_df = compute_customer_segment_analysis(df_sales, df_cust)
display(seg_df)

fig_seg = px.bar(seg_df, x="customer_segment", y="total_revenue", color="margin_pct", title="Revenue & Margin by Customer Segment")
fig_seg.update_layout(template="plotly_dark")
fig_seg.show()
""")
]

# ---------------------------------------------------------
# 3. 03_price_elasticity.ipynb
# ---------------------------------------------------------
nb3_cells = [
    md_cell("""# RetailX Portfolio Project: Econometric Price Elasticity of Demand
### Module 03: Log-Log OLS Regression, Confidence Intervals, and Classification

**Objective**: Estimate empirical price elasticities of demand (PED) using econometric regression models:
$$\\ln(Q_t) = \\beta_0 + \\beta_1 \\ln(P_t) + \\beta_2 \\ln(P_{\\text{comp}, t}) + \\beta_3 \\text{Month}_t + \\epsilon_t$$
where $\\beta_1$ represents the Price Elasticity of Demand (PED).
"""),
    code_cell("""import os
import sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

PROJECT_ROOT = os.path.abspath("..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.elasticity import PriceElasticityEngine

engine = PriceElasticityEngine()
df_prod_elast = engine.calculate_all_product_elasticities()
df_cat_elast = engine.calculate_category_elasticity()
print("Price Elasticity Engine initialized.")
"""),
    md_cell("""## 1. Product-Level Price Elasticity Results
Examine elasticity coefficients, standard errors, $t$-statistics, $p$-values, and 95% Confidence Intervals.
"""),
    code_cell("""display(df_prod_elast[[
    "product_id", "product_name", "category", "current_price", "base_cost",
    "elasticity", "std_error", "t_statistic", "p_value", "ci_lower_95", "ci_upper_95",
    "r_squared", "classification", "confidence"
]])
"""),
    md_cell("""## 2. Category-Level Elasticity Benchmarks
Compare macro elasticity tiers across the 5 product categories.
"""),
    code_cell("""display(df_cat_elast)

fig_cat_e = px.bar(
    df_cat_elast,
    x="category",
    y="category_elasticity",
    color="classification",
    title="Price Elasticity by Product Category",
    labels={"category_elasticity": "Elasticity Coefficient (ε)"}
)
fig_cat_e.update_layout(template="plotly_dark")
fig_cat_e.show()
"""),
    md_cell("""## 3. Visualizing 95% Confidence Intervals
Inspect statistical certainty across all 20 catalog products.
"""),
    code_cell("""fig_ci = go.Figure()
fig_ci.add_trace(go.Scatter(
    x=df_prod_elast["elasticity"],
    y=df_prod_elast["product_name"],
    mode="markers",
    error_x=dict(
        type="data",
        symmetric=False,
        array=df_prod_elast["ci_upper_95"] - df_prod_elast["elasticity"],
        arrayminus=df_prod_elast["elasticity"] - df_prod_elast["ci_lower_95"]
    ),
    marker=dict(size=8, color="#38bdf8")
))
fig_ci.add_vline(x=-1.0, line_dash="dash", line_color="#ef4444", annotation_text="Unit Elasticity (ε = -1.0)")
fig_ci.update_layout(title="Product Price Elasticities with 95% Confidence Intervals", template="plotly_dark", height=600)
fig_ci.show()
""")
]

# ---------------------------------------------------------
# 4. 04_pricing_optimization.ipynb
# ---------------------------------------------------------
nb4_cells = [
    md_cell("""# RetailX Portfolio Project: Pricing Optimization & Recommendations
### Module 04: Revenue vs Profit Maximization, Scenario Simulator, and Recommendation Engine

**Objective**: Model candidate price curves ($\pm 25\%$), identify revenue-maximizing vs profit-maximizing price points, quantify financial upside, and generate business recommendations.
"""),
    code_cell("""import os
import sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PROJECT_ROOT = os.path.abspath("..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pricing_optimizer import PricingOptimizer
from src.recommendations import PricingRecommendationEngine

optimizer = PricingOptimizer()
rec_engine = PricingRecommendationEngine()
print("Pricing Optimization Engines initialized.")
"""),
    md_cell("""## 1. Candidate Price Curve Simulation
Evaluate candidate prices around current baseline for a selected product.
"""),
    code_cell("""pid = "PRD-E01"
curve_df = optimizer.simulate_price_curve(pid)

fig_opt = make_subplots(specs=[[{"secondary_y": True}]])
fig_opt.add_trace(go.Scatter(x=curve_df["candidate_price"], y=curve_df["expected_units"], name="Demand (Units)", line=dict(color="#38bdf8")), secondary_y=False)
fig_opt.add_trace(go.Scatter(x=curve_df["candidate_price"], y=curve_df["expected_revenue"], name="Revenue ($)", line=dict(color="#10b981", dash="dash")), secondary_y=True)
fig_opt.add_trace(go.Scatter(x=curve_df["candidate_price"], y=curve_df["expected_profit"], name="Profit ($)", line=dict(color="#f59e0b")), secondary_y=True)
fig_opt.update_layout(title=f"Pricing Optimization Curve for {curve_df['product_name'].iloc[0]}", template="plotly_dark", height=400)
fig_opt.show()
"""),
    md_cell("""## 2. Catalog-Wide Optimization & Financial Upside
Calculate revenue-maximizing and profit-maximizing targets for all 20 products.
"""),
    code_cell("""df_opt = optimizer.optimize_all_products()

total_rev_upside = df_opt["rev_max_revenue_upside"].sum()
total_prof_upside = df_opt["profit_max_profit_upside"].sum()
print(f"Total Potential Revenue Upside: +${total_rev_upside:,.2f}")
print(f"Total Potential Profit Upside:  +${total_prof_upside:,.2f}")

display(df_opt[["product_name", "current_price", "rev_max_price", "rev_max_revenue_upside", "profit_max_price", "profit_max_profit_upside"]].head(10))
"""),
    md_cell("""## 3. Strategic Pricing Recommendations
Generate explainable pricing recommendations with business rationale and 2x2 opportunity matrix.
"""),
    code_cell("""df_recs = rec_engine.generate_product_recommendations()

display(df_recs[[
    "product_name", "category", "current_price", "competitor_price",
    "recommendation", "recommended_price", "expected_profit_impact", "priority", "rationale"
]])
""")
]

# Write all notebooks
with open(os.path.join(NOTEBOOKS_DIR, "01_data_cleaning.ipynb"), "w") as f:
    json.dump(make_notebook(nb1_cells), f, indent=2)

with open(os.path.join(NOTEBOOKS_DIR, "02_eda.ipynb"), "w") as f:
    json.dump(make_notebook(nb2_cells), f, indent=2)

with open(os.path.join(NOTEBOOKS_DIR, "03_price_elasticity.ipynb"), "w") as f:
    json.dump(make_notebook(nb3_cells), f, indent=2)

with open(os.path.join(NOTEBOOKS_DIR, "04_pricing_optimization.ipynb"), "w") as f:
    json.dump(make_notebook(nb4_cells), f, indent=2)

print("Successfully generated all 4 Jupyter Notebooks in 'notebooks/'")
