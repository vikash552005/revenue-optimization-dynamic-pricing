-- ====================================================================
-- RetailX Analytical SQL Query Suite (22 Production Queries)
-- Demonstrating: CTEs, Window Functions (LAG, LEAD, RANK, ROW_NUMBER,
-- SUM/AVG OVER), CASE WHEN, Subqueries, Date Aggregations, and Joins.
-- ====================================================================

-- --------------------------------------------------------------------
-- QUERY 1: Monthly Revenue, Profit, and MoM Growth Rates
-- Business Question: What is our month-over-month revenue and profit trajectory?
-- --------------------------------------------------------------------
-- NAME: monthly_revenue_and_growth
WITH MonthlyMetrics AS (
    SELECT
        year_month,
        COUNT(transaction_id) AS total_orders,
        SUM(quantity) AS total_units_sold,
        ROUND(SUM(revenue), 2) AS total_revenue,
        ROUND(SUM(profit), 2) AS total_profit,
        ROUND((SUM(profit) / SUM(revenue)) * 100.0, 2) AS profit_margin_pct
    FROM sales
    GROUP BY year_month
)
SELECT
    year_month,
    total_orders,
    total_units_sold,
    total_revenue,
    total_profit,
    profit_margin_pct,
    ROUND(LAG(total_revenue, 1) OVER (ORDER BY year_month), 2) AS prior_month_revenue,
    ROUND(((total_revenue - LAG(total_revenue, 1) OVER (ORDER BY year_month)) / 
           LAG(total_revenue, 1) OVER (ORDER BY year_month)) * 100.0, 2) AS mom_revenue_growth_pct
FROM MonthlyMetrics
ORDER BY year_month;


-- --------------------------------------------------------------------
-- QUERY 2: Monthly Profit Growth and Margin Stability
-- Business Question: Are our profits expanding faster than revenue?
-- --------------------------------------------------------------------
-- NAME: monthly_profit_and_margin
WITH ProfitMoM AS (
    SELECT
        year_month,
        ROUND(SUM(revenue), 2) AS monthly_revenue,
        ROUND(SUM(profit), 2) AS monthly_profit,
        ROUND((SUM(profit) / SUM(revenue)) * 100.0, 2) AS gross_margin_pct
    FROM sales
    GROUP BY year_month
)
SELECT
    year_month,
    monthly_revenue,
    monthly_profit,
    gross_margin_pct,
    ROUND(LAG(monthly_profit, 1) OVER (ORDER BY year_month), 2) AS prev_month_profit,
    ROUND(((monthly_profit - LAG(monthly_profit, 1) OVER (ORDER BY year_month)) / 
           LAG(monthly_profit, 1) OVER (ORDER BY year_month)) * 100.0, 2) AS mom_profit_growth_pct
FROM ProfitMoM
ORDER BY year_month;


-- --------------------------------------------------------------------
-- QUERY 3: Revenue, Profit & Share of Total by Product Category
-- Business Question: Which categories are our primary revenue and margin engines?
-- --------------------------------------------------------------------
-- NAME: revenue_and_margin_by_category
WITH CatSummary AS (
    SELECT
        p.category,
        COUNT(s.transaction_id) AS total_orders,
        SUM(s.quantity) AS total_units,
        ROUND(SUM(s.revenue), 2) AS total_revenue,
        ROUND(SUM(s.profit), 2) AS total_profit,
        ROUND(AVG(s.effective_price), 2) AS average_selling_price,
        ROUND((SUM(s.profit) / SUM(s.revenue)) * 100.0, 2) AS category_margin_pct
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    GROUP BY p.category
)
SELECT
    category,
    total_orders,
    total_units,
    total_revenue,
    total_profit,
    average_selling_price,
    category_margin_pct,
    ROUND((total_revenue / SUM(total_revenue) OVER ()) * 100.0, 2) AS revenue_share_pct,
    ROUND((total_profit / SUM(total_profit) OVER ()) * 100.0, 2) AS profit_share_pct
