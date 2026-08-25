"""
RetailX Synthetic Data Generation Engine
----------------------------------------
Generates a realistic, multi-factor e-commerce transaction dataset with
true underlying microeconomic demand dynamics:
- Price elasticity of demand (varying from highly inelastic to highly elastic)
- Cross-price competitor effects
- Monthly category seasonality curves
- Customer segment purchasing behaviors and regional weights
- Inventory constraints and stockout dynamics
- Injected real-world data quality issues for raw/ ETL pipeline
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Set seeds for deterministic reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. Product Catalog Definition with True Econometric Parameters
# ---------------------------------------------------------
PRODUCT_CATALOG = [
    # Electronics
    {
        "product_id": "PRD-E01",
        "product_name": "Wireless Noise-Canceling Headphones",
        "category": "Electronics",
        "subcategory": "Audio",
        "base_cost": 85.00,
        "base_price": 149.99,
        "base_competitor_price": 144.99,
        "true_elasticity": -1.65,
        "cross_elasticity": 0.55,
        "base_daily_demand": 4.5,
        "inventory_level": 450,
        "seasonality_type": "holiday_heavy"
    },
    {
        "product_id": "PRD-E02",
        "product_name": "Smart Fitness Watch Pro",
        "category": "Electronics",
        "subcategory": "Wearables",
        "base_cost": 110.00,
        "base_price": 199.99,
        "base_competitor_price": 194.99,
        "true_elasticity": -1.35,
        "cross_elasticity": 0.45,
        "base_daily_demand": 3.8,
        "inventory_level": 380,
        "seasonality_type": "holiday_fitness"
    },
    {
        "product_id": "PRD-E03",
        "product_name": "4K Ultra HD Action Camera",
        "category": "Electronics",
        "subcategory": "Cameras",
        "base_cost": 140.00,
        "base_price": 249.99,
        "base_competitor_price": 239.00,
        "true_elasticity": -2.15,
        "cross_elasticity": 0.70,
        "base_daily_demand": 2.6,
        "inventory_level": 220,
        "seasonality_type": "summer_holiday"
    },
    {
        "product_id": "PRD-E04",
        "product_name": "Bluetooth Portable Speaker",
        "category": "Electronics",
        "subcategory": "Audio",
        "base_cost": 26.00,
        "base_price": 59.99,
        "base_competitor_price": 54.99,
        "true_elasticity": -1.80,
        "cross_elasticity": 0.60,
        "base_daily_demand": 5.5,
        "inventory_level": 600,
        "seasonality_type": "summer_holiday"
    },

    # Apparel & Footwear
    {
        "product_id": "PRD-A01",
        "product_name": "Ergonomic Performance Hoodie",
        "category": "Apparel & Footwear",
        "subcategory": "Activewear",
        "base_cost": 22.00,
        "base_price": 64.99,
        "base_competitor_price": 62.00,
        "true_elasticity": -1.15,
        "cross_elasticity": 0.35,
        "base_daily_demand": 5.2,
        "inventory_level": 520,
        "seasonality_type": "winter_heavy"
    },
    {
        "product_id": "PRD-A02",
        "product_name": "Trail Running Shoes Elite",
        "category": "Apparel & Footwear",
        "subcategory": "Footwear",
        "base_cost": 44.00,
        "base_price": 119.99,
        "base_competitor_price": 114.99,
        "true_elasticity": -1.45,
        "cross_elasticity": 0.50,
        "base_daily_demand": 4.0,
        "inventory_level": 400,
        "seasonality_type": "spring_summer"
    },
    {
        "product_id": "PRD-A03",
        "product_name": "Thermal Compression Leggings",
        "category": "Apparel & Footwear",
        "subcategory": "Activewear",
        "base_cost": 14.00,
        "base_price": 44.99,
        "base_competitor_price": 47.99,
        "true_elasticity": -0.82,  # Inelastic staple / pricing power!
        "cross_elasticity": 0.25,
        "base_daily_demand": 6.8,
        "inventory_level": 700,
        "seasonality_type": "winter_heavy"
    },
    {
        "product_id": "PRD-A04",
        "product_name": "Waterproof Windbreaker Jacket",
        "category": "Apparel & Footwear",
        "subcategory": "Outerwear",
        "base_cost": 38.00,
        "base_price": 94.99,
        "base_competitor_price": 98.00,
        "true_elasticity": -1.25,
        "cross_elasticity": 0.40,
        "base_daily_demand": 3.6,
        "inventory_level": 340,
        "seasonality_type": "fall_spring"
    },

    # Home & Kitchen
    {
        "product_id": "PRD-H01",
        "product_name": "Stainless Steel Damask Chef Knife",
        "category": "Home & Kitchen",
        "subcategory": "Cookware",
        "base_cost": 18.00,
        "base_price": 49.99,
        "base_competitor_price": 54.99,
        "true_elasticity": -0.68,  # Inelastic
        "cross_elasticity": 0.20,
        "base_daily_demand": 4.8,
        "inventory_level": 480,
        "seasonality_type": "holiday_cooking"
    },
    {
        "product_id": "PRD-H02",
        "product_name": "Smart Air Purifier True HEPA",
        "category": "Home & Kitchen",
        "subcategory": "Appliances",
        "base_cost": 75.00,
        "base_price": 159.99,
        "base_competitor_price": 149.99,
        "true_elasticity": -1.55,
        "cross_elasticity": 0.50,
        "base_daily_demand": 3.0,
        "inventory_level": 280,
        "seasonality_type": "spring_fall"
    },
    {
        "product_id": "PRD-H03",
        "product_name": "Barista Touch Espresso Machine",
        "category": "Home & Kitchen",
        "subcategory": "Appliances",
        "base_cost": 160.00,
        "base_price": 299.99,
        "base_competitor_price": 284.99,
        "true_elasticity": -2.45,  # Highly elastic luxury
        "cross_elasticity": 0.80,
        "base_daily_demand": 2.0,
        "inventory_level": 160,
        "seasonality_type": "holiday_heavy"
    },
    {
        "product_id": "PRD-H04",
        "product_name": "Non-Stick Ceramic Cookware Set",
        "category": "Home & Kitchen",
        "subcategory": "Cookware",
        "base_cost": 55.00,
        "base_price": 129.99,
        "base_competitor_price": 124.99,
        "true_elasticity": -1.10,
        "cross_elasticity": 0.35,
        "base_daily_demand": 3.8,
        "inventory_level": 320,
        "seasonality_type": "holiday_cooking"
    },

    # Health & Beauty
    {
        "product_id": "PRD-B01",
        "product_name": "Organic Hydrating Face Serum",
        "category": "Health & Beauty",
        "subcategory": "Skincare",
        "base_cost": 8.50,
        "base_price": 38.00,
        "base_competitor_price": 42.00,
        "true_elasticity": -0.48,  # Highly inelastic staple, high margin
        "cross_elasticity": 0.15,
        "base_daily_demand": 7.5,
        "inventory_level": 950,
        "seasonality_type": "steady"
    },
    {
        "product_id": "PRD-B02",
        "product_name": "Advanced Anti-Aging Retinol Cream",
        "category": "Health & Beauty",
        "subcategory": "Skincare",
        "base_cost": 12.00,
        "base_price": 54.00,
        "base_competitor_price": 58.00,
        "true_elasticity": -0.58,  # Inelastic, high pricing power
        "cross_elasticity": 0.20,
        "base_daily_demand": 6.2,
        "inventory_level": 800,
        "seasonality_type": "steady"
    },
    {
        "product_id": "PRD-B03",
        "product_name": "Plant-Based Organic Protein 2lb",
        "category": "Health & Beauty",
        "subcategory": "Wellness",
        "base_cost": 16.50,
        "base_price": 39.99,
        "base_competitor_price": 37.99,
        "true_elasticity": -1.30,
        "cross_elasticity": 0.45,
        "base_daily_demand": 5.4,
        "inventory_level": 550,
        "seasonality_type": "january_fitness"
    },
    {
        "product_id": "PRD-B04",
        "product_name": "Professional Ionic Hair Dryer",
        "category": "Health & Beauty",
        "subcategory": "Haircare",
        "base_cost": 34.00,
        "base_price": 89.99,
        "base_competitor_price": 84.99,
        "true_elasticity": -1.40,
        "cross_elasticity": 0.40,
        "base_daily_demand": 3.4,
        "inventory_level": 310,
        "seasonality_type": "holiday_heavy"
    },

    # Sports & Outdoors
    {
        "product_id": "PRD-S01",
        "product_name": "Adjustable Quick-Select Dumbbells",
        "category": "Sports & Outdoors",
        "subcategory": "Fitness",
        "base_cost": 88.00,
        "base_price": 199.99,
        "base_competitor_price": 189.99,
        "true_elasticity": -1.75,
        "cross_elasticity": 0.60,
        "base_daily_demand": 3.0,
        "inventory_level": 250,
        "seasonality_type": "january_fitness"
    },
    {
        "product_id": "PRD-S02",
        "product_name": "Eco-Grip High-Density Yoga Mat",
        "category": "Sports & Outdoors",
        "subcategory": "Fitness",
        "base_cost": 8.50,
        "base_price": 29.99,
        "base_competitor_price": 32.99,
        "true_elasticity": -0.78,  # Inelastic staple
        "cross_elasticity": 0.22,
        "base_daily_demand": 7.2,
        "inventory_level": 750,
        "seasonality_type": "january_fitness"
    },
    {
        "product_id": "PRD-S03",
        "product_name": "Ultralight 2-Person Backpacking Tent",
        "category": "Sports & Outdoors",
        "subcategory": "Camping",
        "base_cost": 65.00,
        "base_price": 149.99,
        "base_competitor_price": 139.99,
        "true_elasticity": -1.95,
        "cross_elasticity": 0.65,
        "base_daily_demand": 2.5,
        "inventory_level": 210,
        "seasonality_type": "summer_outdoors"
    },
    {
        "product_id": "PRD-S04",
        "product_name": "Insulated Tactical Hydration Pack",
        "category": "Sports & Outdoors",
        "subcategory": "Camping",
        "base_cost": 19.00,
        "base_price": 49.99,
        "base_competitor_price": 47.99,
        "true_elasticity": -1.15,
        "cross_elasticity": 0.35,
        "base_daily_demand": 4.5,
        "inventory_level": 460,
        "seasonality_type": "summer_outdoors"
    }
]

# ---------------------------------------------------------
# 2. Seasonality Multipliers by Month (1-12)
# ---------------------------------------------------------
SEASONALITY_PATTERNS = {
    "holiday_heavy": [0.85, 0.80, 0.90, 0.90, 0.95, 0.95, 0.90, 1.00, 1.05, 1.20, 1.65, 1.95],
    "holiday_fitness": [1.45, 1.10, 0.95, 0.90, 0.90, 0.95, 0.90, 0.95, 1.05, 1.15, 1.50, 1.70],
    "summer_holiday": [0.75, 0.75, 0.85, 0.95, 1.25, 1.45, 1.50, 1.35, 1.00, 0.90, 1.25, 1.40],
    "winter_heavy": [1.35, 1.25, 0.95, 0.75, 0.65, 0.60, 0.60, 0.70, 0.95, 1.20, 1.55, 1.70],
    "spring_summer": [0.80, 0.85, 1.15, 1.30, 1.40, 1.35, 1.25, 1.15, 0.95, 0.85, 0.80, 0.75],
    "fall_spring": [0.85, 0.90, 1.20, 1.25, 1.05, 0.75, 0.70, 0.85, 1.25, 1.35, 1.10, 0.95],
    "holiday_cooking": [0.90, 0.85, 0.90, 0.90, 0.95, 0.90, 0.85, 0.95, 1.05, 1.25, 1.65, 1.85],
    "spring_fall": [0.90, 0.95, 1.30, 1.35, 1.20, 0.95, 0.90, 1.05, 1.25, 1.15, 0.95, 0.85],
    "steady": [0.98, 0.96, 0.99, 1.00, 1.02, 0.98, 0.97, 1.01, 1.02, 1.00, 1.03, 1.04],
    "january_fitness": [1.80, 1.35, 1.10, 1.05, 1.00, 0.95, 0.90, 0.90, 0.95, 0.95, 1.05, 1.15],
    "summer_outdoors": [0.65, 0.70, 0.90, 1.15, 1.45, 1.65, 1.70, 1.55, 1.15, 0.85, 0.70, 0.65]
}

# Customer segments
CUSTOMER_SEGMENTS = [
    {"segment": "Budget Shoppers", "weight": 0.35, "price_sensitivity": 1.30, "avg_qty": 1.1, "discount_affinity": 0.25},
    {"segment": "Value Seekers", "weight": 0.35, "price_sensitivity": 1.00, "avg_qty": 1.4, "discount_affinity": 0.15},
    {"segment": "Premium / High-End", "weight": 0.20, "price_sensitivity": 0.65, "avg_qty": 1.8, "discount_affinity": 0.05},
    {"segment": "Corporate / Bulk", "weight": 0.10, "price_sensitivity": 0.85, "avg_qty": 5.2, "discount_affinity": 0.20}
]

AGE_GROUPS = ["18-25", "26-35", "36-50", "51-65", "65+"]
ACQUISITION_CHANNELS = ["Organic Search", "Paid Social", "Email Marketing", "Referral", "Direct"]


def generate_customers(num_customers=3500):
    """Generate realistic customer base."""
    customers = []
    seg_names = [s["segment"] for s in CUSTOMER_SEGMENTS]
    seg_weights = [s["weight"] for s in CUSTOMER_SEGMENTS]

    for i in range(1, num_customers + 1):
        cust_id = f"CUST-{i:05d}"
        segment = random.choices(seg_names, weights=seg_weights, k=1)[0]
        region = random.choices(["North", "South", "East", "West"], weights=[0.28, 0.22, 0.29, 0.21], k=1)[0]
        age_group = random.choices(AGE_GROUPS, weights=[0.18, 0.38, 0.26, 0.13, 0.05], k=1)[0]
        channel = random.choices(ACQUISITION_CHANNELS, weights=[0.32, 0.28, 0.18, 0.12, 0.10], k=1)[0]
        
        base_clv = {
            "Budget Shoppers": np.random.gamma(shape=3.0, scale=120.0),
            "Value Seekers": np.random.gamma(shape=4.0, scale=220.0),
            "Premium / High-End": np.random.gamma(shape=5.0, scale=450.0),
            "Corporate / Bulk": np.random.gamma(shape=6.0, scale=1200.0)
        }[segment]

        customers.append({
            "customer_id": cust_id,
            "customer_segment": segment,
            "age_group": age_group,
            "region": region,
            "acquisition_channel": channel,
            "customer_lifetime_value": round(float(base_clv), 2)
        })
    return pd.DataFrame(customers)


def generate_products():
    """Generate product catalog table."""
    df_products = pd.DataFrame(PRODUCT_CATALOG)
    seasonality_scores = []
    for _, row in df_products.iterrows():
        pattern = SEASONALITY_PATTERNS[row["seasonality_type"]]
        score = round(max(pattern) / min(pattern), 2)
        seasonality_scores.append(score)
    df_products["seasonality_factor"] = seasonality_scores
    
    cols = [
        "product_id", "product_name", "category", "subcategory",
        "base_cost", "base_price", "base_competitor_price",
        "inventory_level", "seasonality_factor", "true_elasticity", "cross_elasticity"
    ]
    df_products = df_products[cols].rename(columns={
        "base_price": "current_price",
        "base_competitor_price": "competitor_price"
    })
    return df_products


def generate_transactions(df_customers, df_products, start_date="2024-01-01", end_date="2025-12-31"):
    """
    Simulate daily pricing and microeconomic demand across 24 months.
    Yields realistic sales transactions and daily pricing history.
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (end_dt - start_dt).days + 1
    
    sales_records = []
    pricing_history_records = []
    
    # Pre-extract customer list and lookup structures for high performance
    cust_ids = df_customers["customer_id"].values
    cust_segments = df_customers["customer_segment"].values
    cust_regions = df_customers["region"].values
    num_cust = len(cust_ids)
    
    seg_profile_map = {s["segment"]: s for s in CUSTOMER_SEGMENTS}
    
    inventory_tracker = {p["product_id"]: p["inventory_level"] * 10 for p in PRODUCT_CATALOG}
    
    # Pre-generate price fluctuation trajectories
    price_trajectories = {}
    for p in PRODUCT_CATALOG:
        pid = p["product_id"]
        base_p = p["base_price"]
        base_comp = p["base_competitor_price"]
        
        daily_prices = []
        daily_comp_prices = []
        cur_p = base_p
        cur_comp = base_comp
        
        for d in range(total_days):
            if d % 14 == 0 and d > 0:
                price_shift_pct = np.random.choice([-0.12, -0.08, -0.05, 0.0, 0.04, 0.08, 0.12], p=[0.10, 0.15, 0.20, 0.20, 0.15, 0.12, 0.08])
                cur_p = round(base_p * (1.0 + price_shift_pct), 2)
            
            if d % 21 == 0 and d > 0:
                comp_shift = np.random.choice([-0.10, -0.05, 0.0, 0.05, 0.08], p=[0.15, 0.20, 0.30, 0.20, 0.15])
                cur_comp = round(base_comp * (1.0 + comp_shift), 2)
                
            daily_prices.append(cur_p)
            daily_comp_prices.append(cur_comp)
            
        price_trajectories[pid] = {
            "price": daily_prices,
            "competitor_price": daily_comp_prices
        }
    
    transaction_counter = 1
    
    # Simulate day by day
    for day_idx in range(total_days):
        current_date = start_dt + timedelta(days=day_idx)
        date_str = current_date.strftime("%Y-%m-%d")
        month_idx = current_date.month - 1
        day_of_week = current_date.weekday()
        is_weekend = 1 if day_of_week in [5, 6] else 0
        weekend_boost = 1.22 if is_weekend else 1.0
        
        for p in PRODUCT_CATALOG:
            pid = p["product_id"]
            base_cost = p["base_cost"]
            base_p = p["base_price"]
            elasticity = p["true_elasticity"]
            cross_elast = p["cross_elasticity"]
            seasonality_curve = SEASONALITY_PATTERNS[p["seasonality_type"]]
            season_mult = seasonality_curve[month_idx]
            
            p_today = price_trajectories[pid]["price"][day_idx]
            comp_today = price_trajectories[pid]["competitor_price"][day_idx]
            
            price_effect = (p_today / base_p) ** elasticity
            comp_effect = (comp_today / p_today) ** cross_elast
            lambda_orders = p["base_daily_demand"] * price_effect * comp_effect * season_mult * weekend_boost
            
            daily_orders_count = np.random.poisson(max(0.5, lambda_orders))
            
            daily_units_sold = 0
            daily_revenue = 0.0
            
            if daily_orders_count > 0:
                sampled_indices = np.random.randint(0, num_cust, size=daily_orders_count)
                
                for s_idx in sampled_indices:
                    cust_id = cust_ids[s_idx]
                    segment = cust_segments[s_idx]
                    region = cust_regions[s_idx]
                    
                    seg_profile = seg_profile_map[segment]
                    if segment == "Corporate / Bulk":
                        quantity = int(np.random.choice([2, 3, 4, 5, 8, 10], p=[0.20, 0.25, 0.25, 0.15, 0.10, 0.05]))
                    elif segment == "Premium / High-End":
                        quantity = int(np.random.choice([1, 2, 3], p=[0.70, 0.22, 0.08]))
                    elif segment == "Value Seekers":
                        quantity = int(np.random.choice([1, 2], p=[0.82, 0.18]))
                    else:
                        quantity = int(np.random.choice([1, 2], p=[0.92, 0.08]))
                        
                    has_discount = random.random() < seg_profile["discount_affinity"]
                    discount_rate = 0.0
                    if has_discount:
                        discount_rate = float(np.random.choice([0.05, 0.10, 0.15, 0.20], p=[0.40, 0.35, 0.15, 0.10]))
                    
                    unit_price = round(p_today, 2)
                    effective_price = round(unit_price * (1.0 - discount_rate), 2)
                    txn_revenue = round(quantity * effective_price, 2)
                    txn_cost = round(quantity * base_cost, 2)
                    txn_profit = round(txn_revenue - txn_cost, 2)
                    
                    inventory_tracker[pid] = max(15, inventory_tracker[pid] - quantity)
                    if inventory_tracker[pid] < 50:
                        inventory_tracker[pid] += p["inventory_level"] * 5
                        
                    current_inv = inventory_tracker[pid]
                    txn_id = f"TXN-{transaction_counter:07d}"
                    transaction_counter += 1
                    
                    sales_records.append({
                        "transaction_id": txn_id,
                        "date": date_str,
                        "product_id": pid,
                        "customer_id": cust_id,
                        "region": region,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "discount": discount_rate,
                        "revenue": txn_revenue,
                        "cost": txn_cost,
                        "profit": txn_profit,
                        "competitor_price": comp_today,
                        "inventory_level": current_inv
                    })
                    
                    daily_units_sold += quantity
                    daily_revenue += txn_revenue
                
            pricing_history_records.append({
                "date": date_str,
                "product_id": pid,
                "price": p_today,
                "quantity_sold": daily_units_sold,
                "competitor_price": comp_today,
                "revenue": round(daily_revenue, 2)
            })

    df_sales = pd.DataFrame(sales_records)
    df_pricing_history = pd.DataFrame(pricing_history_records)
    
    return df_sales, df_pricing_history


