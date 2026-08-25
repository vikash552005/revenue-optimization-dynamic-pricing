"""
Automated Unit Tests: Data Cleaning & Validation Pipeline
--------------------------------------------------------
Verifies that the ETL pipeline properly handles nulls, duplicates,
invalid values, and enforces strict accounting identities.
"""

import os
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")


@pytest.fixture(scope="module")
def load_datasets():
    df_sales = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "sales_clean.csv"))
    df_prod = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "products_clean.csv"))
    df_cust = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "customers_clean.csv"))
    return df_sales, df_prod, df_cust


def test_sales_no_duplicates(load_datasets):
    df_sales, _, _ = load_datasets
    assert df_sales.duplicated(subset=["transaction_id"]).sum() == 0, "Found duplicate transaction IDs in clean sales!"


def test_sales_no_nulls_in_critical_columns(load_datasets):
    df_sales, _, _ = load_datasets
    critical_cols = ["transaction_id", "date", "product_id", "customer_id", "quantity", "unit_price", "revenue", "profit"]
    for col in critical_cols:
        assert df_sales[col].isna().sum() == 0, f"Found nulls in critical column '{col}'"


def test_sales_accounting_identities(load_datasets):
    df_sales, _, _ = load_datasets
    
    # 1. Effective Price check
    expected_eff = (df_sales["unit_price"] * (1.0 - df_sales["discount"])).round(2)
    eff_diff = (df_sales["effective_price"] - expected_eff).abs().max()
    assert eff_diff < 0.05, f"Effective price mismatch: max diff = {eff_diff}"
    
    # 2. Revenue check
    expected_rev = (df_sales["quantity"] * df_sales["effective_price"]).round(2)
    rev_diff = (df_sales["revenue"] - expected_rev).abs().max()
    assert rev_diff < 0.05, f"Revenue mismatch: max diff = {rev_diff}"
    
    # 3. Profit check
    expected_prof = (df_sales["revenue"] - df_sales["cost"]).round(2)
    prof_diff = (df_sales["profit"] - expected_prof).abs().max()
    assert prof_diff < 0.05, f"Profit mismatch: max diff = {prof_diff}"


def test_sales_positive_values(load_datasets):
    df_sales, _, _ = load_datasets
    assert (df_sales["quantity"] > 0).all(), "Found non-positive quantities in clean sales!"
    assert (df_sales["unit_price"] > 0).all(), "Found non-positive unit prices in clean sales!"
    assert (df_sales["revenue"] > 0).all(), "Found non-positive revenue values in clean sales!"


def test_products_catalog_consistency(load_datasets):
    _, df_prod, _ = load_datasets
    assert len(df_prod) == 20, f"Expected 20 products, found {len(df_prod)}"
    assert (df_prod["base_cost"] > 0).all(), "Base cost must be positive"
    assert (df_prod["current_price"] > df_prod["base_cost"]).all(), "Current price should exceed base cost"
    assert (df_prod["competitor_price"] > 0).all(), "Competitor price must be positive"