FROM CatSummary
ORDER BY total_revenue DESC;


-- --------------------------------------------------------------------
-- QUERY 4: Regional Performance Ranking and Profitability
-- Business Question: Which geographic regions deliver the highest margin efficiency?
-- --------------------------------------------------------------------
-- NAME: regional_performance_ranking
SELECT
    region,
    COUNT(transaction_id) AS total_transactions,
    SUM(quantity) AS total_units_sold,
    ROUND(SUM(revenue), 2) AS total_revenue,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND((SUM(profit) / SUM(revenue)) * 100.0, 2) AS regional_margin_pct,
    ROUND(AVG(effective_price), 2) AS avg_realized_price,
    RANK() OVER (ORDER BY SUM(revenue) DESC) AS revenue_rank,
    RANK() OVER (ORDER BY SUM(profit) DESC) AS profit_rank
FROM sales
GROUP BY region
ORDER BY revenue_rank;


-- --------------------------------------------------------------------
-- QUERY 5: Top 10 Most Profitable Products
-- Business Question: What are our top profit-generating products?
-- --------------------------------------------------------------------
-- NAME: top_10_most_profitable_products
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.base_cost,
    p.current_price,
    SUM(s.quantity) AS total_units_sold,
    ROUND(SUM(s.revenue), 2) AS total_revenue,
    ROUND(SUM(s.profit), 2) AS total_profit,
    ROUND((SUM(s.profit) / SUM(s.revenue)) * 100.0, 2) AS realized_margin_pct,
    DENSE_RANK() OVER (ORDER BY SUM(s.profit) DESC) AS profit_rank
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.base_cost, p.current_price
ORDER BY profit_rank
LIMIT 10;


-- --------------------------------------------------------------------
-- QUERY 6: Bottom 10 Underperforming Products
-- Business Question: Which products yield the lowest revenue/profit contribution?
-- --------------------------------------------------------------------
-- NAME: bottom_10_underperforming_products
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.base_cost,
    p.current_price,
    SUM(s.quantity) AS total_units_sold,
    ROUND(SUM(s.revenue), 2) AS total_revenue,
    ROUND(SUM(s.profit), 2) AS total_profit,
    ROUND((SUM(s.profit) / SUM(s.revenue)) * 100.0, 2) AS realized_margin_pct,
    ROUND(AVG(s.discount) * 100.0, 2) AS avg_discount_pct,
    DENSE_RANK() OVER (ORDER BY SUM(s.revenue) ASC) AS revenue_bottom_rank
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.base_cost, p.current_price
ORDER BY revenue_bottom_rank
LIMIT 10;


-- --------------------------------------------------------------------
-- QUERY 7: Average Selling Price (ASP) vs Base Cost Spread
-- Business Question: How much unit margin dollar spread does each product generate?
-- --------------------------------------------------------------------
-- NAME: average_selling_price_vs_base_cost
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.base_cost,
    ROUND(AVG(s.effective_price), 2) AS realized_asp,
    ROUND(AVG(s.effective_price) - p.base_cost, 2) AS unit_margin_spread,
    ROUND(((AVG(s.effective_price) - p.base_cost) / AVG(s.effective_price)) * 100.0, 2) AS unit_margin_pct
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.base_cost
ORDER BY unit_margin_spread DESC;


-- --------------------------------------------------------------------
-- QUERY 8: Discount Depth Impact on Realized Margins
-- Business Question: Does deeper discounting erode profit faster than it drives volume?
-- --------------------------------------------------------------------
-- NAME: discount_depth_impact_analysis
SELECT
    CASE 
        WHEN discount = 0.0 THEN '0% (Full Price)'
        WHEN discount > 0.0 AND discount <= 0.05 THEN '1% - 5% Discount'
        WHEN discount > 0.05 AND discount <= 0.10 THEN '6% - 10% Discount'
        WHEN discount > 0.10 AND discount <= 0.15 THEN '11% - 15% Discount'
        ELSE '16% - 20%+ Discount'
    END AS discount_tier,
    COUNT(transaction_id) AS total_orders,
    SUM(quantity) AS total_units,
    ROUND(SUM(revenue), 2) AS total_revenue,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND((SUM(profit) / SUM(revenue)) * 100.0, 2) AS realized_margin_pct,
    ROUND(AVG(effective_price), 2) AS avg_effective_price
