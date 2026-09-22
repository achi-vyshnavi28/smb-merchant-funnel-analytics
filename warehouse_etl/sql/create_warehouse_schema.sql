-- ============================================================================
-- Snowflake star-schema DDL for the merchant-funnel data warehouse.
-- Run automatically by python/load_to_snowflake.py (via the Snowflake Python
-- connector) -- kept here as a standalone file too so the schema design can
-- be read/reviewed independently of the load script.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS MERCHANT_FUNNEL_WAREHOUSE;
CREATE SCHEMA IF NOT EXISTS MERCHANT_FUNNEL_WAREHOUSE.ANALYTICS;
USE SCHEMA MERCHANT_FUNNEL_WAREHOUSE.ANALYTICS;

CREATE OR REPLACE TABLE dim_lead (
    mql_id              VARCHAR(32) PRIMARY KEY,
    first_contact_date  DATE,
    landing_page_id     VARCHAR(32),
    origin              VARCHAR(30)
);

CREATE OR REPLACE TABLE dim_seller (
    seller_id     VARCHAR(32) PRIMARY KEY,
    seller_city   VARCHAR(100),
    seller_state  VARCHAR(2)
);

CREATE OR REPLACE TABLE dim_business_segment (
    segment_key       NUMBER PRIMARY KEY,
    business_segment  VARCHAR(60),
    business_type     VARCHAR(30)
);

CREATE OR REPLACE TABLE dim_date (
    date_key      NUMBER PRIMARY KEY,   -- YYYYMMDD
    full_date     DATE,
    year          NUMBER,
    month         NUMBER,
    month_name    VARCHAR(20),
    day           NUMBER,
    day_of_week   VARCHAR(20),
    is_weekend    BOOLEAN
);

CREATE OR REPLACE TABLE fact_deal (
    mql_id                          VARCHAR(32) REFERENCES dim_lead(mql_id),
    seller_id                       VARCHAR(32),  -- not a FK on purpose: 54.9% of deals reference
                                                   -- a seller who never activated (see dim_seller)
    segment_key                     NUMBER REFERENCES dim_business_segment(segment_key),
    date_key                        NUMBER REFERENCES dim_date(date_key),
    lead_type                       VARCHAR(30),
    activated                       BOOLEAN,
    declared_product_catalog_size   NUMBER,
    declared_monthly_revenue        NUMBER,
    total_orders                    NUMBER,
    total_revenue                   NUMBER(12,2),
    PRIMARY KEY (mql_id)
);

-- Example warehouse-style analytical query: activation rate by month and
-- lead type, computed straight from the star schema.
-- SELECT d.year, d.month_name, f.lead_type,
--        COUNT(*) AS won_deals,
--        SUM(CASE WHEN f.activated THEN 1 ELSE 0 END) AS activated,
--        ROUND(100.0 * SUM(CASE WHEN f.activated THEN 1 ELSE 0 END) / COUNT(*), 2) AS activation_rate_pct
-- FROM fact_deal f
-- JOIN dim_date d ON d.date_key = f.date_key
-- GROUP BY d.year, d.month_name, f.lead_type
-- ORDER BY d.year, d.month_name;
