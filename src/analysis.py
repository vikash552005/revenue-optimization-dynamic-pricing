"""
RetailX Business Analysis & EDA Engine
-------------------------------------
Provides standardized analytical data aggregations, business KPIs,
cohort metrics, and executive summaries from clean transaction data.
"""

import os
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")


def load_clean_data():
    """Load all cleaned datasets from processed directory."""
    df_customers = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "customers_clean.csv"))
    df_products = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "products_clean.csv"))
    df_sales = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "sales_clean.csv"))
    df_pricing = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "pricing_history_clean.csv"))
    return df_customers, df_products, df_sales, df_pricing


def compute_executive_kpis(df_sales: pd.DataFrame) -> dict:
    """Calculate executive-level scorecard metrics."""
    total_revenue = float(df_sales["revenue"].sum())
    total_profit = float(df_sales["profit"].sum())
    total_units = int(df_sales["quantity"].sum())
    total_orders = int(len(df_sales))
    active_customers = int(df_sales["customer_id"].nunique())
    
    margin_pct = (total_profit / total_revenue) * 100.0 if total_revenue > 0 else 0.0
    asp = total_revenue / total_units if total_units > 0 else 0.0
    aov = total_revenue / total_orders if total_orders > 0 else 0.0
    
    # Calculate Year-over-Year (YoY) or 2024 vs 2025 growth
    rev_2024 = float(df_sales[df_sales["year"] == 2024]["revenue"].sum())
    rev_2025 = float(df_sales[df_sales["year"] == 2025]["revenue"].sum())
    yoy_growth = ((rev_2025 - rev_2024) / rev_2024) * 100.0 if rev_2024 > 0 else 0.0
    
    prof_2024 = float(df_sales[df_sales["year"] == 2024]["profit"].sum())
    prof_2025 = float(df_sales[df_sales["year"] == 2025]["profit"].sum())
    yoy_profit_growth = ((prof_2025 - prof_2024) / prof_2024) * 100.0 if prof_2024 > 0 else 0.0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_profit": round(total_profit, 2),
        "gross_margin_pct": round(margin_pct, 2),
        "total_units_sold": total_units,
        "total_orders": total_orders,
        "active_customers": active_customers,
        "average_selling_price": round(asp, 2),
        "average_order_value": round(aov, 2),
        "revenue_2024": round(rev_2024, 2),
        "revenue_2025": round(rev_2025, 2),
        "yoy_revenue_growth_pct": round(yoy_growth, 2),
        "yoy_profit_growth_pct": round(yoy_profit_growth, 2)
    }


def compute_monthly_trends(df_sales: pd.DataFrame) -> pd.DataFrame:
    """Aggregate monthly performance with MoM growth rates."""
    monthly = df_sales.groupby("year_month").agg(
        total_orders=("transaction_id", "count"),
        total_units=("quantity", "sum"),
        revenue=("revenue", "sum"),
        cost=("cost", "sum"),
        profit=("profit", "sum")
    ).reset_index()
    
    monthly["profit_margin_pct"] = ((monthly["profit"] / monthly["revenue"]) * 100.0).round(2)
    monthly["asp"] = (monthly["revenue"] / monthly["total_units"]).round(2)
    monthly["prev_revenue"] = monthly["revenue"].shift(1)
    monthly["mom_revenue_growth_pct"] = (((monthly["revenue"] - monthly["prev_revenue"]) / monthly["prev_revenue"]) * 100.0).round(2)
    monthly["prev_profit"] = monthly["profit"].shift(1)
    monthly["mom_profit_growth_pct"] = (((monthly["profit"] - monthly["prev_profit"]) / monthly["prev_profit"]) * 100.0).round(2)
    
    return monthly.fillna(0.0)