FROM sales
GROUP BY discount_tier
ORDER BY total_revenue DESC;


-- --------------------------------------------------------------------
-- QUERY 9: Competitor Price Index Comparison
-- Business Question: Are we pricing above or below our primary market competitors?
-- --------------------------------------------------------------------
-- NAME: competitor_price_index_comparison
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.current_price AS retailx_price,
    p.competitor_price AS comp_price,
    ROUND(p.current_price - p.competitor_price, 2) AS price_difference,
    ROUND(((p.current_price - p.competitor_price) / p.competitor_price) * 100.0, 2) AS premium_vs_comp_pct,
    CASE 
        WHEN p.current_price > p.competitor_price * 1.03 THEN 'Premium Priced (>3% higher)'
        WHEN p.current_price < p.competitor_price * 0.97 THEN 'Discount Priced (>3% lower)'
        ELSE 'Parity Priced (Within +/-3%)'
    END AS competitive_stance
FROM products p
ORDER BY premium_vs_comp_pct DESC;


-- --------------------------------------------------------------------
-- QUERY 10: Product Margin Bands Classification
-- Business Question: What percentage of our catalog sits in high vs low margin bands?
-- --------------------------------------------------------------------
-- NAME: product_margin_bands_distribution
WITH ProductMargins AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        ROUND((SUM(s.profit) / SUM(s.revenue)) * 100.0, 2) AS realized_margin_pct,
        SUM(s.revenue) AS revenue,
        SUM(s.profit) AS profit
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    GROUP BY p.product_id, p.product_name, p.category
)
SELECT
    CASE 
        WHEN realized_margin_pct >= 60.0 THEN 'High Margin (>= 60%)'
        WHEN realized_margin_pct >= 40.0 THEN 'Medium Margin (40% - 59%)'
        ELSE 'Low Margin (< 40%)'
    END AS margin_band,
    COUNT(product_id) AS product_count,
    ROUND(SUM(revenue), 2) AS total_revenue,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND((SUM(profit) / SUM(revenue)) * 100.0, 2) AS aggregate_margin_pct
FROM ProductMargins
GROUP BY margin_band
ORDER BY total_profit DESC;


-- --------------------------------------------------------------------
-- QUERY 11: Customer Segment Revenue, Volume & Average Order Value (AOV)
-- Business Question: What is the spend profile and AOV across customer segments?
-- --------------------------------------------------------------------
-- NAME: customer_segment_revenue_and_aov
SELECT
    c.customer_segment,
    COUNT(DISTINCT c.customer_id) AS active_customers,
    COUNT(s.transaction_id) AS total_transactions,
    SUM(s.quantity) AS total_units_purchased,
    ROUND(SUM(s.revenue), 2) AS total_revenue,
    ROUND(SUM(s.profit), 2) AS total_profit,
    ROUND(SUM(s.revenue) / COUNT(s.transaction_id), 2) AS average_order_value,
    ROUND((SUM(s.profit) / SUM(s.revenue)) * 100.0, 2) AS segment_margin_pct
FROM sales s
JOIN customers c ON s.customer_id = c.customer_id
GROUP BY c.customer_segment
ORDER BY total_revenue DESC;


