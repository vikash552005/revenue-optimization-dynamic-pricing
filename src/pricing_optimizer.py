"""
RetailX Pricing Optimizer & Demand Simulation Engine
---------------------------------------------------
Calculates optimal revenue-maximizing and profit-maximizing prices
for each product using econometric demand curves:
    Q(P) = Q_0 * (P / P_0)^epsilon * (P_comp / P)^cross_elasticity

Features:
- Candidate price grid search (+/-25% in 1% steps)
- Revenue-maximizing vs Profit-maximizing price points
- Annualized financial opportunity calculations
- Interactive scenario simulator function for dashboard
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
from src.elasticity import PriceElasticityEngine


class PricingOptimizer:
    def __init__(self, elasticity_engine: Optional[PriceElasticityEngine] = None):
        if elasticity_engine is None:
            self.elast_engine = PriceElasticityEngine()
        else:
            self.elast_engine = elasticity_engine
            
        self.df_products = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "products_clean.csv"))
        self.df_sales = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "sales_clean.csv"))
        self.elasticities_df = self.elast_engine.calculate_all_product_elasticities()
        self.elasticity_map = self.elasticities_df.set_index("product_id").to_dict(orient="index")

    def simulate_price_curve(self, product_id: str, price_range_pct: float = 0.25, step_pct: float = 0.01) -> pd.DataFrame:
        """
        Generate candidate price curve evaluating expected demand,
        revenue, profit, and margin across candidate price points.
        """
        if product_id not in self.elasticity_map:
            return pd.DataFrame()
            
        e_info = self.elasticity_map[product_id]
        p_base = e_info["current_price"]
        c_base = e_info["base_cost"]
        comp_price = e_info["competitor_price"]
        epsilon = e_info["elasticity"]
        cross_elast = e_info.get("cross_price_elasticity", 0.3)
        
        # Calculate baseline annual volume
        p_sales = self.df_sales[self.df_sales["product_id"] == product_id]
        annual_volume_base = float(p_sales["quantity"].sum() / 2.0)  # 24mo dataset -> 12mo base
        if annual_volume_base <= 0:
            annual_volume_base = e_info["avg_daily_demand"] * 365.0
            
        multipliers = np.arange(1.0 - price_range_pct, 1.0 + price_range_pct + (step_pct / 2.0), step_pct)
        
        curve_records = []
        for mult in multipliers:
            cand_price = round(p_base * mult, 2)
            if cand_price <= c_base:
                continue
                
            price_ratio = cand_price / p_base
            comp_ratio = comp_price / cand_price
            
            # Demand elasticity adjustment
            demand_multiplier = (price_ratio ** epsilon) * (comp_ratio ** cross_elast)
            expected_annual_units = round(annual_volume_base * demand_multiplier, 1)
            
            expected_revenue = round(expected_annual_units * cand_price, 2)
            expected_cost = round(expected_annual_units * c_base, 2)
            expected_profit = round(expected_revenue - expected_cost, 2)
            margin_pct = round(((cand_price - c_base) / cand_price) * 100.0, 2)
            
            curve_records.append({
                "product_id": product_id,
                "product_name": e_info["product_name"],
                "candidate_price": cand_price,
                "price_change_pct": round((mult - 1.0) * 100.0, 1),
                "expected_units": expected_annual_units,
                "expected_revenue": expected_revenue,
                "expected_cost": expected_cost,
                "expected_profit": expected_profit,
                "margin_pct": margin_pct,
                "unit_profit": round(cand_price - c_base, 2)
            })
            
        return pd.DataFrame(curve_records)

    def optimize_product_pricing(self, product_id: str) -> Dict:
        """
        Compute optimal revenue-maximizing and profit-maximizing prices
        and financial upside for a single product.
        """
        curve_df = self.simulate_price_curve(product_id)
        if curve_df.empty:
            return {}
            
        e_info = self.elasticity_map[product_id]
        p_current = e_info["current_price"]
        c_base = e_info["base_cost"]
        
        # Current baseline row (closest to current price)
        current_row = curve_df.iloc[(curve_df["candidate_price"] - p_current).abs().argsort()[:1]].iloc[0]
        
        # Optimal Revenue row
        rev_max_row = curve_df.loc[curve_df["expected_revenue"].idxmax()]
        
        # Optimal Profit row
        prof_max_row = curve_df.loc[curve_df["expected_profit"].idxmax()]
        
        # Revenue Opportunity & Profit Opportunity
        rev_delta = rev_max_row["expected_revenue"] - current_row["expected_revenue"]
        prof_delta = prof_max_row["expected_profit"] - current_row["expected_profit"]
        
        return {
            "product_id": product_id,
            "product_name": e_info["product_name"],
            "category": e_info["category"],
            "elasticity": e_info["elasticity"],
            "classification": e_info["classification"],
            "base_cost": c_base,
            "current_price": p_current,
            "competitor_price": e_info["competitor_price"],
            "current_annual_units": current_row["expected_units"],
            "current_annual_revenue": current_row["expected_revenue"],
            "current_annual_profit": current_row["expected_profit"],
            "current_margin_pct": current_row["margin_pct"],
            
            # Revenue-Maximizing Target
            "rev_max_price": rev_max_row["candidate_price"],
            "rev_max_price_change_pct": rev_max_row["price_change_pct"],
            "rev_max_expected_units": rev_max_row["expected_units"],
            "rev_max_expected_revenue": rev_max_row["expected_revenue"],
            "rev_max_revenue_upside": round(rev_delta, 2),
            "rev_max_revenue_upside_pct": round((rev_delta / current_row["expected_revenue"]) * 100.0, 2) if current_row["expected_revenue"] > 0 else 0.0,
            
            # Profit-Maximizing Target
            "profit_max_price": prof_max_row["candidate_price"],
            "profit_max_price_change_pct": prof_max_row["price_change_pct"],
            "profit_max_expected_units": prof_max_row["expected_units"],
            "profit_max_expected_revenue": prof_max_row["expected_revenue"],
            "profit_max_expected_profit": prof_max_row["expected_profit"],
            "profit_max_margin_pct": prof_max_row["margin_pct"],
            "profit_max_profit_upside": round(prof_delta, 2),
            "profit_max_profit_upside_pct": round((prof_delta / current_row["expected_profit"]) * 100.0, 2) if current_row["expected_profit"] > 0 else 0.0
        }

    def optimize_all_products(self) -> pd.DataFrame:
        """Compute optimal pricing for all catalog products."""
        results = []
        for pid in self.df_products["product_id"].unique():
            res = self.optimize_product_pricing(pid)
            if res:
                results.append(res)
        return pd.DataFrame(results)

    def simulate_custom_scenario(
        self,
        product_id: str,
        new_price: float,
        competitor_price: Optional[float] = None,
        discount_pct: float = 0.0,
        season_multiplier: float = 1.0,
        regional_multiplier: float = 1.0
    ) -> Dict:
        """
        Interactive Simulator: Simulates the financial and demand impact
        of a custom price change against current baseline.
        """
        if product_id not in self.elasticity_map:
            return {}
            
        e_info = self.elasticity_map[product_id]
        p_current = e_info["current_price"]
        c_base = e_info["base_cost"]
        comp_base = competitor_price if competitor_price is not None else e_info["competitor_price"]
        epsilon = e_info["elasticity"]
        cross_elast = e_info.get("cross_price_elasticity", 0.3)
        
        # Base annual units
        p_sales = self.df_sales[self.df_sales["product_id"] == product_id]
        base_annual_units = float(p_sales["quantity"].sum() / 2.0)
        
        # Current baseline P&L
        current_rev = round(base_annual_units * p_current, 2)
        current_cost = round(base_annual_units * c_base, 2)
        current_profit = round(current_rev - current_cost, 2)
        current_margin = round(((p_current - c_base) / p_current) * 100.0, 2)
        
        # Proposed P&L
        eff_new_price = round(new_price * (1.0 - (discount_pct / 100.0)), 2)
        price_ratio = eff_new_price / p_current
        comp_ratio = comp_base / eff_new_price
        
        demand_mult = (price_ratio ** epsilon) * (comp_ratio ** cross_elast) * season_multiplier * regional_multiplier
        proposed_units = round(base_annual_units * demand_mult, 1)
        proposed_rev = round(proposed_units * eff_new_price, 2)
        proposed_cost = round(proposed_units * c_base, 2)
        proposed_profit = round(proposed_rev - proposed_cost, 2)
        proposed_margin = round(((eff_new_price - c_base) / eff_new_price) * 100.0, 2) if eff_new_price > 0 else 0.0
        
        # Deltas
        delta_units = round(proposed_units - base_annual_units, 1)
        delta_units_pct = round((delta_units / base_annual_units) * 100.0, 2) if base_annual_units > 0 else 0.0
        
        delta_rev = round(proposed_rev - current_rev, 2)
        delta_rev_pct = round((delta_rev / current_rev) * 100.0, 2) if current_rev > 0 else 0.0
        
        delta_profit = round(proposed_profit - current_profit, 2)
        delta_profit_pct = round((delta_profit / current_profit) * 100.0, 2) if current_profit > 0 else 0.0

        return {
            "product_id": product_id,
            "product_name": e_info["product_name"],
            "category": e_info["category"],
            "elasticity": e_info["elasticity"],
            "classification": e_info["classification"],
            "base_cost": c_base,
            "current_price": p_current,
            "new_price": new_price,
            "effective_new_price": eff_new_price,
            "competitor_price": comp_base,
            "discount_pct": discount_pct,
            
            # Baseline
            "current_units": base_annual_units,
            "current_revenue": current_rev,
            "current_profit": current_profit,
            "current_margin_pct": current_margin,
            
            # Proposed
            "proposed_units": proposed_units,
            "proposed_revenue": proposed_rev,
            "proposed_profit": proposed_profit,
            "proposed_margin_pct": proposed_margin,
            
            # Deltas
            "delta_units": delta_units,
            "delta_units_pct": delta_units_pct,
            "delta_revenue": delta_rev,
            "delta_revenue_pct": delta_rev_pct,
            "delta_profit": delta_profit,
            "delta_profit_pct": delta_profit_pct
        }


def main():
    print("=" * 60)
    print("RetailX Pricing Optimizer & Opportunity Engine Running...")
    print("=" * 60)
    
    optimizer = PricingOptimizer()
    df_opt = optimizer.optimize_all_products()
    
    print(f"Catalog Products Optimized: {len(df_opt)}")
    
    total_current_profit = df_opt["current_annual_profit"].sum()
    total_opt_profit = df_opt["profit_max_expected_profit"].sum()
    total_profit_upside = df_opt["profit_max_profit_upside"].sum()
    
    total_current_rev = df_opt["current_annual_revenue"].sum()
    total_opt_rev = df_opt["rev_max_expected_revenue"].sum()
    total_rev_upside = df_opt["rev_max_revenue_upside"].sum()
    
    print(f"Baseline Annual Revenue: ${total_current_rev:,.2f}")
    print(f"Potential Revenue Upside: +${total_rev_upside:,.2f} (+{round((total_rev_upside/total_current_rev)*100, 2)}%)")
    print(f"Baseline Annual Profit:  ${total_current_profit:,.2f}")
    print(f"Potential Profit Upside:  +${total_profit_upside:,.2f} (+{round((total_profit_upside/total_current_profit)*100, 2)}%)")
    
    print("\n--- Top 5 Profit Optimization Opportunities ---")
    top5 = df_opt.sort_values(by="profit_max_profit_upside", ascending=False).head(5)
    cols = ["product_name", "current_price", "profit_max_price", "profit_max_price_change_pct", "profit_max_profit_upside"]
    print(top5[cols].to_string(index=False))
    print("=" * 60)

if __name__ == "__main__":
    main()