def compute_category_summary(df_sales: pd.DataFrame, df_products: pd.DataFrame) -> pd.DataFrame:
    """Aggregate category-level sales, margins, and contribution shares."""
    # Ensure category is available without introducing colliding suffix columns
    if "category" in df_sales.columns:
        merged = df_sales.copy()
    else:
        if "product_id" not in df_sales.columns:
            raise KeyError(f"'product_id' is required in df_sales to resolve category. Available columns: {list(df_sales.columns)}")
        if "product_id" not in df_products.columns or "category" not in df_products.columns:
            raise KeyError(f"df_products must contain 'product_id' and 'category'. Available columns: {list(df_products.columns)}")
        merged = df_sales.merge(df_products[["product_id", "category"]], on="product_id", how="left")

    # Data Validation
    required_cols = ["category", "transaction_id", "quantity", "revenue", "cost", "profit"]
    missing_cols = [c for c in required_cols if c not in merged.columns]
    if missing_cols:
        raise KeyError(f"Missing required column(s) {missing_cols} for category summary. Available columns: {list(merged.columns)}")

    if merged.empty:
        return pd.DataFrame(columns=[
            "category", "total_orders", "total_units", "total_revenue",
            "total_cost", "total_profit", "profit_margin_pct", "asp",
            "revenue_share_pct", "profit_share_pct"
        ])

    cat_df = merged.groupby("category").agg(
        total_orders=("transaction_id", "count"),
        total_units=("quantity", "sum"),
        total_revenue=("revenue", "sum"),
        total_cost=("cost", "sum"),
        total_profit=("profit", "sum")
    ).reset_index()

    grand_rev = cat_df["total_revenue"].sum()
    grand_prof = cat_df["total_profit"].sum()

    cat_df["profit_margin_pct"] = np.where(cat_df["total_revenue"] > 0, ((cat_df["total_profit"] / cat_df["total_revenue"]) * 100.0).round(2), 0.0)
    cat_df["asp"] = np.where(cat_df["total_units"] > 0, (cat_df["total_revenue"] / cat_df["total_units"]).round(2), 0.0)
    cat_df["revenue_share_pct"] = np.where(grand_rev > 0, ((cat_df["total_revenue"] / grand_rev) * 100.0).round(2), 0.0)
    cat_df["profit_share_pct"] = np.where(grand_prof > 0, ((cat_df["total_profit"] / grand_prof) * 100.0).round(2), 0.0)

    return cat_df.sort_values(by="total_revenue", ascending=False)


def compute_regional_breakdown(df_sales: pd.DataFrame) -> pd.DataFrame:
    """Aggregate regional sales and profit margin metrics."""
    if "region" not in df_sales.columns:
        raise KeyError(f"'region' column is required in df_sales. Available columns: {list(df_sales.columns)}")

    required_cols = ["region", "transaction_id", "quantity", "revenue", "profit"]
    missing_cols = [c for c in required_cols if c not in df_sales.columns]
    if missing_cols:
        raise KeyError(f"Missing required column(s) {missing_cols} for regional breakdown. Available columns: {list(df_sales.columns)}")

    if df_sales.empty:
        return pd.DataFrame(columns=[
            "region", "total_orders", "total_units", "total_revenue",
            "total_profit", "profit_margin_pct", "asp", "revenue_share_pct"
        ])

    reg_df = df_sales.groupby("region").agg(
        total_orders=("transaction_id", "count"),
        total_units=("quantity", "sum"),
        total_revenue=("revenue", "sum"),
        total_profit=("profit", "sum")
    ).reset_index()

    grand_rev = reg_df["total_revenue"].sum()
    reg_df["profit_margin_pct"] = np.where(reg_df["total_revenue"] > 0, ((reg_df["total_profit"] / reg_df["total_revenue"]) * 100.0).round(2), 0.0)
    reg_df["asp"] = np.where(reg_df["total_units"] > 0, (reg_df["total_revenue"] / reg_df["total_units"]).round(2), 0.0)
    reg_df["revenue_share_pct"] = np.where(grand_rev > 0, ((reg_df["total_revenue"] / grand_rev) * 100.0).round(2), 0.0)

    return reg_df.sort_values(by="total_revenue", ascending=False)