-- --------------------------------------------------------------------
-- QUERY 12: Repeat vs One-Time Customer Cohort Breakdown
-- Business Question: How much revenue is driven by repeat vs single-purchase buyers?
-- --------------------------------------------------------------------
-- NAME: repeat_vs_one_time_customers
WITH CustomerFrequency AS (
    SELECT
        customer_id,
        COUNT(transaction_id) AS order_count,
        SUM(revenue) AS customer_total_spend,
        SUM(profit) AS customer_total_profit
    FROM sales
    WHERE customer_id != 'CUST-GUEST'
    GROUP BY customer_id
)
SELECT
    CASE 
        WHEN order_count = 1 THEN '1 Order (One-Time)'
        WHEN order_count BETWEEN 2 AND 5 THEN '2 - 5 Orders (Occasional)'
        WHEN order_count BETWEEN 6 AND 15 THEN '6 - 15 Orders (Frequent)'
        ELSE '16+ Orders (Power Buyer)'
    END AS purchase_frequency_tier,
    COUNT(customer_id) AS customer_count,
    ROUND(SUM(customer_total_spend), 2) AS total_spend,
    ROUND(SUM(customer_total_profit), 2) AS total_profit,
    ROUND(AVG(customer_total_spend), 2) AS avg_spend_per_customer
FROM CustomerFrequency
GROUP BY purchase_frequency_tier
ORDER BY total_spend DESC;


-- --------------------------------------------------------------------
-- QUERY 13: Monthly Category Demand Seasonality Index
-- Business Question: How does category demand swing across the 12 calendar months?
-- --------------------------------------------------------------------
-- NAME: monthly_category_demand_seasonality
WITH MonthlyCategorySales AS (
    SELECT
        p.category,
        s.month,
        SUM(s.revenue) AS monthly_rev
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    GROUP BY p.category, s.month
),
CategoryAverage AS (
    SELECT
        category,
        AVG(monthly_rev) AS avg_monthly_rev
    FROM MonthlyCategorySales
    GROUP BY category
)
SELECT
    mcs.category,
    mcs.month,
    ROUND(mcs.monthly_rev, 2) AS category_monthly_revenue,
    ROUND(ca.avg_monthly_rev, 2) AS category_avg_monthly_revenue,
    ROUND((mcs.monthly_rev / ca.avg_monthly_rev) * 100.0, 2) AS seasonality_index_pct
FROM MonthlyCategorySales mcs
JOIN CategoryAverage ca ON mcs.category = ca.category
ORDER BY mcs.category, mcs.month;


-- --------------------------------------------------------------------
-- QUERY 14: Price Change Response Tracking
-- Business Question: How did daily volume react when product prices shifted?
-- --------------------------------------------------------------------
-- NAME: price_change_demand_response
WITH PriceLag AS (
    SELECT
        date,
        product_id,
        price,
        quantity_sold,
        revenue,
        LAG(price, 1) OVER (PARTITION BY product_id ORDER BY date) AS prior_price,
        LAG(quantity_sold, 1) OVER (PARTITION BY product_id ORDER BY date) AS prior_quantity
    FROM pricing_history
)
SELECT
    date,
    product_id,
    prior_price,
    price AS new_price,
    ROUND(((price - prior_price) / prior_price) * 100.0, 2) AS price_change_pct,
    prior_quantity,
    quantity_sold AS new_quantity,
    ROUND(((CAST(quantity_sold AS REAL) - prior_quantity) / prior_quantity) * 100.0, 2) AS demand_change_pct
FROM PriceLag
WHERE prior_price IS NOT NULL AND price != prior_price
ORDER BY date DESC, product_id
LIMIT 20;


