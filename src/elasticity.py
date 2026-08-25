"""
RetailX Econometric Price Elasticity Engine
------------------------------------------
Calculates empirical Price Elasticity of Demand (PED) using
log-log Ordinary Least Squares (OLS) regression:
    ln(Q_t) = beta_0 + beta_1 * ln(P_t) + beta_2 * ln(P_comp_t) + beta_3 * Seasonality_t + e_t

Outputs:
- Elasticity coefficient (beta_1)
- Standard errors, t-statistics, p-values, 95% Confidence Intervals
- R-squared goodness-of-fit
- Elasticity classification (Inelastic, Elastic, Highly Sensitive)
- Product & category level aggregations
"""

import os
import math
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")


def _run_ols_regression(X_mat: np.ndarray, y_vec: np.ndarray) -> Dict:
    """
    Computes exact closed-form OLS regression with standard errors,
    t-statistics, two-tailed p-values, and R-squared.
    """
    n, k = X_mat.shape
    df = n - k
    
    # beta_hat = (X^T X)^(-1) X^T y
    xtx_inv = np.linalg.pinv(X_mat.T @ X_mat)
    beta_hat = xtx_inv @ (X_mat.T @ y_vec)
    
    # Residuals & Variance
    residuals = y_vec - (X_mat @ beta_hat)
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y_vec - np.mean(y_vec)) ** 2)
    s2 = ss_res / max(1, df)
    
    # Covariance matrix & Standard Errors
    cov_beta = s2 * xtx_inv
    se_beta = np.sqrt(np.maximum(0, np.diag(cov_beta)))
    
    # t-stats & p-values (using erfc for asymptotic standard normal/t approximation)
    t_stats = np.where(se_beta > 0, beta_hat / se_beta, 0.0)
    p_values = np.array([math.erfc(abs(t) / math.sqrt(2)) for t in t_stats])
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    
    return {
        "params": beta_hat,
        "bse": se_beta,
        "tvalues": t_stats,
        "pvalues": p_values,
        "rsquared": float(r_squared),
        "nobs": n,
        "df_resid": df
    }


