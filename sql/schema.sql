-- ====================================================================
-- RetailX Relational Database Schema
-- SQLite 3 Compatible DDL
-- ====================================================================

-- 1. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_segment TEXT NOT NULL,
    age_group TEXT NOT NULL,
    region TEXT NOT NULL,
    acquisition_channel TEXT NOT NULL,
    customer_lifetime_value REAL NOT NULL DEFAULT 0.0
);

-- 2. Products Table
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    base_cost REAL NOT NULL,
    current_price REAL NOT NULL,
    competitor_price REAL NOT NULL,
    inventory_level INTEGER NOT NULL DEFAULT 0,
    seasonality_factor REAL NOT NULL DEFAULT 1.0,
    true_elasticity REAL,
    cross_elasticity REAL,
    base_margin_pct REAL
);

-- 3. Sales Transactions Table
CREATE TABLE IF NOT EXISTS sales (
    transaction_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    product_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    region TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    discount REAL NOT NULL DEFAULT 0.0,
    effective_price REAL NOT NULL,
    revenue REAL NOT NULL,
    cost REAL NOT NULL,
    profit REAL NOT NULL,
    profit_margin_pct REAL NOT NULL,
    competitor_price REAL NOT NULL,
    inventory_level INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    year_month TEXT NOT NULL,
    day_of_week TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- 4. Daily Pricing History Table
CREATE TABLE IF NOT EXISTS pricing_history (
    date TEXT NOT NULL,
    product_id TEXT NOT NULL,
    price REAL NOT NULL,
    quantity_sold INTEGER NOT NULL DEFAULT 0,
    competitor_price REAL NOT NULL,
    revenue REAL NOT NULL DEFAULT 0.0,
    PRIMARY KEY (date, product_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Indexes for fast analytical queries
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(date);
CREATE INDEX IF NOT EXISTS idx_sales_prod ON sales(product_id);
CREATE INDEX IF NOT EXISTS idx_sales_cust ON sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_reg ON sales(region);
CREATE INDEX IF NOT EXISTS idx_sales_ym ON sales(year_month);
CREATE INDEX IF NOT EXISTS idx_pricing_dt_prd ON pricing_history(date, product_id);
CREATE INDEX IF NOT EXISTS idx_prod_cat ON products(category);