-- --------------------------------------------------------------------
-- QUERY 15: Quarterly Cumulative Running Revenue by Year
-- Business Question: What is our intra-year running revenue accumulation?
-- --------------------------------------------------------------------
-- NAME: quarterly_revenue_and_running_totals
WITH QuarterlyData AS (
    SELECT
        year,
        CASE 
            WHEN month IN (1, 2, 3) THEN 'Q1'
            WHEN month IN (4, 5, 6) THEN 'Q2'
            WHEN month IN (7, 8, 9) THEN 'Q3'
            ELSE 'Q4'
        END AS quarter,
        SUM(revenue) AS quarter_revenue,
        SUM(profit) AS quarter_profit
    FROM sales
    GROUP BY year, quarter
)
SELECT
    year,
    quarter,
    ROUND(quarter_revenue, 2) AS quarter_revenue,
    ROUND(quarter_profit, 2) AS quarter_profit,
    ROUND(SUM(quarter_revenue) OVER (PARTITION BY year ORDER BY quarter), 2) AS ytd_cumulative_revenue,
    ROUND(SUM(quarter_profit) OVER (PARTITION BY year ORDER BY quarter), 2) AS ytd_cumulative_profit
FROM QuarterlyData
ORDER BY year, quarter;


-- --------------------------------------------------------------------
-- QUERY 16: Product Revenue Rank Within Category
-- Business Question: Who are the rank leaders inside each individual category?
-- --------------------------------------------------------------------
-- NAME: product_revenue_rank_within_category
SELECT
    p.category,
    p.product_id,
    p.product_name,
    SUM(s.quantity) AS total_units_sold,
    ROUND(SUM(s.revenue), 2) AS total_revenue,
    ROUND(SUM(s.profit), 2) AS total_profit,
    ROW_NUMBER() OVER (PARTITION BY p.category ORDER BY SUM(s.revenue) DESC) AS rank_in_category
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.category, p.product_id, p.product_name
ORDER BY p.category, rank_in_category;


-- --------------------------------------------------------------------
-- QUERY 17: Customer Acquisition Channel Performance
-- Business Question: Which marketing acquisition channel generates the highest revenue?
-- --------------------------------------------------------------------
-- NAME: customer_lifetime_value_by_channel
SELECT
    c.acquisition_channel,
    COUNT(DISTINCT c.customer_id) AS acquired_customers,
    ROUND(SUM(c.customer_lifetime_value), 2) AS total_modeled_clv,
    ROUND(AVG(c.customer_lifetime_value), 2) AS avg_customer_clv,
    ROUND(SUM(s.revenue), 2) AS total_realized_revenue,
    ROUND(SUM(s.profit), 2) AS total_realized_profit,
    ROUND(SUM(s.revenue) / COUNT(DISTINCT c.customer_id), 2) AS revenue_per_acquired_user
FROM customers c
LEFT JOIN sales s ON c.customer_id = s.customer_id
GROUP BY c.acquisition_channel
ORDER BY total_realized_revenue DESC;


-- --------------------------------------------------------------------
-- QUERY 18: Inventory Velocity and Stock Turnover Proxy
-- Business Question: Which products have fast stock turns vs risk of overstocking?
-- --------------------------------------------------------------------
-- NAME: inventory_turnover_velocity_proxy
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.inventory_level AS current_warehouse_stock,
    SUM(s.quantity) AS total_units_sold_24mo,
    ROUND(CAST(SUM(s.quantity) AS REAL) / 24.0, 1) AS avg_monthly_units_sold,
    ROUND((CAST(SUM(s.quantity) AS REAL) / 24.0) / p.inventory_level, 2) AS monthly_inventory_turn_ratio,
    CASE 
        WHEN ((CAST(SUM(s.quantity) AS REAL) / 24.0) / p.inventory_level) > 0.80 THEN 'High Velocity / Stockout Risk'
        WHEN ((CAST(SUM(s.quantity) AS REAL) / 24.0) / p.inventory_level) < 0.30 THEN 'Slow Velocity / Overstock Risk'
        ELSE 'Balanced Inventory'
    END AS inventory_health_status
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.inventory_level
ORDER BY monthly_inventory_turn_ratio DESC;