class PriceElasticityEngine:
    def __init__(self, df_pricing_history: Optional[pd.DataFrame] = None, df_products: Optional[pd.DataFrame] = None):
        if df_pricing_history is None:
            self.df_pricing = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "pricing_history_clean.csv"))
        else:
            self.df_pricing = df_pricing_history.copy()
            
        if df_products is None:
            self.df_products = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "products_clean.csv"))
        else:
            self.df_products = df_products.copy()
            
        self._prepare_data()

    def _prepare_data(self):
        """Prepare log transforms, date features, and merge product attributes."""
        df = self.df_pricing.copy()
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.month
        df["year_month"] = df["date"].dt.strftime("%Y-%m")
        
        # Merge product category and metadata
        df = df.merge(self.df_products[["product_id", "product_name", "category", "base_cost", "current_price"]], on="product_id", how="left")
        
        # Ensure positive non-zero quantities for log transformation
        df["quantity_sold_adj"] = df["quantity_sold"].clip(lower=1)
        df["price_adj"] = df["price"].clip(lower=0.01)
        df["comp_price_adj"] = df["competitor_price"].clip(lower=0.01)
        
        df["ln_quantity"] = np.log(df["quantity_sold_adj"])
        df["ln_price"] = np.log(df["price_adj"])
        df["ln_comp_price"] = np.log(df["comp_price_adj"])
        
        self.df_data = df

    def estimate_product_elasticity(self, product_id: str) -> Dict:
        """
        Estimate econometric price elasticity for a single product via Log-Log OLS.
        Model: ln(Q) = beta_0 + beta_1*ln(P) + beta_2*ln(P_comp) + beta_3*Month
        """
        p_df = self.df_data[self.df_data["product_id"] == product_id].copy()
        if len(p_df) < 30:
            return None
            
        p_meta = self.df_products[self.df_products["product_id"] == product_id].iloc[0]
        
        # Build design matrix: [1, ln_price, ln_comp_price, month]
        X = np.column_stack([
            np.ones(len(p_df)),
            p_df["ln_price"].values,
            p_df["ln_comp_price"].values,
            p_df["month"].values
        ])
        y = p_df["ln_quantity"].values
        
        try:
            res = _run_ols_regression(X, y)
            
            coef = float(res["params"][1])
            se = float(res["bse"][1])
            t_stat = float(res["tvalues"][1])
            p_val = float(res["pvalues"][1])
            ci_lower = coef - 1.96 * se
            ci_upper = coef + 1.96 * se
            r2 = float(res["rsquared"])
            
            cross_coef = float(res["params"][2])
            cross_pval = float(res["pvalues"][2])
            
            # Classification logic
            if coef > -1.0:
                classification = "Inelastic"
                pricing_power = "High Pricing Power (Low Sensitivity)"
            elif coef >= -2.0:
                classification = "Elastic"
                pricing_power = "Moderate Sensitivity (Volume Driven)"
            else:
                classification = "Highly Sensitive"
                pricing_power = "Extreme Sensitivity (Competitor Risk)"
                
            confidence = "High (p < 0.01)" if p_val < 0.01 else ("Moderate (p < 0.05)" if p_val < 0.05 else "Low (p >= 0.05)")
            
            avg_daily_demand = float(p_df["quantity_sold"].mean())
            current_p = float(p_meta["current_price"])
            base_c = float(p_meta["base_cost"])
            comp_p = float(p_meta["competitor_price"])
            
            return {
                "product_id": product_id,
                "product_name": p_meta["product_name"],
                "category": p_meta["category"],
                "elasticity": round(coef, 3),
                "std_error": round(se, 3),
                "t_statistic": round(t_stat, 2),
                "p_value": round(p_val, 4),
                "ci_lower_95": round(ci_lower, 3),
                "ci_upper_95": round(ci_upper, 3),
                "cross_price_elasticity": round(cross_coef, 3),
                "cross_p_value": round(cross_pval, 4),
                "r_squared": round(r2, 3),
                "observations": int(len(p_df)),
                "classification": classification,
                "pricing_power": pricing_power,
                "confidence": confidence,
                "current_price": current_p,
                "base_cost": base_c,
                "competitor_price": comp_p,
                "avg_daily_demand": round(avg_daily_demand, 1),
                "intercept": float(res["params"][0])
            }
        except Exception as e:
            print(f"Error estimating elasticity for {product_id}: {e}")
            return None

    def calculate_all_product_elasticities(self) -> pd.DataFrame:
        """Compute elasticity metrics for all products in catalog."""
        results = []
        for pid in self.df_products["product_id"].unique():
            res = self.estimate_product_elasticity(pid)
            if res:
                results.append(res)
        return pd.DataFrame(results).sort_values(by="elasticity", ascending=True)

    def calculate_category_elasticity(self) -> pd.DataFrame:
        """Compute aggregate price elasticity across each category."""
        cat_results = []
        for cat in self.df_products["category"].unique():
            cat_df = self.df_data[self.df_data["category"] == cat].copy()
            if len(cat_df) < 50:
                continue
                
            X = np.column_stack([
                np.ones(len(cat_df)),
                cat_df["ln_price"].values,
                cat_df["ln_comp_price"].values,
                cat_df["month"].values
            ])
            y = cat_df["ln_quantity"].values
            
            try:
                res = _run_ols_regression(X, y)
                coef = float(res["params"][1])
                se = float(res["bse"][1])
                r2 = float(res["rsquared"])
                p_val = float(res["pvalues"][1])
                
                cat_results.append({
                    "category": cat,
                    "category_elasticity": round(coef, 3),
                    "std_error": round(se, 3),
                    "p_value": round(p_val, 4),
                    "r_squared": round(r2, 3),
                    "classification": "Inelastic" if coef > -1.0 else ("Elastic" if coef >= -2.0 else "Highly Sensitive"),
                    "total_observations": int(len(cat_df))
                })
            except Exception as e:
                print(f"Error estimating category elasticity for {cat}: {e}")
                
        return pd.DataFrame(cat_results).sort_values(by="category_elasticity", ascending=True)


def main():
    print("=" * 60)
    print("RetailX Econometric Price Elasticity Engine Running...")
    print("=" * 60)
    
    engine = PriceElasticityEngine()
    df_prod_elast = engine.calculate_all_product_elasticities()
    df_cat_elast = engine.calculate_category_elasticity()
    
    print("\n--- Product-Level Price Elasticity Summary ---")
    print(df_prod_elast[["product_id", "product_name", "category", "elasticity", "classification", "r_squared"]].to_string(index=False))
    
    print("\n--- Category-Level Price Elasticity Summary ---")
    print(df_cat_elast.to_string(index=False))
    print("=" * 60)

if __name__ == "__main__":
    main()
