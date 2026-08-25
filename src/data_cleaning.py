"""
RetailX Production Data Cleaning & ETL Pipeline
----------------------------------------------
Implements a production-grade data cleaning and validation pipeline:
1. Audits raw data anomalies (duplicates, nulls, outliers, type inconsistencies)
2. Executes systematic remediation rules
3. Re-validates microeconomic & accounting identities:
   - Revenue = Quantity * Unit Price * (1 - Discount)
   - Cost = Quantity * Base Cost
   - Profit = Revenue - Cost
   - Profit Margin % = (Profit / Revenue) * 100
4. Exports standardized datasets to data/processed/
5. Populates SQLite database (sql/retailx.db)
"""

import os
import json
import sqlite3
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
SQL_DIR = os.path.join(PROJECT_ROOT, "sql")
DB_PATH = os.path.join(SQL_DIR, "retailx.db")

os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(SQL_DIR, exist_ok=True)


class DataCleaner:
    def __init__(self):
        self.audit_log = {
            "customers": {},
            "products": {},
            "sales": {},
            "pricing_history": {},
            "summary": {}
        }

    def clean_customers(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate customer master data."""
        df = df_raw.copy()
        initial_rows = len(df)
        
        # 1. Deduplication
        dups = df.duplicated(subset=["customer_id"]).sum()
        df = df.drop_duplicates(subset=["customer_id"])
        
        # 2. String standardization
        for col in ["customer_segment", "age_group", "region", "acquisition_channel"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                
        # 3. Handle missing values
        null_regions = (df["region"] == "nan") | df["region"].isna()
        null_reg_count = int(null_regions.sum())
        # Impute missing region with mode
        mode_region = df.loc[~null_regions, "region"].mode()[0] if not df.loc[~null_regions, "region"].empty else "East"
        df.loc[null_regions, "region"] = mode_region
        
        # 4. Numeric bounds validation
        df["customer_lifetime_value"] = pd.to_numeric(df["customer_lifetime_value"], errors="coerce").fillna(0.0)
        df["customer_lifetime_value"] = df["customer_lifetime_value"].clip(lower=0.0).round(2)
        
        self.audit_log["customers"] = {
            "initial_rows": initial_rows,
            "final_rows": len(df),
            "duplicates_removed": int(dups),
            "null_regions_imputed": null_reg_count,
            "imputation_strategy": f"Mode imputation ('{mode_region}')"
        }
        return df

    def clean_products(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate product catalog data."""
        df = df_raw.copy()
        initial_rows = len(df)
        
        # 1. Standardize category strings (trim, title-case mapping)
        category_map = {
            "electronics": "Electronics",
            "apparel & footwear": "Apparel & Footwear",
            "home & kitchen": "Home & Kitchen",
            "health & beauty": "Health & Beauty",
            "sports & outdoors": "Sports & Outdoors"
        }
        df["category"] = df["category"].astype(str).str.strip()
        df["category"] = df["category"].apply(lambda c: category_map.get(c.lower(), c.title()))
        
        if "subcategory" in df.columns:
            df["subcategory"] = df["subcategory"].astype(str).str.strip().str.title()
            
        # 2. Numeric validation & rounding
        num_cols = ["base_cost", "current_price", "competitor_price", "inventory_level", "seasonality_factor"]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
                
        df["base_cost"] = df["base_cost"].clip(lower=0.01).round(2)
        df["current_price"] = df["current_price"].clip(lower=0.01).round(2)
        df["competitor_price"] = df["competitor_price"].clip(lower=0.01).round(2)
        df["inventory_level"] = df["inventory_level"].fillna(0).astype(int)
        
        # Calculate base profit margin %
        df["base_margin_pct"] = (((df["current_price"] - df["base_cost"]) / df["current_price"]) * 100).round(2)
        
        self.audit_log["products"] = {
            "initial_rows": initial_rows,
            "final_rows": len(df),
            "categories_standardized": df["category"].nunique(),
            "avg_base_margin_pct": round(float(df["base_margin_pct"].mean()), 2)
        }
        return df

    def clean_sales(self, df_raw: pd.DataFrame, df_products_clean: pd.DataFrame) -> pd.DataFrame:
        """Clean, deduplicate, and validate sales transaction records."""
        df = df_raw.copy()
        initial_rows = len(df)
        
        # 1. Remove duplicate transactions
        initial_dups = int(df.duplicated(subset=["transaction_id"]).sum())
        df = df.drop_duplicates(subset=["transaction_id"])
        
        # 2. Date parsing & standardization (handles YYYY-MM-DD and MM/DD/YYYY)
        df["date"] = pd.to_datetime(df["date"], errors="coerce", format="mixed").dt.strftime("%Y-%m-%d")
        df = df.dropna(subset=["date"])
        
        # 3. Drop negative or zero invalid quantity/price glitch records
        invalid_mask = (df["quantity"] <= 0) | (df["unit_price"] <= 0) | (df["revenue"] <= 0)
        invalid_count = int(invalid_mask.sum())
        df = df[~invalid_mask].copy()
        
        # 4. Impute missing customer IDs
        missing_cust_count = int(df["customer_id"].isna().sum())
        df["customer_id"] = df["customer_id"].fillna("CUST-GUEST")
        
        # 5. Impute missing discount values
        missing_disc_count = int(df["discount"].isna().sum())
        df["discount"] = df["discount"].fillna(0.0).clip(lower=0.0, upper=0.50)
        
        # 6. Merge base_cost from clean products for accounting reconciliation
        prod_cost_map = df_products_clean.set_index("product_id")["base_cost"].to_dict()
        df["base_cost"] = df["product_id"].map(prod_cost_map)
        
        # 7. Strictly enforce accounting identities
        df["quantity"] = df["quantity"].astype(int)
        df["unit_price"] = df["unit_price"].astype(float).round(2)
        df["discount"] = df["discount"].astype(float).round(4)
        
        df["effective_price"] = (df["unit_price"] * (1.0 - df["discount"])).round(2)
        df["revenue"] = (df["quantity"] * df["effective_price"]).round(2)
        df["cost"] = (df["quantity"] * df["base_cost"]).round(2)
        df["profit"] = (df["revenue"] - df["cost"]).round(2)
        df["profit_margin_pct"] = np.where(df["revenue"] > 0, ((df["profit"] / df["revenue"]) * 100).round(2), 0.0)
        
        # Add year, month, year_month for analytics
        df["year"] = pd.to_datetime(df["date"]).dt.year
        df["month"] = pd.to_datetime(df["date"]).dt.month
        df["year_month"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m")
        df["day_of_week"] = pd.to_datetime(df["date"]).dt.day_name()
        
        self.audit_log["sales"] = {
            "initial_rows": initial_rows,
            "final_rows": len(df),
            "duplicates_removed": initial_dups,
            "invalid_records_removed": invalid_count,
            "missing_customer_ids_imputed": missing_cust_count,
            "missing_discounts_imputed": missing_disc_count,
            "total_clean_revenue": round(float(df["revenue"].sum()), 2),
            "total_clean_profit": round(float(df["profit"].sum()), 2),
            "overall_profit_margin_pct": round(float((df["profit"].sum() / df["revenue"].sum()) * 100), 2)
        }
        return df

    def clean_pricing_history(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate pricing history daily metrics."""
        df = df_raw.copy()
        initial_rows = len(df)
        
        df = df.drop_duplicates(subset=["date", "product_id"])
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df = df.dropna(subset=["date"])
        
        df["price"] = pd.to_numeric(df["price"], errors="coerce").clip(lower=0.01).round(2)
        df["competitor_price"] = pd.to_numeric(df["competitor_price"], errors="coerce").clip(lower=0.01).round(2)
        df["quantity_sold"] = pd.to_numeric(df["quantity_sold"], errors="coerce").fillna(0).astype(int)
        df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0.0).round(2)
        
        self.audit_log["pricing_history"] = {
            "initial_rows": initial_rows,
            "final_rows": len(df)
        }
        return df

    def export_to_sqlite(self, df_customers, df_products, df_sales, df_pricing):
        """Populate clean SQLite database with indexes."""
        conn = sqlite3.connect(DB_PATH)
        
        df_customers.to_sql("customers", conn, if_exists="replace", index=False)
        df_products.to_sql("products", conn, if_exists="replace", index=False)
        df_sales.to_sql("sales", conn, if_exists="replace", index=False)
        df_pricing.to_sql("pricing_history", conn, if_exists="replace", index=False)
        
        # Create analytical indexes
        cursor = conn.cursor()
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(date);",
            "CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_id);",
            "CREATE INDEX IF NOT EXISTS idx_sales_customer ON sales(customer_id);",
            "CREATE INDEX IF NOT EXISTS idx_sales_region ON sales(region);",
            "CREATE INDEX IF NOT EXISTS idx_sales_year_month ON sales(year_month);",
            "CREATE INDEX IF NOT EXISTS idx_pricing_date_prod ON pricing_history(date, product_id);",
            "CREATE INDEX IF NOT EXISTS idx_products_cat ON products(category);"
        ]
        for idx_stmt in indexes:
            cursor.execute(idx_stmt)
            
        conn.commit()
        conn.close()
        print(f"SQLite database successfully created and indexed at: {DB_PATH}")


def run_pipeline():
    print("=" * 60)
    print("RetailX Production Data Cleaning Pipeline Running...")
    print("=" * 60)
    
    cleaner = DataCleaner()
    
    # 1. Load raw files
    df_raw_cust = pd.read_csv(os.path.join(RAW_DATA_DIR, "customers.csv"))
    df_raw_prod = pd.read_csv(os.path.join(RAW_DATA_DIR, "products.csv"))
    df_raw_sales = pd.read_csv(os.path.join(RAW_DATA_DIR, "sales.csv"))
    df_raw_pricing = pd.read_csv(os.path.join(RAW_DATA_DIR, "pricing_history.csv"))
    
    print(f"Raw Sales Records Loaded: {len(df_raw_sales):,}")
    
    # 2. Clean tables
    df_clean_cust = cleaner.clean_customers(df_raw_cust)
    df_clean_prod = cleaner.clean_products(df_raw_prod)
    df_clean_sales = cleaner.clean_sales(df_raw_sales, df_clean_prod)
    df_clean_pricing = cleaner.clean_pricing_history(df_raw_pricing)
    
    # 3. Export to processed CSVs
    df_clean_cust.to_csv(os.path.join(PROCESSED_DATA_DIR, "customers_clean.csv"), index=False)
    df_clean_prod.to_csv(os.path.join(PROCESSED_DATA_DIR, "products_clean.csv"), index=False)
    df_clean_sales.to_csv(os.path.join(PROCESSED_DATA_DIR, "sales_clean.csv"), index=False)
    df_clean_pricing.to_csv(os.path.join(PROCESSED_DATA_DIR, "pricing_history_clean.csv"), index=False)
    
    # 4. Save audit log JSON
    audit_path = os.path.join(PROCESSED_DATA_DIR, "data_cleaning_audit.json")
    with open(audit_path, "w") as f:
        json.dump(cleaner.audit_log, f, indent=2)
        
    # 5. Populate SQLite DB
    cleaner.export_to_sqlite(df_clean_cust, df_clean_prod, df_clean_sales, df_clean_pricing)
    
    print("=" * 60)
    print("DATA CLEANING COMPLETE:")
    print(f" - Clean Customers: {len(df_clean_cust):,} rows")
    print(f" - Clean Products: {len(df_clean_prod):,} rows")
    print(f" - Clean Sales: {len(df_clean_sales):,} rows")
    print(f" - Clean Pricing History: {len(df_clean_pricing):,} rows")
    print(f" - Total Revenue: ${cleaner.audit_log['sales']['total_clean_revenue']:,.2f}")
    print(f" - Total Profit: ${cleaner.audit_log['sales']['total_clean_profit']:,.2f}")
    print(f" - Overall Profit Margin: {cleaner.audit_log['sales']['overall_profit_margin_pct']}%")
    print(f" - Audit log saved to: {audit_path}")
    print("=" * 60)
    return cleaner.audit_log


if __name__ == "__main__":
    run_pipeline()
