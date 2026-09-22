"""
Extract + Transform step of the ETL pipeline: pulls the OLTP-shaped data out
of the merchant_funnel_analytics PostgreSQL database and reshapes it into a
proper dimensional (star schema) model -- the standard data-warehouse
pattern, distinct from just copying source tables 1:1.

Star schema:
    dim_lead, dim_seller, dim_business_segment, dim_date  (dimensions)
    fact_deal                                              (fact, grain = 1
                                                              row per closed
                                                              deal)

Output: one Parquet file per table in warehouse_etl/data/staged/, which
load_to_snowflake.py then loads as-is (kept as a separate step so the load
step -- the one that needs real Snowflake credentials -- has zero
transformation logic in it).
"""
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "data" / "staged"
STAGED.mkdir(parents=True, exist_ok=True)

ENGINE = create_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/merchant_funnel_analytics")


def build_dim_lead() -> pd.DataFrame:
    return pd.read_sql(
        "SELECT mql_id, first_contact_date, landing_page_id, origin FROM marketing_qualified_leads", ENGINE,
        parse_dates=["first_contact_date"],
    )


def build_dim_seller() -> pd.DataFrame:
    return pd.read_sql("SELECT seller_id, seller_city, seller_state FROM sellers", ENGINE)


def build_dim_business_segment() -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT DISTINCT business_segment, business_type FROM closed_deals "
        "WHERE business_segment IS NOT NULL", ENGINE,
    )
    df = df.reset_index(drop=True)
    df.insert(0, "segment_key", df.index + 1)
    return df


def build_dim_date(min_date: str, max_date: str) -> pd.DataFrame:
    dates = pd.date_range(min_date, max_date, freq="D")
    return pd.DataFrame({
        "date_key": dates.strftime("%Y%m%d").astype(int),
        # Plain datetime.date objects (not pandas Timestamps) -- Snowflake's
        # write_pandas/COPY INTO can't auto-cast a raw Timestamp's underlying
        # epoch-microseconds representation into a DATE column, but a plain
        # date object maps cleanly.
        "full_date": dates.date,
        "year": dates.year,
        "month": dates.month,
        "month_name": dates.strftime("%B"),
        "day": dates.day,
        "day_of_week": dates.strftime("%A"),
        "is_weekend": dates.dayofweek.isin([5, 6]),
    })


def build_fact_deal(dim_segment: pd.DataFrame) -> pd.DataFrame:
    deals = pd.read_sql(
        """
        SELECT cd.mql_id, cd.seller_id, cd.won_date, cd.business_segment, cd.business_type,
               cd.lead_type, cd.declared_product_catalog_size, cd.declared_monthly_revenue
        FROM closed_deals cd
        """,
        ENGINE,
        parse_dates=["won_date"],
    )
    sellers = pd.read_sql("SELECT seller_id FROM sellers", ENGINE)
    revenue = pd.read_sql(
        "SELECT seller_id, total_orders, total_revenue FROM seller_revenue", ENGINE
    )

    deals["activated"] = deals["seller_id"].isin(set(sellers["seller_id"]))
    deals = deals.merge(revenue, on="seller_id", how="left")
    deals = deals.merge(dim_segment, on=["business_segment", "business_type"], how="left")
    deals["date_key"] = deals["won_date"].dt.strftime("%Y%m%d").astype("Int64")

    return deals[[
        "mql_id", "seller_id", "segment_key", "date_key", "lead_type", "activated",
        "declared_product_catalog_size", "declared_monthly_revenue", "total_orders", "total_revenue",
    ]]


def main() -> None:
    dim_lead = build_dim_lead()
    dim_seller = build_dim_seller()
    dim_segment = build_dim_business_segment()
    fact = build_fact_deal(dim_segment)

    min_date = fact["date_key"].dropna().astype(str).min()
    max_date = fact["date_key"].dropna().astype(str).max()
    min_date = f"{min_date[:4]}-{min_date[4:6]}-{min_date[6:]}"
    max_date = f"{max_date[:4]}-{max_date[4:6]}-{max_date[6:]}"
    dim_date = build_dim_date(min_date, max_date)

    tables = {
        "dim_lead": dim_lead,
        "dim_seller": dim_seller,
        "dim_business_segment": dim_segment,
        "dim_date": dim_date,
        "fact_deal": fact,
    }
    for name, df in tables.items():
        out = STAGED / f"{name}.parquet"
        df.to_parquet(out, index=False)
        print(f"{name}: {len(df):,} rows -> {out}")


if __name__ == "__main__":
    main()
