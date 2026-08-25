"""
Automated Unit Tests: Pricing Optimizer & Dynamic Simulator
----------------------------------------------------------
Verifies pricing curve simulation, candidate grid bounds, and
financial upside calculations.
"""

import os
import sys
import pytest
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pricing_optimizer import PricingOptimizer


@pytest.fixture(scope="module")
def optimizer():
    return PricingOptimizer()


def test_price_curve_simulation(optimizer):
    curve_df = optimizer.simulate_price_curve("PRD-E01")
    assert not curve_df.empty, "Simulated price curve is empty!"
    assert "candidate_price" in curve_df.columns
    assert "expected_revenue" in curve_df.columns
    assert "expected_profit" in curve_df.columns
    
    # Check that demand decreases as candidate price increases
    units = curve_df["expected_units"].values
    assert units[0] > units[-1], "Demand should be higher at the lowest price than at the highest price!"


def test_optimize_all_products(optimizer):
    df_opt = optimizer.optimize_all_products()
    assert len(df_opt) == 20
    
    # Profit upside must be non-negative
    assert (df_opt["profit_max_profit_upside"] >= 0).all()
    
    # Optimal prices must be above base cost
    assert (df_opt["profit_max_price"] > df_opt["base_cost"]).all()


def test_custom_scenario_simulation(optimizer):
    res = optimizer.simulate_custom_scenario(
        product_id="PRD-E01",
        new_price=160.0,
        competitor_price=150.0,
        discount_pct=5.0
    )
    assert res["product_id"] == "PRD-E01"
    assert res["proposed_units"] > 0
    assert res["proposed_revenue"] > 0
    assert "delta_profit" in res
