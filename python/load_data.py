"""
Loads the raw marketing-funnel CSVs into the merchant_funnel_analytics
PostgreSQL database.
Run after sql/01_schema.sql has been applied.
"""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PSQL = r"C:\Program Files\PostgreSQL\16\bin\psql.exe"

DB = {
    "host": "localhost",
    "port": "5432",
    "user": "postgres",
    "dbname": "merchant_funnel_analytics",
}

LOAD_ORDER = [
    ("sellers", "olist_sellers_dataset.csv"),
    ("marketing_qualified_leads", "olist_marketing_qualified_leads_dataset.csv"),
    ("closed_deals", "olist_closed_deals_dataset.csv"),
    ("seller_revenue", "seller_revenue_summary.csv"),
]


def run_copy(table: str, csv_file: str) -> None:
    csv_path = (RAW_DIR / csv_file).as_posix()
    copy_cmd = f"\\copy {table} FROM '{csv_path}' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')"
    cmd = [
        PSQL,
        "-h", DB["host"],
        "-p", DB["port"],
        "-U", DB["user"],
        "-d", DB["dbname"],
        "-c", copy_cmd,
    ]
    env = os.environ.copy()
    env["PGPASSWORD"] = os.environ.get("PGPASSWORD", "postgres")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(f"[{table}] {result.stdout.strip() or result.stderr.strip()}")
    if result.returncode != 0:
        raise RuntimeError(f"Failed loading {table}: {result.stderr}")


def main() -> None:
    for table, csv_file in LOAD_ORDER:
        run_copy(table, csv_file)
    print("\nAll tables loaded.")


if __name__ == "__main__":
    main()
