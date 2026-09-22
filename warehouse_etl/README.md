# warehouse_etl

An automated ETL pipeline that extracts the merchant-funnel data out of PostgreSQL, reshapes it into a proper **star-schema dimensional model** (the standard data-warehouse pattern — not just a copy of the source tables), and loads it into **Snowflake**.

## Why a star schema, not just a table dump

A data warehouse isn't "the same tables, but in the cloud" — it's modeled for fast analytical rollups. This pipeline builds:

- **`dim_lead`**, **`dim_seller`**, **`dim_business_segment`**, **`dim_date`** — dimension tables
- **`fact_deal`** — one row per closed deal, at the grain analysts actually query at, with `activated` pre-computed (joined against the sellers table once, at build time) and revenue pre-joined from `seller_revenue`, so every downstream query skips those joins

Note: `fact_deal.seller_id` deliberately has **no foreign key** to `dim_seller`, mirroring the same real data-quality finding as the relational schema in [`sql/01_schema.sql`](../sql/01_schema.sql) — 54.9% of closed deals reference a seller who never activated, so a strict FK would either reject real data or silently hide the finding. The warehouse keeps the raw signal and lets `activated` (a boolean already resolved at ETL time) answer the analytical question instead.

This is the same schema-design skill tested by "basic understanding of data warehouse concepts" — not just running `pandas.to_sql`.

## Pipeline (two steps, deliberately split)

1. **Extract + Transform** — [`python/build_star_schema.py`](python/build_star_schema.py). Pulls from the local `merchant_funnel_analytics` Postgres database, builds the star schema, and stages it as Parquet files in `data/staged/`. Needs local Postgres access only.
2. **Load** — [`python/load_to_snowflake.py`](python/load_to_snowflake.py). Creates the warehouse/schema/tables from [`sql/create_warehouse_schema.sql`](sql/create_warehouse_schema.sql) and bulk-loads the staged Parquet files via `write_pandas`. Needs real Snowflake credentials, read only from environment variables — the script never hardcodes or prompts for a password.

Splitting it this way means the step that needs real cloud credentials has zero transformation logic in it.

## Running it

```bash
pip install -r requirements.txt

# Step 1 (needs local Postgres, already set up elsewhere in this repo)
python python/build_star_schema.py

# Step 2 (needs your own Snowflake account -- set these first)
export SNOWFLAKE_ACCOUNT="your-account-identifier"
export SNOWFLAKE_USER="your-username"
export SNOWFLAKE_PASSWORD="your-password"
export SNOWFLAKE_WAREHOUSE="COMPUTE_WH"
python python/load_to_snowflake.py
```

On success, `load_to_snowflake.py` prints the row count loaded into each table and runs a sample analytical query (activation rate by lead type) directly against the newly loaded warehouse tables to confirm everything landed correctly.

## Confirmed working — actual output from a live run

```
Connected as user=VYSHNAVIACHI  role=ACCOUNTADMIN  warehouse=COMPUTE_WH
Creating database/schema/tables...
Loaded dim_lead: 8,000 rows
Loaded dim_seller: 3,095 rows
Loaded dim_business_segment: 65 rows
Loaded dim_date: 345 rows
Loaded fact_deal: 842 rows

Verifying with a warehouse-style analytical query...
('online_big', 126, 79, Decimal('62.70'))
('online_medium', 332, 172, Decimal('51.81'))
(None, 6, 3, Decimal('50.00'))
('online_top', 14, 6, Decimal('42.86'))
('online_beginner', 57, 21, Decimal('36.84'))
('online_small', 77, 28, Decimal('36.36'))
('industry', 123, 41, Decimal('33.33'))
('offline', 104, 30, Decimal('28.85'))
('other', 3, 0, Decimal('0.00'))

Done. Data is live in Snowflake under MERCHANT_FUNNEL_WAREHOUSE.ANALYTICS.
```

Row counts match the PostgreSQL source exactly, and activation rate by lead type matches the SQL/Power BI/Excel findings elsewhere in this repo (`online_big` highest at 62.7%, `offline` lowest at 28.85%) — this is a real, verified round trip through a live Snowflake warehouse, not just code that "should work."

**Note:** one early run hit `Failed to cast variant value ... to DATE` on `dim_lead.first_contact_date` — a pandas `Timestamp` column serializes to epoch-microseconds internally, which Snowflake's `write_pandas` can't auto-cast into a `DATE` column. Fixed in [`build_star_schema.py`](python/build_star_schema.py) by converting to a plain `datetime.date` with `.dt.date` before staging (same fix `dim_date` already used).

## Data

Real merchant-acquisition-funnel data (same source as the rest of this repo): 8,000 leads / 842 closed deals from the [Olist Marketing Funnel dataset](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist), joined to real seller revenue.
