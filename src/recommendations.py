"""
RetailX Pricing Recommendation Engine
------------------------------------
Synthesizes price elasticity, competitor positioning, gross margins,
and inventory velocity to generate concrete, explainable, and quantified
pricing recommendations for every product in the catalog.
"""

import os
import sys
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
from src.elasticity import PriceElasticityEngine
from src.pricing_optimizer import PricingOptimizer


class PricingRecommendationEngine:
    def __init__(self):
        self.elast_engine = PriceElasticityEngine()
        self.optimizer = PricingOptimizer(self.elast_engine)
        self.df_products = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "products_clean.csv"))
        self.df_sales = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "sales_clean.csv"))

    def generate_product_recommendations(self) -> pd.DataFrame:
        """
        Generate actionable pricing recommendations for all catalog products.
        """
        opt_df = self.optimizer.optimize_all_products()
        recs = []
        
        for _, row in opt_df.iterrows():
            pid = row["product_id"]
            p_name = row["product_name"]
            cat = row["category"]
            p_curr = row["current_price"]
            p_comp = row["competitor_price"]
            c_base = row["base_cost"]
            margin_pct = row["current_margin_pct"]
            epsilon = row["elasticity"]
            classification = row["classification"]
            
            # Target profit-maximizing candidate
            p_opt = row["profit_max_price"]
            opt_delta_pct = row["profit_max_price_change_pct"]
            profit_upside = row["profit_max_profit_upside"]
            profit_upside_pct = row["profit_max_profit_upside_pct"]
            
            comp_diff_pct = ((p_curr - p_comp) / p_comp) * 100.0
            
            # Check inventory turnover proxy
            p_sales = self.df_sales[self.df_sales["product_id"] == pid]
            annual_units = row["current_annual_units"]
            inv_level = self.df_products.loc[self.df_products["product_id"] == pid, "inventory_level"].values[0]
            monthly_turn = (annual_units / 12.0) / max(1, inv_level)
            
            # Recommendation Decision Logic
            if classification == "Inelastic":
                # Inelastic demand: Raising price captures immediate margin with minimal volume drop
                if p_curr < p_comp:
                    rec_action = "Increase Price"
                    rec_change_pct = min(12.0, max(5.0, round(abs(comp_diff_pct) * 0.8, 1)))
                    recommended_price = round(p_curr * (1.0 + (rec_change_pct / 100.0)), 2)
                    priority = "High"
                    rationale = (
                        f"Inelastic demand (e = {epsilon:.2f}) and currently priced {abs(comp_diff_pct):.1f}% below competitor "
                        f"(${p_comp:.2f}). Raising price by {rec_change_pct:.1f}% captures significant margin with minimal volume erosion."
                    )
                else:
                    rec_action = "Increase Price"
                    rec_change_pct = 5.0
                    recommended_price = round(p_curr * 1.05, 2)
                    priority = "Medium"
                    rationale = (
                        f"Inelastic demand profile (e = {epsilon:.2f}) indicates strong pricing power. "
                        f"A conservative 5.0% price increase will expand gross margin without hurting demand."
                    )
            elif classification == "Highly Sensitive":
                # Highly sensitive / elastic: If priced higher than competitor, lowering price recaptures volume
                if comp_diff_pct > 2.0:
                    rec_action = "Decrease Price"
                    rec_change_pct = -min(15.0, max(5.0, round(comp_diff_pct * 1.1, 1)))
                    recommended_price = round(p_curr * (1.0 + (rec_change_pct / 100.0)), 2)
                    priority = "High"
                    rationale = (
                        f"Highly price sensitive (e = {epsilon:.2f}) and overpriced by {comp_diff_pct:.1f}% vs competitor (${p_comp:.2f}). "
                        f"Lowering price to parity unlocks massive volume surges and expands net dollar profit."
                    )
                else:
                    if monthly_turn < 0.35:
                        rec_action = "Discount / Clearance"
                        rec_change_pct = -10.0
                        recommended_price = round(p_curr * 0.90, 2)
                        priority = "Medium"
                        rationale = (
                            f"High price sensitivity (e = {epsilon:.2f}) combined with slow inventory turn ({monthly_turn:.2f}x/mo). "
                            f"A 10% promotional discount will clear excess stock and boost cash flow."
                        )
                    else:
                        rec_action = "Maintain Price"
                        rec_change_pct = 0.0
                        recommended_price = p_curr
                        priority = "Low"
                        rationale = (
                            f"Competitor pricing is close to parity (${p_comp:.2f}). Price sensitivity (e = {epsilon:.2f}) "
                            f"makes price increases risky. Maintain current price and protect market share."
                        )
            else: # Elastic (-1.0 to -2.0)
                if abs(opt_delta_pct) < 3.0:
                    rec_action = "Maintain Price"
                    rec_change_pct = 0.0
                    recommended_price = p_curr
                    priority = "Low"
                    rationale = (
                        f"Current price (${p_curr:.2f}) is already within 3% of theoretical profit-maximizing optimum. "
                        f"Maintain stable pricing to preserve predictable sales velocity."
                    )
                elif opt_delta_pct < 0:
                    rec_action = "Decrease Price"
                    rec_change_pct = max(-10.0, round(opt_delta_pct, 1))
                    recommended_price = round(p_curr * (1.0 + (rec_change_pct / 100.0)), 2)
                    priority = "Medium"
                    rationale = (
                        f"Elastic demand (e = {epsilon:.2f}). Reducing price by {abs(rec_change_pct):.1f}% stimulates "
                        f"sufficient incremental unit volume to grow overall gross profit."
                    )
                else:
                    rec_action = "Increase Price"
                    rec_change_pct = min(8.0, round(opt_delta_pct, 1))
                    recommended_price = round(p_curr * (1.0 + (rec_change_pct / 100.0)), 2)
                    priority = "Medium"
                    rationale = (
                        f"Healthy unit margin spread (${p_curr - c_base:.2f}) with competitor supporting higher price point (${p_comp:.2f}). "
                        f"A moderate price hike of {rec_change_pct:.1f}% enhances profitability."
                    )

            # Re-estimate scenario outcomes using the recommended price
            sim_res = self.optimizer.simulate_custom_scenario(
                product_id=pid,
                new_price=recommended_price,
                competitor_price=p_comp
            )
            
            # 2x2 Matrix Quadrant Tagging
            # X: Elasticity (abs(e)), Y: Margin %
            if abs(epsilon) < 1.3 and margin_pct >= 50.0:
                quadrant = "Q1: Premium Margin & Pricing Power"
            elif abs(epsilon) >= 1.3 and margin_pct >= 50.0:
                quadrant = "Q2: High Margin Volume Driver"
            elif abs(epsilon) < 1.3 and margin_pct < 50.0:
                quadrant = "Q3: Margin Repair Candidate"
            else:
                quadrant = "Q4: Price Sensitive / Operational Focus"
                
            recs.append({
                "product_id": pid,
                "product_name": p_name,
                "category": cat,
                "current_price": p_curr,
                "competitor_price": p_comp,
                "base_cost": c_base,
                "current_margin_pct": margin_pct,
                "elasticity": epsilon,
                "classification": classification,
                "recommendation": rec_action,
                "recommended_price": recommended_price,
                "recommended_change_pct": rec_change_pct,
                "priority": priority,
                "expected_volume_change_pct": sim_res.get("delta_units_pct", 0.0),
                "expected_revenue_impact": sim_res.get("delta_revenue", 0.0),
                "expected_revenue_impact_pct": sim_res.get("delta_revenue_pct", 0.0),
                "expected_profit_impact": sim_res.get("delta_profit", 0.0),
                "expected_profit_impact_pct": sim_res.get("delta_profit_pct", 0.0),
                "opportunity_quadrant": quadrant,
                "rationale": rationale
            })
            
        return pd.DataFrame(recs).sort_values(by="expected_profit_impact", ascending=False)


def main():
    print("=" * 60)
    print("RetailX Pricing Recommendation Engine Running...")
    print("=" * 60)
    
    engine = PricingRecommendationEngine()
    df_recs = engine.generate_product_recommendations()
    
    print(f"Generated recommendations for {len(df_recs)} catalog products.\n")
    
    action_counts = df_recs["recommendation"].value_counts()
    print("--- Recommended Actions Summary ---")
    for action, count in action_counts.items():
        print(f" - {action}: {count} products")
        
    total_prof_impact = df_recs["expected_profit_impact"].sum()
    total_rev_impact = df_recs["expected_revenue_impact"].sum()
    print(f"\nNet Estimated Annual Profit Upside: +${total_prof_impact:,.2f}")
    print(f"Net Estimated Annual Revenue Upside: +${total_rev_impact:,.2f}")
    
    print("\n--- Sample Recommendations ---")
    cols = ["product_name", "current_price", "recommendation", "recommended_price", "expected_profit_impact", "priority"]
    print(df_recs[cols].head(8).to_string(index=False))
    print("=" * 60)

if __name__ == "__main__":
    main()