def inject_dirty_raw_data(df_customers, df_products, df_sales, df_pricing):
    """
    Inject realistic raw data quality issues into datasets to test
    and demonstrate the robust data cleaning pipeline.
    """
    raw_sales = df_sales.copy()
    raw_customers = df_customers.copy()
    raw_products = df_products.copy()
    raw_pricing = df_pricing.copy()
    
    # 1. Inject duplicate sales transactions (~0.8%)
    num_dups = int(len(raw_sales) * 0.008)
    dup_rows = raw_sales.sample(n=num_dups, random_state=SEED)
    raw_sales = pd.concat([raw_sales, dup_rows], ignore_index=True)
    
    # 2. Inject missing customer IDs (~1.0%)
    missing_cust_indices = raw_sales.sample(frac=0.010, random_state=SEED).index
    raw_sales.loc[missing_cust_indices, "customer_id"] = np.nan
    
    # 3. Inject missing discount values (~1.2%)
    missing_disc_indices = raw_sales.sample(frac=0.012, random_state=SEED+1).index
    raw_sales.loc[missing_disc_indices, "discount"] = np.nan
    
    # 4. Inject invalid negative quantities & zero prices
    glitch_indices = raw_sales.sample(n=45, random_state=SEED+2).index
    raw_sales.loc[glitch_indices[:20], "quantity"] = -1
    raw_sales.loc[glitch_indices[20:35], "unit_price"] = -5.0
    raw_sales.loc[glitch_indices[35:], "revenue"] = -50.0
    
    # 5. Inconsistent category string casing and whitespace in products
    category_variations = [" electronics ", "ELECTRONICS", "Electronics", "Apparel & footwear", " apparel & footwear "]
    for i in range(min(5, len(raw_products))):
        raw_products.loc[i, "category"] = category_variations[i % len(category_variations)]
        
    # 6. Inconsistent date formats in sales (some slashed MM/DD/YYYY)
    date_slash_indices = raw_sales.sample(frac=0.03, random_state=SEED+3).index
    raw_sales.loc[date_slash_indices, "date"] = raw_sales.loc[date_slash_indices, "date"].apply(
        lambda d: datetime.strptime(str(d), "%Y-%m-%d").strftime("%m/%d/%Y") if pd.notnull(d) else d
    )
    
    # 7. Missing region in some customer rows (~0.8%)
    missing_reg_indices = raw_customers.sample(frac=0.008, random_state=SEED+4).index
    raw_customers.loc[missing_reg_indices, "region"] = np.nan

    return raw_customers, raw_products, raw_sales, raw_pricing


