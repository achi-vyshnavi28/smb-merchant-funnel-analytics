-- ============================================================================
-- smb-merchant-funnel-analytics
-- PostgreSQL schema for the Olist Marketing Funnel dataset, joined to real
-- seller performance data.
-- Source: Olist / Kaggle (CC BY-NC-SA 4.0)
-- https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist
--
-- Domain framing: this is the seller/merchant ACQUISITION side of the same
-- platform modeled in the sibling whatsapp-order-ops-analytics repo (which
-- covers the ORDER OPERATIONS side). Together they mirror the two halves of
-- a WhatsApp-first SMB platform's business: getting merchants onto the
-- platform, then running their day-to-day operations once they're on it.
-- ============================================================================

DROP TABLE IF EXISTS closed_deals CASCADE;
DROP TABLE IF EXISTS marketing_qualified_leads CASCADE;
DROP TABLE IF EXISTS seller_revenue CASCADE;
DROP TABLE IF EXISTS sellers CASCADE;

CREATE TABLE sellers (
    seller_id              VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(5),
    seller_city            VARCHAR(100),
    seller_state           VARCHAR(2)
);

CREATE TABLE marketing_qualified_leads (
    mql_id              VARCHAR(32) PRIMARY KEY,
    first_contact_date  DATE,
    landing_page_id     VARCHAR(32),
    origin              VARCHAR(30)
);

-- has_company / has_gtin loaded as TEXT, not BOOLEAN: the raw CSV encodes
-- them as literal "True"/"False" strings mixed with genuine nulls, and a
-- meaningful share of rows have neither -- collapsing that distinction to
-- boolean at load time would silently discard a real data-quality signal
-- (called out explicitly in the EDA report instead).
-- seller_id is intentionally NOT a foreign key to sellers: 462 of 842 closed
-- deals (54.9%) reference a seller_id that never appears in the sellers
-- table at all -- i.e. the deal was won but that merchant never actually
-- listed a product or made a sale. That gap is the headline finding of this
-- project (see docs/case_study.md), not a data error to constrain away.
CREATE TABLE closed_deals (
    mql_id                          VARCHAR(32) PRIMARY KEY REFERENCES marketing_qualified_leads(mql_id),
    seller_id                       VARCHAR(32),
    sdr_id                          VARCHAR(32),
    sr_id                           VARCHAR(32),
    won_date                        TIMESTAMP,
    business_segment                VARCHAR(60),
    lead_type                       VARCHAR(30),
    lead_behaviour_profile          VARCHAR(40),  -- some leads have combined profiles e.g. "cat, wolf"
    has_company                     VARCHAR(10),
    has_gtin                        VARCHAR(10),
    average_stock                   VARCHAR(30),
    business_type                   VARCHAR(30),
    declared_product_catalog_size   NUMERIC,
    declared_monthly_revenue        NUMERIC
);

-- Precomputed from the full order/order_items data in the sibling
-- whatsapp-order-ops-analytics repo (python/prepare_seller_revenue.py there)
-- -- this repo stays focused on the funnel, not a second copy of the full
-- order dataset.
CREATE TABLE seller_revenue (
    seller_id         VARCHAR(32) PRIMARY KEY REFERENCES sellers(seller_id),
    total_orders      INTEGER,
    total_revenue     NUMERIC(12,2),
    first_order_date  TIMESTAMP,
    last_order_date   TIMESTAMP
);

CREATE INDEX idx_closed_deals_seller_id ON closed_deals(seller_id);
CREATE INDEX idx_closed_deals_sdr ON closed_deals(sdr_id);
CREATE INDEX idx_closed_deals_sr ON closed_deals(sr_id);
CREATE INDEX idx_mql_origin ON marketing_qualified_leads(origin);