-- --------------------------------------------------------------------
-- QUERY 19: Regional Realized Pricing and Discount Disparities
-- Business Question: Are discounts and realized selling prices consistent across regions?
-- --------------------------------------------------------------------
-- NAME: regional_pricing_and_discount_disparities
SELECT
    s.region,
    p.category,
    COUNT(s.transaction_id) AS transactions,
    ROUND(AVG(s.unit_price), 2) AS avg_list_price,
    ROUND(AVG(s.discount) * 100.0, 2) AS avg_discount_pct,
    ROUND(AVG(s.effective_price), 2) AS avg_realized_price,
    ROUND((SUM(s.profit) / SUM(s.revenue)) * 100.0, 2) AS region_category_margin_pct
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY s.region, p.category
ORDER BY p.category, s.region;


-- --------------------------------------------------------------------
-- QUERY 20: Immediate Pricing Action Opportunities
-- Business Question: Which products are priced below competitors with high demand and strong margin?
-- --------------------------------------------------------------------
-- NAME: immediate_pricing_opportunity_candidates
WITH ProductPerformance AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        p.current_price,
        p.competitor_price,
        p.base_cost,
        SUM(s.quantity) AS units_sold,
        SUM(s.revenue) AS revenue,
        ROUND((SUM(s.profit) / SUM(s.revenue)) * 100.0, 2) AS margin_pct,
        ROUND(((p.competitor_price - p.current_price) / p.current_price) * 100.0, 2) AS competitor_price_premium_pct
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    GROUP BY p.product_id, p.product_name, p.category, p.current_price, p.competitor_price, p.base_cost
)
SELECT
    product_id,
    product_name,
    category,
    current_price,
    competitor_price,
    competitor_price_premium_pct,
    margin_pct,
    units_sold,
    CASE 
        WHEN competitor_price > current_price AND margin_pct >= 50.0 THEN 'High Priority: Raise Price (Underpriced vs Competitor)'
        WHEN current_price > competitor_price * 1.05 AND units_sold < 3000 THEN 'Review: Consider Lowering Price (Competitor is Cheaper)'
        ELSE 'Maintain Current Price'
    END AS strategic_pricing_action
FROM ProductPerformance
ORDER BY competitor_price_premium_pct DESC;


-- --------------------------------------------------------------------
-- QUERY 21: Day of Week Order Velocity
-- Business Question: What day of the week generates peak revenue and volume?
-- --------------------------------------------------------------------
-- NAME: day_of_week_order_velocity
SELECT
    day_of_week,
    COUNT(transaction_id) AS total_orders,
    SUM(quantity) AS total_units_sold,
    ROUND(SUM(revenue), 2) AS total_revenue,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND(AVG(revenue), 2) AS avg_revenue_per_order
FROM sales
GROUP BY day_of_week
ORDER BY total_revenue DESC;


-- --------------------------------------------------------------------
-- QUERY 22: Pareto Product Revenue Distribution (80/20 Rule)
-- Business Question: What cumulative percentage of catalog drives 80% of revenue?
-- --------------------------------------------------------------------
-- NAME: pareto_product_revenue_distribution
WITH ProductRev AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        ROUND(SUM(s.revenue), 2) AS total_product_revenue
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    GROUP BY p.product_id, p.product_name, p.category
),
CumulativeRev AS (
    SELECT
        product_id,
        product_name,
        category,
        total_product_revenue,
        SUM(total_product_revenue) OVER (ORDER BY total_product_revenue DESC) AS cumulative_revenue,
        SUM(total_product_revenue) OVER () AS grand_total_revenue
    FROM ProductRev
)
SELECT
    product_id,
    product_name,
    category,
    total_product_revenue,
    cumulative_revenue,
    ROUND((cumulative_revenue / grand_total_revenue) * 100.0, 2) AS cumulative_revenue_share_pct,
    CASE 
        WHEN (cumulative_revenue / grand_total_revenue) <= 0.80 THEN 'Top 80% Revenue Driver'
        ELSE 'Long Tail Driver'
    END AS pareto_classification
FROM CumulativeRev
ORDER BY total_product_revenue DESC;