def main():
    print("=" * 60)
    print("RetailX Data Generation Engine Starting...")
    print("=" * 60)
    
    print("[1/4] Generating Customer Base...")
    df_customers = generate_customers(num_customers=3500)
    print(f"      Created {len(df_customers):,} customer profiles across 4 segments.")
    
    print("[2/4] Generating Product Catalog...")
    df_products = generate_products()
    print(f"      Created {len(df_products)} products with defined econometric elasticity parameters.")
    
    print("[3/4] Simulating 24 Months of Transactions (2024-01-01 to 2025-12-31)...")
    df_sales, df_pricing = generate_transactions(df_customers, df_products, start_date="2024-01-01", end_date="2025-12-31")
    print(f"      Generated {len(df_sales):,} sales transactions.")
    print(f"      Generated {len(df_pricing):,} daily pricing history records.")
    
    print("[4/4] Creating Raw Injected Datasets for ETL Data Cleaning...")
    raw_cust, raw_prod, raw_sales, raw_pricing = inject_dirty_raw_data(df_customers, df_products, df_sales, df_pricing)
    
    # Save Raw Datasets
    raw_cust.to_csv(os.path.join(RAW_DATA_DIR, "customers.csv"), index=False)
    raw_prod.to_csv(os.path.join(RAW_DATA_DIR, "products.csv"), index=False)
    raw_sales.to_csv(os.path.join(RAW_DATA_DIR, "sales.csv"), index=False)
    raw_pricing.to_csv(os.path.join(RAW_DATA_DIR, "pricing_history.csv"), index=False)
    
    print("=" * 60)
    print(f"SUCCESS: Raw files written to '{RAW_DATA_DIR}'")
    print(f" - customers.csv: {len(raw_cust):,} rows")
    print(f" - products.csv: {len(raw_prod):,} rows")
    print(f" - sales.csv: {len(raw_sales):,} rows")
    print(f" - pricing_history.csv: {len(raw_pricing):,} rows")
    print("=" * 60)

if __name__ == "__main__":
    main()
