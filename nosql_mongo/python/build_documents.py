"""
Extract + Transform step: pulls the same merchant-funnel data out of
PostgreSQL and reshapes it into genuine denormalized DOCUMENTS -- one JSON
document per closed deal, with lead info, seller info, and revenue summary
embedded inline. This is the actual point of a document database: model for
how the data is *read* (a whole deal at once -- lead context, activation
status, revenue, in one fetch), not for update-anomaly-free normalization
the way the relational schema is.

Contrast with warehouse_etl/, which models the SAME source data as a
normalized star schema for Snowflake -- deliberately different modeling
disciplines for the same underlying facts, on purpose.

Output: nosql_mongo/data/staged/deals.jsonl.gz (one JSON object per line,
gzip-compressed), consumed by load_to_mongodb.py.
"""
import gzip
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "data" / "staged"
STAGED.mkdir(parents=True, exist_ok=True)

ENGINE = create_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/merchant_funnel_analytics")


def fetch_deals() -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT cd.mql_id, cd.seller_id, cd.sdr_id, cd.sr_id, cd.won_date,
               cd.business_segment, cd.lead_type, cd.lead_behaviour_profile,
               cd.has_company, cd.has_gtin, cd.average_stock, cd.business_type,
               cd.declared_product_catalog_size, cd.declared_monthly_revenue,
               mql.first_contact_date, mql.landing_page_id, mql.origin
        FROM closed_deals cd
        JOIN marketing_qualified_leads mql ON mql.mql_id = cd.mql_id
        """,
        ENGINE,
        parse_dates=["won_date", "first_contact_date"],
    )


def fetch_sellers() -> pd.DataFrame:
    return pd.read_sql("SELECT seller_id, seller_city, seller_state FROM sellers", ENGINE)


def fetch_revenue() -> pd.DataFrame:
    return pd.read_sql(
        "SELECT seller_id, total_orders, total_revenue, first_order_date, last_order_date "
        "FROM seller_revenue",
        ENGINE,
        parse_dates=["first_order_date", "last_order_date"],
    )


def build_document(deal_row, seller_row, revenue_row) -> dict:
    activated = seller_row is not None

    seller = None
    if seller_row is not None:
        seller = {
            "seller_id": deal_row.seller_id,
            "city": seller_row.seller_city,
            "state": seller_row.seller_state,
        }

    revenue = None
    if revenue_row is not None:
        revenue = {
            "total_orders": int(revenue_row.total_orders),
            "total_revenue": float(revenue_row.total_revenue),
            "first_order_date": revenue_row.first_order_date.isoformat() if pd.notna(revenue_row.first_order_date) else None,
            "last_order_date": revenue_row.last_order_date.isoformat() if pd.notna(revenue_row.last_order_date) else None,
        }

    return {
        "_id": deal_row.mql_id,
        "lead": {
            "first_contact_date": deal_row.first_contact_date.isoformat() if pd.notna(deal_row.first_contact_date) else None,
            "landing_page_id": deal_row.landing_page_id,
            "origin": deal_row.origin,
        },
        "deal": {
            "won_date": deal_row.won_date.isoformat() if pd.notna(deal_row.won_date) else None,
            "sdr_id": deal_row.sdr_id,
            "sr_id": deal_row.sr_id,
            "business_segment": deal_row.business_segment,
            "business_type": deal_row.business_type,
            "lead_type": deal_row.lead_type,
            "lead_behaviour_profile": deal_row.lead_behaviour_profile,
            "has_company": deal_row.has_company if pd.notna(deal_row.has_company) else None,
            "has_gtin": deal_row.has_gtin if pd.notna(deal_row.has_gtin) else None,
            "declared_product_catalog_size": float(deal_row.declared_product_catalog_size) if pd.notna(deal_row.declared_product_catalog_size) else None,
            "declared_monthly_revenue": float(deal_row.declared_monthly_revenue) if pd.notna(deal_row.declared_monthly_revenue) else None,
        },
        "activated": activated,
        "seller": seller,
        "revenue": revenue,
    }


def main() -> None:
    deals = fetch_deals()
    sellers = fetch_sellers().set_index("seller_id")
    revenue = fetch_revenue().set_index("seller_id")

    out_path = STAGED / "deals.jsonl.gz"
    n = 0
    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        for row in deals.itertuples():
            seller_row = sellers.loc[row.seller_id] if row.seller_id in sellers.index else None
            revenue_row = revenue.loc[row.seller_id] if row.seller_id in revenue.index else None
            doc = build_document(row, seller_row, revenue_row)
            f.write(json.dumps(doc) + "\n")
            n += 1

    print(f"Wrote {n:,} deal documents -> {out_path}")


if __name__ == "__main__":
    main()
