"""
Automated Unit Tests: Analysis & Aggregation Engine
---------------------------------------------------
Verifies that all analysis and summary functions handle both raw sales
and pre-filtered sales (with existing category/segment columns) without
raising KeyError or introducing colliding suffix columns.
"""

import os
import sys
import pytest
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
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


@pytest.fixture(scope="module")
def data():
    return load_clean_data()


def test_category_summary_raw_sales(data):
    df_cust, df_prod, df_sales, _ = data
    cat_df = compute_category_summary(df_sales, df_prod)
    
    assert not cat_df.empty
    assert "category" in cat_df.columns
    assert "total_revenue" in cat_df.columns
    assert "total_profit" in cat_df.columns
    assert "total_units" in cat_df.columns
    assert len(cat_df) == len(df_prod["category"].unique())


def test_category_summary_filtered_sales_with_existing_category_col(data):
    df_cust, df_prod, df_sales, _ = data
    prod_cat_map = df_prod.set_index("product_id")["category"].to_dict()
    
    # Simulate Streamlit dashboard filtering behavior
    df_filtered = df_sales.copy()
    df_filtered["category"] = df_filtered["product_id"].map(prod_cat_map)
    
    cat_df = compute_category_summary(df_filtered, df_prod)
    assert not cat_df.empty
    assert "category" in cat_df.columns
    assert "category_x" not in cat_df.columns
    assert "category_y" not in cat_df.columns
    assert len(cat_df) == len(df_prod["category"].unique())


def test_customer_segment_analysis_raw_and_filtered(data):
    df_cust, _, df_sales, _ = data
    
    # 1. Raw sales
    seg_raw = compute_customer_segment_analysis(df_sales, df_cust)
    assert "customer_segment" in seg_raw.columns
    assert "total_revenue" in seg_raw.columns
    
    # 2. Filtered sales with existing customer_segment column
    cust_seg_map = df_cust.set_index("customer_id")["customer_segment"].to_dict()
    df_filtered = df_sales.copy()
    df_filtered["customer_segment"] = df_filtered["customer_id"].map(cust_seg_map).fillna("Guest Shoppers")
    
    seg_filt = compute_customer_segment_analysis(df_filtered, df_cust)
    assert "customer_segment" in seg_filt.columns
    assert "customer_segment_x" not in seg_filt.columns
    assert "customer_segment_y" not in seg_filt.columns


def test_regional_breakdown(data):
    _, _, df_sales, _ = data
    reg_df = compute_regional_breakdown(df_sales)
    assert not reg_df.empty
    assert "region" in reg_df.columns
    assert len(reg_df) == df_sales["region"].nunique()


def test_missing_column_validation_raises_keyerror():
    # Pass a dataframe missing required columns to verify informative error
    bad_sales = pd.DataFrame({"some_random_col": [1, 2, 3]})
    bad_prod = pd.DataFrame({"some_other_col": [1, 2, 3]})
    
    with pytest.raises(KeyError) as exc_info:
        compute_category_summary(bad_sales, bad_prod)
    assert "required in df_sales" in str(exc_info.value)
