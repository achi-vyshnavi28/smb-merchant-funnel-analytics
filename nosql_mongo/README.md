# nosql_mongo

Models the same merchant-funnel data a second way: as genuine denormalized **documents** — one per closed deal, with lead context, seller info, and revenue summary embedded inline — loaded into a live **MongoDB Atlas** cluster.

## Why documents, not just "the same tables in Mongo"

A document database earns its place when the read pattern is "give me everything about this deal in one fetch," not "join 4 tables." Each document in this collection embeds:

- **`lead`** — first contact date, landing page, acquisition channel
- **`deal`** — won date, SDR/SR, business segment, lead type, declared catalog size/revenue at sign-up
- **`activated`** — precomputed boolean (was this deal's seller ever found in the sellers table)
- **`seller`** — city/state, only present if activated
- **`revenue`** — total orders/revenue/date range, only present if activated

That's the same design discipline as [`warehouse_etl/`](../warehouse_etl/) applied in the opposite direction: the star schema normalizes for update-safety and rollup speed, this collection denormalizes for single-fetch reads — deliberately different modeling disciplines for the same underlying facts.

## Pipeline (two steps, deliberately split)

1. **Extract + Transform** — [`python/build_documents.py`](python/build_documents.py). Pulls from the local `merchant_funnel_analytics` Postgres database, builds one document per closed deal, and stages it as gzip-compressed JSONL in `data/staged/`. Needs local Postgres access only.
2. **Load** — [`python/load_to_mongodb.py`](python/load_to_mongodb.py). Bulk-inserts the staged documents into MongoDB Atlas, creates 3 indexes, and runs 4 example queries (a `find` and three real aggregation pipelines using `$group`, `$project`, `$cond`, and `$match`). Needs your own MongoDB Atlas connection string, read only from the `MONGODB_URI` environment variable — the script never hardcodes or prompts for a password.

## Running it

```bash
pip install -r requirements.txt

# Step 1 (needs local Postgres, already set up elsewhere in this repo)
python python/build_documents.py

# Step 2 (needs your own MongoDB Atlas cluster -- set this first)
export MONGODB_URI="mongodb+srv://user:password@cluster0.xxxxx.mongodb.net/"
python python/load_to_mongodb.py
```

## Confirmed working — actual output from a live run

```
Loading documents into merchant_funnel_nosql.deals ...
Loaded 842 documents
Created indexes on deal.lead_type, activated, lead.origin

--- Example NoSQL queries against the loaded documents ---

1) Find: 3 activated deals from the online_big lead type
   deal 327174d3648a...  segment=home_appliances  revenue=R$ 25372.08
   deal 408a9c4a7980...  segment=construction_tools_house_garden  revenue=R$ 1428.22
   deal 0b97be8b4b40...  segment=watches  revenue=R$ 122261.02

2) Aggregation: activation rate by lead type
   online_big: 79/126 activated (62.7%)
   online_medium: 172/332 activated (51.8%)
   nan: 3/6 activated (50.0%)
   online_top: 6/14 activated (42.9%)
   online_beginner: 21/57 activated (36.8%)
   online_small: 28/77 activated (36.4%)
   industry: 41/123 activated (33.3%)
   offline: 30/104 activated (28.8%)
   other: 0/3 activated (0.0%)

3) Aggregation: total revenue by acquisition channel (embedded lead.origin, no join needed)
   unknown: R$ 238,478.75 across 81 activated sellers
   organic_search: R$ 235,919.42 across 113 activated sellers
   paid_search: R$ 179,427.11 across 101 activated sellers
   social: R$ 51,292.04 across 31 activated sellers
   direct_traffic: R$ 27,517.13 across 31 activated sellers

4) Activation rate computed directly from embedded fields (no join needed)
   380 / 842 won deals activated (45.1%)

Done. Data is live in MongoDB Atlas: merchant_funnel_nosql.deals
```

All 842 documents loaded, and every number above matches the PostgreSQL/Power BI/Excel/Streamlit findings elsewhere in this repo exactly (45.1% overall activation rate, same lead-type and channel breakdowns) — this is a real, verified round trip through a live MongoDB Atlas cluster, not just code that "should work."

## Data

Real merchant-acquisition-funnel data (same source as the rest of this repo): 842 closed deals from the [Olist Marketing Funnel dataset](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist), joined to real seller revenue.
