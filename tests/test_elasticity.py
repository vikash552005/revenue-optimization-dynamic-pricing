"""
Automated Unit Tests: Price Elasticity Engine
---------------------------------------------
Verifies that econometric log-log regressions execute accurately,
generate valid statistical confidence intervals, and classify products.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.elasticity import PriceElasticityEngine


@pytest.fixture(scope="module")
def elast_engine():
    return PriceElasticityEngine()


def test_product_elasticity_calculation(elast_engine):
    df_res = elast_engine.calculate_all_product_elasticities()
    assert len(df_res) == 20, f"Expected 20 product results, got {len(df_res)}"
    
    # Elasticity must be negative according to law of demand
    assert (df_res["elasticity"] < 0).all(), "All price elasticities of demand should be negative"
    
    # Standard errors must be positive
    assert (df_res["std_error"] > 0).all(), "Standard errors must be strictly positive"
    
    # Check 95% Confidence Intervals
    assert (df_res["ci_lower_95"] < df_res["elasticity"]).all()
    assert (df_res["ci_upper_95"] > df_res["elasticity"]).all()


def test_elasticity_classification_validity(elast_engine):
    df_res = elast_engine.calculate_all_product_elasticities()
    valid_classes = {"Inelastic", "Elastic", "Highly Sensitive"}
    assert set(df_res["classification"].unique()).issubset(valid_classes)


def test_category_elasticity(elast_engine):
    df_cat = elast_engine.calculate_category_elasticity()
    assert len(df_cat) == 5, f"Expected 5 categories, got {len(df_cat)}"
    assert (df_cat["category_elasticity"] < 0).all()