def compute_customer_segment_analysis(df_sales: pd.DataFrame, df_customers: pd.DataFrame) -> pd.DataFrame:
    """Analyze purchasing behavior and profitability by customer segment."""
    # Ensure customer_segment is available without introducing colliding suffix columns
    if "customer_segment" in df_sales.columns:
        merged = df_sales.copy()
    else:
        if "customer_id" not in df_sales.columns:
            raise KeyError(f"'customer_id' is required in df_sales to resolve customer segment. Available columns: {list(df_sales.columns)}")
        if "customer_id" not in df_customers.columns or "customer_segment" not in df_customers.columns:
            raise KeyError(f"df_customers must contain 'customer_id' and 'customer_segment'. Available columns: {list(df_customers.columns)}")
        merged = df_sales.merge(df_customers[["customer_id", "customer_segment"]], on="customer_id", how="left")

    merged["customer_segment"] = merged["customer_segment"].fillna("Guest Shoppers")

    # Data Validation
    required_cols = ["customer_segment", "customer_id", "transaction_id", "quantity", "revenue", "profit", "discount"]
    missing_cols = [c for c in required_cols if c not in merged.columns]
    if missing_cols:
        raise KeyError(f"Missing required column(s) {missing_cols} for customer segment analysis. Available columns: {list(merged.columns)}")

    if merged.empty:
        return pd.DataFrame(columns=[
            "customer_segment", "unique_customers", "total_orders", "total_units",
            "total_revenue", "total_profit", "avg_discount_pct", "aov", "asp",
            "margin_pct", "units_per_order"
        ])

    seg_df = merged.groupby("customer_segment").agg(
        unique_customers=("customer_id", "nunique"),
        total_orders=("transaction_id", "count"),
        total_units=("quantity", "sum"),
        total_revenue=("revenue", "sum"),
        total_profit=("profit", "sum"),
        avg_discount_pct=("discount", lambda x: round(x.mean() * 100.0, 2))
    ).reset_index()

    seg_df["aov"] = np.where(seg_df["total_orders"] > 0, (seg_df["total_revenue"] / seg_df["total_orders"]).round(2), 0.0)
    seg_df["asp"] = np.where(seg_df["total_units"] > 0, (seg_df["total_revenue"] / seg_df["total_units"]).round(2), 0.0)
    seg_df["margin_pct"] = np.where(seg_df["total_revenue"] > 0, ((seg_df["total_profit"] / seg_df["total_revenue"]) * 100.0).round(2), 0.0)
    seg_df["units_per_order"] = np.where(seg_df["total_orders"] > 0, (seg_df["total_units"] / seg_df["total_orders"]).round(2), 0.0)

    return seg_df.sort_values(by="total_revenue", ascending=False)


def compute_product_performance(df_sales: pd.DataFrame, df_products: pd.DataFrame) -> pd.DataFrame:
    """Comprehensive product performance ledger with unit economics."""
    prod_sales = df_sales.groupby("product_id").agg(
        total_orders=("transaction_id", "count"),
        total_units_sold=("quantity", "sum"),
        total_revenue=("revenue", "sum"),
        total_cost=("cost", "sum"),
        total_profit=("profit", "sum"),
        avg_realized_price=("effective_price", "mean"),
        avg_discount_pct=("discount", lambda x: round(x.mean() * 100.0, 2))
    ).reset_index()
    
    merged = prod_sales.merge(df_products, on="product_id", how="left")
    
    merged["realized_margin_pct"] = ((merged["total_profit"] / merged["total_revenue"]) * 100.0).round(2)
    merged["unit_dollar_margin"] = (merged["avg_realized_price"] - merged["base_cost"]).round(2)
    merged["competitor_price_diff_pct"] = (((merged["current_price"] - merged["competitor_price"]) / merged["competitor_price"]) * 100.0).round(2)
    
    cols = [
        "product_id", "product_name", "category", "subcategory",
        "current_price", "competitor_price", "base_cost", "avg_realized_price",
        "unit_dollar_margin", "realized_margin_pct", "total_units_sold",
        "total_revenue", "total_profit", "avg_discount_pct",
        "competitor_price_diff_pct", "inventory_level"
    ]
    
    return merged[cols].sort_values(by="total_revenue", ascending=False)


def compute_discount_impact(df_sales: pd.DataFrame) -> pd.DataFrame:
    """Evaluate margin erosion and volume elasticities across discount bands."""
    def get_tier(d):
        if d == 0.0:
            return "0% Full Price"
        elif d <= 0.05:
            return "1% - 5%"
        elif d <= 0.10:
            return "6% - 10%"
        elif d <= 0.15:
            return "11% - 15%"
        else:
            return "16% - 20%"
            
    df_copy = df_sales.copy()
    df_copy["discount_tier"] = df_copy["discount"].apply(get_tier)
    
    tier_df = df_copy.groupby("discount_tier").agg(
        order_count=("transaction_id", "count"),
        units_sold=("quantity", "sum"),
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        avg_realized_price=("effective_price", "mean")
    ).reset_index()
    
    tier_df["margin_pct"] = ((tier_df["profit"] / tier_df["revenue"]) * 100.0).round(2)
    tier_df["aov"] = (tier_df["revenue"] / tier_df["order_count"]).round(2)
    
    return tier_df.sort_values(by="revenue", ascending=False)
